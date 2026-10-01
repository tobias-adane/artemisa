"""Un hilo lector por cámara (03-ALGORITMO.md, Lectura del stream).

Lee de go2rtc continuamente y guarda solo el frame más reciente. Sin este hilo,
OpenCV acumula frames en su buffer y el bridge entregaría frames viejos.
"""

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import cv2
import numpy as np

RECONNECT_BACKOFF_MAX_S = 60

# RTSP sobre TCP, no UDP: menos artefactos en redes domésticas.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

log = logging.getLogger(__name__)

Frame = np.ndarray[Any, Any]


class Capture(Protocol):
    def isOpened(self) -> bool: ...  # noqa: N802 (API de OpenCV)
    def read(self) -> tuple[bool, Any]: ...
    def release(self) -> None: ...


def open_capture(url: str) -> Capture:
    return cv2.VideoCapture(url, cv2.CAP_FFMPEG)


def backoff_s(attempt: int) -> float:
    """1, 2, 4, 8… hasta RECONNECT_BACKOFF_MAX_S."""
    return float(min(2 ** min(attempt, 16), RECONNECT_BACKOFF_MAX_S))


@dataclass(frozen=True)
class Snapshot:
    frame: Frame
    captured_at: datetime


class FrameReader(threading.Thread):
    def __init__(
        self,
        space_id: str,
        url: str,
        open_fn: Callable[[str], Capture] = open_capture,
        wait: Callable[[float], object] | None = None,
    ) -> None:
        super().__init__(name=f"reader-{space_id}", daemon=True)
        self.space_id = space_id
        self.url = url
        self._open = open_fn
        self._lock = threading.Lock()
        self._latest: Snapshot | None = None
        self._stop_event = threading.Event()
        self._wait = wait or self._stop_event.wait  # se corta al pedir stop()
        self._frames = 0
        self._window_start = time.monotonic()
        self.fps = 0.0
        self.error: str | None = "not_started"

    def latest(self) -> Snapshot | None:
        with self._lock:
            return self._latest

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        attempt = 0
        while not self._stop_event.is_set():
            capture = self._open(self.url)
            if not capture.isOpened():
                capture.release()
                self._fail("open_failed", attempt)
                attempt += 1
                continue
            log.info("reader %s: connected", self.space_id)
            self.error = None
            read_any = False
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    break
                read_any = True
                self._store(frame)
            capture.release()
            if self._stop_event.is_set():
                break
            attempt = 0 if read_any else attempt
            self._fail("stream_ended", attempt)
            attempt += 1

    def _store(self, frame: Frame) -> None:
        with self._lock:
            self._latest = Snapshot(frame, datetime.now(UTC))
        self._frames += 1
        elapsed = time.monotonic() - self._window_start
        if elapsed >= 1.0:
            self.fps = round(self._frames / elapsed, 1)
            self._frames = 0
            self._window_start = time.monotonic()

    def _fail(self, error: str, attempt: int) -> None:
        self.error = error
        self.fps = 0.0
        delay = backoff_s(attempt)
        log.warning("reader %s: %s, retrying in %.0fs", self.space_id, error, delay)
        self._wait(delay)
