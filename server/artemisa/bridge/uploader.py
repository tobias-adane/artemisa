"""Entrega de frames a la nube (03-ALGORITMO.md, Entrega del frame).

Cada CAPTURE_INTERVAL_S, el último frame de cada cámara se reduce, se comprime
en memoria y se sube con POST /v1/frames. Nunca se escribe a disco. Si la nube
no responde, el frame se pierde: no hay cola.
"""

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

import cv2
import httpx

from artemisa.bridge.reader import Frame, FrameReader

CAPTURE_INTERVAL_S = 1
UPLOAD_MAX_WIDTH = 512
JPEG_QUALITY = 70

log = logging.getLogger(__name__)


def encode(frame: Frame) -> bytes:
    """Reduce a UPLOAD_MAX_WIDTH, manteniendo la proporción, y comprime a JPEG.

    OpenCV no escribe EXIF: el JPEG sale sin metadatos.
    """
    height, width = frame.shape[:2]
    if width > UPLOAD_MAX_WIDTH:
        size = (UPLOAD_MAX_WIDTH, round(height * UPLOAD_MAX_WIDTH / width))
        frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
    ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise ValueError("could not encode frame")
    return jpeg.tobytes()


class Uploader:
    def __init__(self, client: httpx.AsyncClient, api_url: str, token: str) -> None:
        self.client = client
        self.url = f"{api_url.rstrip('/')}/v1/frames"
        self.token = token
        self._failing = False
        self._last_sent: dict[str, datetime] = {}

    async def deliver(self, space_id: str, frame: Frame, captured_at: datetime) -> bool:
        body = encode(frame)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "image/jpeg",
            "X-Space-Id": space_id,
            "X-Frame-Id": str(uuid4()),
            "X-Captured-At": captured_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        }
        try:
            response = await self.client.post(
                self.url, content=body, headers=headers, timeout=CAPTURE_INTERVAL_S
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self._report(False, type(exc).__name__)
            return False
        finally:
            del body
        self._report(True, None)
        return True

    async def run(self, readers: Sequence[FrameReader]) -> None:
        while True:
            started = asyncio.get_running_loop().time()
            for reader in readers:
                snapshot = reader.latest()
                if snapshot is None or self._last_sent.get(reader.space_id) == snapshot.captured_at:
                    continue  # sin frame nuevo: no se reenvía el anterior
                self._last_sent[reader.space_id] = snapshot.captured_at
                await self.deliver(reader.space_id, snapshot.frame, snapshot.captured_at)
            elapsed = asyncio.get_running_loop().time() - started
            await asyncio.sleep(max(0.0, CAPTURE_INTERVAL_S - elapsed))

    def _report(self, ok: bool, error: str | None) -> None:
        """Un log por cambio de estado, no uno por frame."""
        if not ok and not self._failing:
            log.warning("uploads failing (%s): frames are dropped, not queued", error)
        elif ok and self._failing:
            log.info("uploads recovered")
        self._failing = not ok
