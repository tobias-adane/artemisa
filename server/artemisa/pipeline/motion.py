"""Paso 1: movimiento, en la nube (03-ALGORITMO.md, Detección).

Aritmética de píxeles, sin modelos. Un loop por space, porque el fondo que
compara vive en memoria. El frame vive en el inbox hasta que llega el
siguiente y nunca se escribe a disco.
"""

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import cv2
import numpy as np

CAPTURE_INTERVAL_S = 1
STALE_FRAME_S = 5
ANALYSIS_WIDTH = 320
BLUR_KERNEL = (21, 21)
PIXEL_DIFF_THRESHOLD = 25
BG_LEARNING_RATE = 0.05
GLOBAL_CHANGE_RATIO = 0.6
DESCRIBE_MIN_INTERVAL_S = 10
STATE_MIN_INTERVAL_S = 300
STATE_REFRESH_MAX_S = 3600
DILATE_KERNEL = np.ones((3, 3), np.uint8)  # el que OpenCV usa por defecto

FrameKind = Literal["motion", "state"]
Image = np.ndarray[Any, Any]

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class InboxFrame:
    jpeg: bytes
    captured_at: datetime
    received_at: float  # time.monotonic() al llegar


class Inbox:
    """El último frame de un space, en memoria. El anterior se suelta al llegar uno nuevo."""

    def __init__(self) -> None:
        self.latest: InboxFrame | None = None

    def put(self, frame: InboxFrame) -> None:
        self.latest = frame


class MotionDetector:
    """Decide qué frames pasan al Paso 2a. Sin refuerzo: llega en el paso 8."""

    def __init__(self, motion_threshold: float) -> None:
        self.motion_threshold = motion_threshold
        self.background: np.ndarray[Any, np.dtype[np.float32]] | None = None
        self.last_described = float("-inf")
        self.last_state = float("-inf")

    def step(self, frame: Image, now: float) -> tuple[FrameKind, float] | None:
        """Devuelve el tipo de frame que pasa al Paso 2a y la proporción cambiada, o None."""
        height, width = frame.shape[:2]
        small = cv2.resize(frame, (ANALYSIS_WIDTH, round(height * ANALYSIS_WIDTH / width)))
        gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), BLUR_KERNEL, 0)
        if self.background is None:
            self.background = gray.astype(np.float32)
            return None

        diff = cv2.absdiff(gray, self.background.astype(np.uint8))
        _, mask = cv2.threshold(diff, PIXEL_DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
        mask = cv2.dilate(mask, DILATE_KERNEL)
        changed = cv2.countNonZero(mask) / mask.size
        cv2.accumulateWeighted(gray, self.background, BG_LEARNING_RATE)

        if changed >= GLOBAL_CHANGE_RATIO:
            # Luz que se prende o apaga, infrarrojo, salto de exposición: no es movimiento.
            self.background = gray.astype(np.float32)
            if now - self.last_state >= STATE_MIN_INTERVAL_S:
                self.last_state = now
                return "state", changed
        elif changed >= self.motion_threshold:
            if now - self.last_described >= DESCRIBE_MIN_INTERVAL_S:
                self.last_described = now
                return "motion", changed
        elif now - self.last_state >= STATE_REFRESH_MAX_S:
            self.last_state = now
            return "state", changed
        return None


FrameHandler = Callable[[FrameKind, InboxFrame], Coroutine[Any, Any, None]]


class MotionLoop:
    def __init__(self, space_id: str, motion_threshold: float, handle: FrameHandler) -> None:
        self.space_id = space_id
        self.inbox = Inbox()
        self.detector = MotionDetector(motion_threshold)
        self.handle = handle
        self._last_seen: InboxFrame | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    def tick(self, now: float) -> None:
        """Una vuelta del loop: mira el último frame del inbox, si es nuevo y no está viejo."""
        latest = self.inbox.latest
        if latest is None or latest is self._last_seen or now - latest.received_at > STALE_FRAME_S:
            return  # la salud de la cámara la reporta el bridge
        self._last_seen = latest
        frame = cv2.imdecode(np.frombuffer(latest.jpeg, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            log.warning("space %s: frame could not be decoded, dropped", self.space_id)
            return
        decision = self.detector.step(frame, now)
        del frame
        if decision is not None:
            kind, changed = decision
            log.info("space %s: %s frame to describe (changed %.3f)", self.space_id, kind, changed)
            task = asyncio.create_task(self.handle(kind, latest))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def run(self) -> None:
        while True:
            await asyncio.sleep(CAPTURE_INTERVAL_S)
            self.tick(time.monotonic())
