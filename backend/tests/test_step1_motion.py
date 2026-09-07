from datetime import datetime, timedelta, timezone

import numpy as np

from pipeline.step1_motion import MotionState, detect, frame_diff_score, threshold_for_sensitivity


def solid_frame(value: int, shape=(64, 64, 3)) -> np.ndarray:
    return np.full(shape, value, dtype=np.uint8)


def test_first_frame_always_emits():
    state = MotionState()
    result = detect(state, solid_frame(100))
    assert result.should_emit
    assert result.reason == "motion"


def test_identical_frames_do_not_emit():
    state = MotionState()
    detect(state, solid_frame(100))  # primer frame, siempre emite
    result = detect(state, solid_frame(100))
    assert not result.should_emit
    assert result.reason == "none"


def test_large_change_emits_motion():
    state = MotionState(threshold=25.0)
    detect(state, solid_frame(0))
    result = detect(state, solid_frame(255))
    assert result.should_emit
    assert result.reason == "motion"
    assert result.score >= 25.0


def test_heartbeat_emits_after_silence_even_without_motion():
    now = datetime.now(timezone.utc)
    state = MotionState(heartbeat=timedelta(minutes=5))
    detect(state, solid_frame(100), now=now)
    # sin movimiento, pero pasaron 6 minutos -> heartbeat
    result = detect(state, solid_frame(100), now=now + timedelta(minutes=6))
    assert result.should_emit
    assert result.reason == "heartbeat"


def test_no_heartbeat_before_window_elapses():
    now = datetime.now(timezone.utc)
    state = MotionState(heartbeat=timedelta(minutes=5))
    detect(state, solid_frame(100), now=now)
    result = detect(state, solid_frame(100), now=now + timedelta(minutes=1))
    assert not result.should_emit


def test_frame_diff_score_zero_for_identical():
    frame = solid_frame(50)
    assert frame_diff_score(frame[:, :, 0], frame[:, :, 0]) == 0.0


def test_sensitivity_thresholds_ordering():
    # más sensible = threshold más bajo (detecta cambios más sutiles)
    assert threshold_for_sensitivity("high") < threshold_for_sensitivity("balanced") < threshold_for_sensitivity("low")
