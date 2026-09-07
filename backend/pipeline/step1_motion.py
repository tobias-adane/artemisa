"""
Paso 1 — Detección de movimiento (OpenCV, gratuito).

Diferencia de frames consecutivos en escala de grises. Si el cambio
supera el threshold, el frame se pasa (en memoria) a Paso 2a. El frame
NUNCA se escribe a disco ni a la base de datos acá ni en ningún punto
de este módulo — ver backend/CLAUDE.md regla absoluta #1.

Heartbeat: si no hubo cambio en `heartbeat_seconds` (default 5 min), se
manda 1 frame igual como chequeo de salud — así una cámara que mira una
habitación vacía por horas no queda completamente en silencio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import cv2
import numpy as np

DEFAULT_THRESHOLD = 25.0  # diferencia media de píxel (0-255) para considerar "movimiento"
DEFAULT_HEARTBEAT = timedelta(minutes=5)

SENSITIVITY_THRESHOLDS = {
    # Ajustado por espacio vía user_preferences.alert_sensitivity — ver
    # backend/CLAUDE.md Paso 1. Sensibilidad alta = threshold más bajo
    # (detecta cambios más sutiles).
    "low": 40.0,
    "balanced": 25.0,
    "high": 12.0,
}


def threshold_for_sensitivity(sensitivity: str) -> float:
    return SENSITIVITY_THRESHOLDS.get(sensitivity, DEFAULT_THRESHOLD)


def frame_diff_score(previous_gray: np.ndarray, current_gray: np.ndarray) -> float:
    """Diferencia media absoluta entre dos frames en escala de grises, ya del mismo tamaño."""
    if previous_gray.shape != current_gray.shape:
        current_gray = cv2.resize(current_gray, (previous_gray.shape[1], previous_gray.shape[0]))
    diff = cv2.absdiff(previous_gray, current_gray)
    return float(np.mean(diff))


def to_gray(frame_bgr: np.ndarray) -> np.ndarray:
    if frame_bgr.ndim == 2:
        return frame_bgr
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)


@dataclass
class MotionState:
    """Estado por espacio entre llamadas consecutivas a `detect`. Vive en memoria del proceso del worker de esa cámara."""

    previous_gray: np.ndarray | None = None
    last_emitted_at: datetime | None = None
    threshold: float = DEFAULT_THRESHOLD
    heartbeat: timedelta = field(default_factory=lambda: DEFAULT_HEARTBEAT)


@dataclass(frozen=True)
class MotionResult:
    should_emit: bool
    reason: str  # 'motion' | 'heartbeat' | 'none'
    score: float


def detect(state: MotionState, frame_bgr: np.ndarray, *, now: datetime | None = None) -> MotionResult:
    """
    Actualiza `state` in-place y decide si este frame debe pasar a
    Paso 2a. No persiste nada — el llamador decide qué hacer con
    `frame_bgr` si `should_emit` es True (pasarlo a VisionClient) y lo
    descarta en cualquier otro caso.
    """
    now = now or datetime.now(timezone.utc)
    gray = to_gray(frame_bgr)

    if state.previous_gray is None:
        state.previous_gray = gray
        state.last_emitted_at = now
        return MotionResult(should_emit=True, reason="motion", score=0.0)

    score = frame_diff_score(state.previous_gray, gray)
    state.previous_gray = gray

    if score >= state.threshold:
        state.last_emitted_at = now
        return MotionResult(should_emit=True, reason="motion", score=score)

    if state.last_emitted_at is None or (now - state.last_emitted_at) >= state.heartbeat:
        state.last_emitted_at = now
        return MotionResult(should_emit=True, reason="heartbeat", score=score)

    return MotionResult(should_emit=False, reason="none", score=score)
