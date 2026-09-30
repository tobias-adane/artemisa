from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

from artemisa.lab.seed_demo import SPACES, demo_day

TZ = ZoneInfo("America/Argentina/Buenos_Aires")
DAY = date(2026, 9, 30)


def test_demo_day_has_13_normal_threads() -> None:
    threads = demo_day(DAY, TZ)
    assert len(threads) == 13
    assert all(t.classification == "normal" for t in threads)
    assert {t.space for t in threads} <= set(SPACES)
    assert all(t.start_time.date() == DAY and t.start_time.tzinfo == TZ for t in threads)
    assert all(t.end_time > t.start_time for t in threads)
    assert all(len(t.narrative) <= 240 and len(t.reasoning) <= 500 for t in threads)


def test_package_thread_spans_its_three_layers() -> None:
    package = next(t for t in demo_day(DAY, TZ) if t.layers)
    assert [layer.captured_at.time() for layer in package.layers] == [
        time(11, 19, 48),
        time(11, 20, 12),
        time(11, 20, 31),
    ]
    assert package.start_time.time() == time(11, 19, 48)
    assert package.end_time.time() == time(11, 20, 31)
    assert all(len(layer.description) <= 200 for layer in package.layers)


def test_other_threads_last_five_minutes() -> None:
    others = [t for t in demo_day(DAY, TZ) if not t.layers]
    assert len(others) == 12
    assert all(t.end_time - t.start_time == timedelta(minutes=5) for t in others)


def test_attention_flag_changes_only_the_335_thread() -> None:
    normal, attention = demo_day(DAY, TZ), demo_day(DAY, TZ, attention=True)
    changed = [(a, b) for a, b in zip(normal, attention, strict=True) if a != b]
    assert len(changed) == 1
    before, after = changed[0]
    assert after.start_time.time() == time(15, 35)
    assert after.classification == "attention"
    assert after.narrative == "Maya's back with someone I haven't seen before."
    assert before.narrative == "Maya's back, and she brought a friend."
