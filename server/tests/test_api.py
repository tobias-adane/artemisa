"""Paso 5: endpoint de frames, Paso 1 (movimiento) y Paso 2a (descripción), sin red."""

import asyncio
import base64
import builtins
import json
import logging
import os
import tempfile
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import cv2
import httpx
import httpx2
import numpy as np
import pytest
from openai import AsyncOpenAI

from artemisa.api.app import create_app
from artemisa.api.auth import token_hash
from artemisa.core.config import STALE_FRAME_S, load_registry
from artemisa.core.schemas import DescribeOut, Flag
from artemisa.pipeline import describe as describe_module
from artemisa.pipeline import motion
from artemisa.pipeline.describe import SpaceInfo, describe, messages_for, on_frame
from artemisa.pipeline.motion import (
    BOOSTED_INTERVAL_S,
    DESCRIBE_MIN_INTERVAL_S,
    STATE_REFRESH_MAX_S,
    InboxFrame,
    MotionDetector,
    MotionLoop,
)
from artemisa.providers.gateway import BASE_URL, Completion, Gateway, ModelCallFailed, RunContext
from tests.fakes import THREAD, FakePool

TOKEN = "lab-token"
BRIDGE = UUID("00000000-0000-4000-8000-0000000000b1")
OTHER_BRIDGE = UUID("00000000-0000-4000-8000-0000000000b2")
SPACE = UUID("00000000-0000-4000-8000-0000000000a1")
FOREIGN_SPACE = UUID("00000000-0000-4000-8000-0000000000a2")
REASONING_SECRET = "internal chain of thought about the stranger"

TZ = "America/Argentina/Buenos_Aires"
INFO = SpaceInfo(SPACE, "user_lab", BRIDGE, "Front Door", 0.02, "es-AR", TZ)


def scene(box: tuple[int, int, int, int] | None = None, light: int = 40) -> np.ndarray[Any, Any]:
    """Una escena quieta de 640×360; box agrega un objeto claro (movimiento)."""
    image = np.full((360, 640, 3), light, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (120, 80), (90, 90, 90), -1)
    if box is not None:
        x, y, w, h = box
        cv2.rectangle(image, (x, y), (x + w, y + h), (230, 230, 230), -1)
    return image


def jpeg(image: np.ndarray[Any, Any]) -> bytes:
    ok, buf = cv2.imencode(".jpg", image)
    assert ok
    return buf.tobytes()


# Paso 1: detector


def test_first_frame_learns_the_background_then_a_first_state() -> None:
    # 03: last_state arranca en -inf, así que el space tiene estado apenas arranca.
    detector = MotionDetector(0.02)
    assert detector.step(scene(), 0) is None
    first = detector.step(scene(), 1)
    assert first is not None and first[0] == "state"
    assert detector.step(scene(), 2) is None


def test_motion_passes_at_most_every_describe_interval() -> None:
    detector = MotionDetector(0.02)
    detector.step(scene(), 0)
    detector.last_state = 0
    first = detector.step(scene(box=(300, 150, 120, 120)), 1)
    assert first is not None and first[0] == "motion" and first[1] > 0.02
    assert detector.step(scene(box=(200, 100, 120, 120)), 2) is None  # dentro de los 10 s
    later = detector.step(scene(box=(400, 200, 120, 120)), 1 + DESCRIBE_MIN_INTERVAL_S)
    assert later is not None and later[0] == "motion"


def test_light_change_is_state_not_motion_and_resets_background() -> None:
    detector = MotionDetector(0.02)
    detector.step(scene(light=40), 0)
    result = detector.step(scene(light=200), 1)
    assert result is not None and result[0] == "state" and result[1] >= 0.6
    assert detector.step(scene(light=200), 2) is None  # el fondo ya es el nuevo


def test_quiet_space_refreshes_state_after_the_max() -> None:
    detector = MotionDetector(0.02)
    detector.step(scene(), 0)
    detector.last_state = 0
    assert detector.step(scene(), STATE_REFRESH_MAX_S - 1) is None
    result = detector.step(scene(), STATE_REFRESH_MAX_S)
    assert result is not None and result[0] == "state"


def test_threshold_is_per_space() -> None:
    picky = MotionDetector(0.5)
    picky.step(scene(), 0)
    picky.last_state = 0
    assert picky.step(scene(box=(300, 150, 120, 120)), 1) is None


# Paso 1: refuerzo del Paso 3


def test_a_boost_passes_still_frames_every_boosted_interval() -> None:
    """Una persona quieta en el piso no se mueve: con refuerzo pasa igual."""
    detector = MotionDetector(0.02)
    detector.step(scene(), 0)
    detector.last_state = 0
    assert detector.step(scene(), 1) is None  # quieto y sin refuerzo: nada
    detector.boost(1, BOOSTED_INTERVAL_S, 120)
    first = detector.step(scene(), 2)
    assert first is not None and first[0] == "motion" and first[1] < 0.02
    assert detector.step(scene(), 2 + BOOSTED_INTERVAL_S - 1) is None
    assert detector.step(scene(), 2 + BOOSTED_INTERVAL_S) is not None
    assert detector.step(scene(), 121) is None  # vencido: vuelve a la regla de siempre


def test_a_boost_shortens_the_interval_between_moving_frames() -> None:
    detector = MotionDetector(0.02)
    detector.step(scene(), 0)
    detector.last_state = 0
    detector.boost(0, BOOSTED_INTERVAL_S, 120)
    assert detector.step(scene(box=(300, 150, 120, 120)), 1) is not None
    later = detector.step(scene(box=(200, 100, 120, 120)), 1 + BOOSTED_INTERVAL_S)
    assert later is not None  # sin refuerzo serían 10 s


def test_a_light_change_during_a_boost_is_still_state() -> None:
    detector = MotionDetector(0.02)
    detector.step(scene(light=40), 0)
    detector.boost(0, BOOSTED_INTERVAL_S, 120)
    result = detector.step(scene(light=200), 1)
    assert result is not None and result[0] == "state"


def test_the_api_boosts_only_spaces_whose_loop_it_has() -> None:
    frames = create_app(FakeDb(), FakeModels([]), FakeSignals()).state.frames
    frames.boost(uuid4(), BOOSTED_INTERVAL_S, 120)  # sin loop: no pasa nada
    assert frames.loops == {}


# Paso 1: loop


def test_loop_ignores_stale_repeated_and_undecodable_frames() -> None:
    calls: list[str] = []

    async def handle(kind: Any, frame: InboxFrame) -> None:
        calls.append(kind)

    async def scenario() -> None:
        loop = MotionLoop(str(SPACE), 0.02, handle)
        now = 100.0
        loop.inbox.put(InboxFrame(jpeg(scene()), datetime.now(UTC), now))
        loop.tick(now)  # aprende el fondo
        moving = InboxFrame(jpeg(scene(box=(300, 150, 120, 120))), datetime.now(UTC), now)
        loop.inbox.put(moving)
        loop.tick(now + 1 + STALE_FRAME_S)  # viejo: se ignora
        loop.inbox.put(InboxFrame(moving.jpeg, moving.captured_at, now + 2))
        loop.tick(now + 2)
        loop.tick(now + 2.5)  # el mismo frame: no se vuelve a mirar
        loop.inbox.put(InboxFrame(b"not a jpeg", datetime.now(UTC), now + 3))
        loop.tick(now + 3)
        await asyncio.gather(*loop._tasks)

    asyncio.run(scenario())
    assert calls == ["motion"]


# Paso 2a


class FakeModels:
    def __init__(self, results: list[DescribeOut | Exception]) -> None:
        self.results = results
        self.calls: list[tuple[str, RunContext]] = []

    async def complete(self, role: str, messages: Any, schema: Any, context: RunContext) -> Any:
        self.calls.append((role, context))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return Completion(result, role)


class FakeDb:
    def __init__(self, space_bridge: UUID = BRIDGE) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.space_bridge = space_bridge
        self.pool = FakePool()

    def acquire(self) -> Any:
        return self.pool.acquire()

    async def execute(self, query: str, *args: object) -> object:
        self.executed.append((query, args))
        return "OK"

    async def fetch(self, query: str, *args: object) -> list[Any]:
        assert "bridge_secrets" in query
        return [
            {"bridge_id": OTHER_BRIDGE, "token_hash": token_hash("other-token")},
            {"bridge_id": BRIDGE, "token_hash": token_hash(TOKEN)},
        ]

    async def fetchrow(self, query: str, *args: object) -> Any:
        space_id = args[0]
        if space_id == SPACE:
            return {**INFO.__dict__, "bridge_id": self.space_bridge}
        if space_id == FOREIGN_SPACE:
            return {**INFO.__dict__, "id": FOREIGN_SPACE, "bridge_id": OTHER_BRIDGE}
        return None


class FakeSignals:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, object]]] = []

    async def signal_worker(self, channel: str, **payload: object) -> None:
        self.sent.append((channel, payload))


OUT = DescribeOut(description="Alguien deja una caja en la puerta.", flags=[], people_count=1)


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(describe_module, "RETRY_WAIT_S", 0)


def test_prompt_uses_language_local_time_and_inline_image() -> None:
    captured = datetime(2026, 10, 1, 14, 20, tzinfo=UTC)  # 11:20 en Buenos Aires
    messages: Any = messages_for(INFO, b"\xff\xd8jpeg", captured, "low")
    assert "Write the sentence in Argentine Spanish." in messages[0]["content"]
    text, image = messages[1]["content"]
    assert text["text"] == "Space: Front Door. Local time: 11:20."
    assert image["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert image["image_url"]["detail"] == "low"


def test_describe_retries_only_on_failure() -> None:
    ok = FakeModels([OUT])
    assert asyncio.run(describe(ok, INFO, "motion", b"x", datetime.now(UTC), None)) == OUT
    assert len(ok.calls) == 1

    flaky = FakeModels([ModelCallFailed("x"), ModelCallFailed("x"), OUT])
    assert asyncio.run(describe(flaky, INFO, "state", b"x", datetime.now(UTC), None)) == OUT
    assert len(flaky.calls) == 3
    assert flaky.calls[0][1].step == "state"

    down = FakeModels([ModelCallFailed("x")] * 3)
    assert asyncio.run(describe(down, INFO, "motion", b"x", datetime.now(UTC), None)) is None
    assert len(down.calls) == 1 + describe_module.DESCRIBE_RETRIES


def test_motion_frame_updates_state_and_last_motion() -> None:
    db, signals = FakeDb(), FakeSignals()
    captured = datetime.now(UTC)
    frame = InboxFrame(b"x", captured, 0)
    asyncio.run(on_frame(FakeModels([OUT]), db, signals, INFO, "motion", frame, None))
    query, args = db.executed[0]
    assert query.lstrip().startswith("update spaces")
    assert args == (SPACE, OUT.description, True, captured, True)
    # y suma el layer a su thread, en una sola transacción
    events = db.pool.connection.events
    assert events == ["begin", "lock", "select_open", "insert_thread", "insert_layer", "commit"]
    assert signals.sent == []  # sin flags, el worker lo ve en su próximo tick


def test_an_urgent_flag_signals_the_worker_fast_path() -> None:
    signals = FakeSignals()
    urgent = OUT.model_copy(update={"flags": [Flag.person_on_floor]})
    frame = InboxFrame(b"x", datetime.now(UTC), 0)
    asyncio.run(on_frame(FakeModels([urgent]), FakeDb(), signals, INFO, "motion", frame, None))
    assert signals.sent == [("analyze_now", {"thread_id": THREAD, "fast_path": True})]


def test_state_frame_does_not_touch_last_motion_and_failure_drops_the_frame() -> None:
    db = FakeDb()
    frame = InboxFrame(b"x", datetime.now(UTC), 0)
    asyncio.run(on_frame(FakeModels([OUT]), db, FakeSignals(), INFO, "state", frame, None))
    assert db.executed[0][1][4] is False
    assert db.pool.acquired == 0  # un frame de estado no crea threads ni layers
    failed = FakeDb()
    down = FakeModels([ModelCallFailed("x")] * 3)
    asyncio.run(on_frame(down, failed, FakeSignals(), INFO, "motion", frame, None))
    assert failed.executed == []
    assert failed.pool.acquired == 0  # sin descripción no existe un thread


# Endpoint


def headers(overrides: dict[str, str] | None = None) -> dict[str, str]:
    base = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "image/jpeg",
        "X-Space-Id": str(SPACE),
        "X-Frame-Id": str(uuid4()),
        "X-Captured-At": datetime.now(UTC).isoformat(timespec="milliseconds"),
    }
    return {**base, **(overrides or {})}


def post_all(
    requests: list[tuple[dict[str, str], bytes]], db: FakeDb | None = None
) -> tuple[list[int], Any]:
    app = create_app(db or FakeDb(), FakeModels([]), FakeSignals())
    motion_interval = motion.CAPTURE_INTERVAL_S

    async def send() -> list[int]:
        motion.CAPTURE_INTERVAL_S = 3600  # el loop no corre solo durante el test
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
                codes = [
                    (await client.post("/v1/frames", headers=h, content=body)).status_code
                    for h, body in requests
                ]
            await app.state.frames.close()
            return codes
        finally:
            motion.CAPTURE_INTERVAL_S = motion_interval

    return asyncio.run(send()), app.state.frames


def test_valid_frame_is_accepted_into_the_inbox() -> None:
    body = jpeg(scene())
    codes, frames = post_all([(headers(), body)])
    assert codes == [202]
    latest = frames.loops[SPACE].inbox.latest
    assert latest is not None and latest.jpeg == body


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"Authorization": "Bearer wrong"}, 401),
        ({"Authorization": "nope"}, 401),
        ({"X-Space-Id": str(FOREIGN_SPACE)}, 403),
        ({"X-Space-Id": str(uuid4())}, 403),
        ({"X-Space-Id": "not-a-uuid"}, 422),
        ({"Content-Type": "image/png"}, 422),
        ({"X-Captured-At": "2026-10-01T10:00:00"}, 422),  # sin zona horaria
        ({"X-Captured-At": (datetime.now(UTC) - timedelta(seconds=31)).isoformat()}, 422),
    ],
)
def test_rejections(change: dict[str, str], code: int) -> None:
    codes, frames = post_all([(headers(change), jpeg(scene()))])
    assert codes == [code]
    assert frames.loops == {}


def test_oversized_frame_is_rejected() -> None:
    codes, frames = post_all([(headers(), b"\xff" * (300 * 1024 + 1))])
    assert codes == [413]
    assert frames.loops == {}


def test_duplicate_frame_id_is_dropped() -> None:
    first, second = jpeg(scene()), jpeg(scene(box=(1, 1, 50, 50)))
    same = headers()
    codes, frames = post_all([(same, first), (same, second)])
    assert codes == [202, 202]
    assert frames.loops[SPACE].inbox.latest.jpeg == first


# Guarda de 05-DATOS.md: la API no escribe a disco ni deja imágenes en logs o en la base


def forbid_disk_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    real_open, real_os_open = builtins.open, os.open

    def guarded_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(flag in mode for flag in "wax+"):
            raise AssertionError(f"disk write attempted: {file}")
        return real_open(file, mode, *args, **kwargs)

    def guarded_os_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND):
            raise AssertionError(f"disk write attempted: {path}")
        return real_os_open(path, flags, *args, **kwargs)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("disk write attempted")

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(os, "open", guarded_os_open)
    monkeypatch.setattr(cv2, "imwrite", forbidden)
    for name in ("TemporaryFile", "NamedTemporaryFile", "SpooledTemporaryFile", "mkstemp"):
        monkeypatch.setattr(tempfile, name, forbidden)


def gateway_answering(answer: dict[str, Any], db: FakeDb) -> Gateway:
    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        return httpx2.Response(
            200,
            json={
                "id": "c1",
                "object": "chat.completion",
                "created": 0,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(answer),
                            "reasoning": REASONING_SECRET,
                        },
                    }
                ],
                "usage": {"prompt_tokens": 600, "completion_tokens": 40, "total_tokens": 640},
            },
        )

    client = AsyncOpenAI(
        api_key="test",
        base_url=BASE_URL,
        max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )
    return Gateway(client, load_registry(), db)


def test_frames_never_touch_disk_logs_or_pipeline_runs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    db = FakeDb()
    models = gateway_answering(OUT.model_dump(mode="json"), db)
    app = create_app(db, models, FakeSignals())
    quiet, moving = jpeg(scene()), jpeg(scene(box=(300, 150, 120, 120)))
    monkeypatch.setattr(motion, "CAPTURE_INTERVAL_S", 3600)
    forbid_disk_writes(monkeypatch)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
            for body in (quiet, moving):
                response = await client.post("/v1/frames", headers=headers(), content=body)
                assert response.status_code == 202
                loop = app.state.frames.loops[SPACE]
                loop.tick(loop.inbox.latest.received_at)
            await asyncio.gather(*loop._tasks)
        await app.state.frames.close()

    with caplog.at_level(logging.DEBUG):
        asyncio.run(scenario())

    runs = [args for query, args in db.executed if "pipeline_runs" in query]
    updates = [args for query, args in db.executed if query.lstrip().startswith("update spaces")]
    assert len(runs) == 1 and runs[0][15] is None  # una llamada ok, en pipeline_runs
    assert updates and updates[0][1] == OUT.description

    stored = caplog.text + repr(runs)
    for image in (quiet, moving):
        assert base64.b64encode(image)[:40].decode() not in stored
    assert "/9j/" not in stored  # comienzo de un JPEG en base64
    assert "\\xff\\xd8" not in stored and "ÿØ" not in stored
    assert REASONING_SECRET not in stored
    assert TOKEN not in caplog.text


def test_boosted_still_frames_never_touch_disk_or_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """El refuerzo manda frames sin movimiento a describir: siguen sin tocar disco ni logs."""
    db = FakeDb()
    models = gateway_answering(OUT.model_dump(mode="json"), db)
    app = create_app(db, models, FakeSignals())
    still = [jpeg(scene(light=40 + i)) for i in range(3)]  # tres frames quietos, distintos
    monkeypatch.setattr(motion, "CAPTURE_INTERVAL_S", 3600)
    forbid_disk_writes(monkeypatch)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
            for i, body in enumerate(still):
                response = await client.post("/v1/frames", headers=headers(), content=body)
                assert response.status_code == 202
                loop = app.state.frames.loops[SPACE]
                if i == 0:
                    loop.detector.last_state = loop.inbox.latest.received_at
                    app.state.frames.boost(SPACE, 0, 120)  # cada frame, para el test
                loop.tick(loop.inbox.latest.received_at)
            await asyncio.gather(*loop._tasks)
        await app.state.frames.close()

    with caplog.at_level(logging.DEBUG):
        asyncio.run(scenario())

    runs = [args for query, args in db.executed if "pipeline_runs" in query]
    assert len(runs) == 2  # los dos frames quietos pasaron por el refuerzo
    stored = caplog.text + repr(runs)
    for image in still:
        assert base64.b64encode(image)[:40].decode() not in stored
    assert "/9j/" not in stored
    assert "\\xff\\xd8" not in stored and "ÿØ" not in stored
