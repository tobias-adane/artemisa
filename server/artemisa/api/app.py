"""La API (artemisa-api). En la Fase 0 la levanta artemisa-lab en el mismo proceso."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI

from artemisa.api.auth import Database
from artemisa.api.routes import frames
from artemisa.core.config import load_registry
from artemisa.pipeline.describe import Models, SpaceInfo, WorkerSignal, on_frame
from artemisa.pipeline.motion import FrameKind, InboxFrame, MotionLoop

FRAME_DEDUP_WINDOW_S = 300

log = logging.getLogger(__name__)


class Frames:
    """Lo que vive en memoria de la API: el inbox y el loop de cada space, y los ids vistos."""

    def __init__(self, db: Database, models: Models, signals: WorkerSignal) -> None:
        self.db = db
        self.models = models
        self.signals = signals
        self.detail = load_registry().roles["describe"].image_detail
        self.loops: dict[UUID, MotionLoop] = {}
        self._spaces: dict[UUID, SpaceInfo] = {}
        self._seen: dict[UUID, float] = {}
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def space(self, space_id: UUID) -> SpaceInfo | None:
        if space_id not in self._spaces:
            row = await self.db.fetchrow(
                """select s.id, s.user_id, s.bridge_id, s.name, s.motion_threshold,
                          u.locale, u.timezone
                   from spaces s join users u on u.id = s.user_id where s.id = $1""",
                space_id,
            )
            if row is None:
                return None
            self._spaces[space_id] = SpaceInfo(**dict(row))
        return self._spaces[space_id]

    def first_time(self, frame_id: UUID) -> bool:
        """Descarta duplicados por X-Frame-Id dentro de FRAME_DEDUP_WINDOW_S."""
        now = time.monotonic()
        self._seen = {k: t for k, t in self._seen.items() if now - t < FRAME_DEDUP_WINDOW_S}
        if frame_id in self._seen:
            return False
        self._seen[frame_id] = now
        return True

    def put(self, space: SpaceInfo, frame: InboxFrame) -> None:
        loop = self.loops.get(space.id)
        if loop is None:

            async def handle(kind: FrameKind, inbox_frame: InboxFrame) -> None:
                await on_frame(
                    self.models, self.db, self.signals, space, kind, inbox_frame, self.detail
                )

            loop = MotionLoop(str(space.id), space.motion_threshold, handle)
            self.loops[space.id] = loop
            self._tasks[space.id] = asyncio.create_task(loop.run())
            log.info("space %s (%s): motion loop started", space.id, space.name)
        loop.inbox.put(frame)

    async def close(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)


def create_app(db: Database, models: Models, signals: WorkerSignal) -> FastAPI:
    frames_state = Frames(db, models, signals)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await frames_state.close()

    app = FastAPI(title="Artemisa", lifespan=lifespan)
    app.state.frames = frames_state
    app.include_router(frames.router)
    return app
