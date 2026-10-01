"""El bridge del paso 4, sin red ni go2rtc: video sintético y servidores simulados."""

import asyncio
import builtins
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
import pytest
from websockets.asyncio.server import ServerConnection, serve

from artemisa.bridge import go2rtc
from artemisa.bridge.control import ControlChannel, control_url, health
from artemisa.bridge.reader import RECONNECT_BACKOFF_MAX_S, FrameReader, backoff_s
from artemisa.bridge.uploader import UPLOAD_MAX_WIDTH, Uploader, encode
from artemisa.core.config import RedactRtsp, redact

SPACE = "8f4e2c1a-0000-4000-8000-000000000001"


def frame(width: int = 1280, height: int = 720, value: int = 0) -> np.ndarray[Any, Any]:
    return np.full((height, width, 3), value, dtype=np.uint8)


# Lector


class FakeCapture:
    def __init__(self, frames: list[Any], opened: bool = True) -> None:
        self.frames = frames
        self.opened = opened
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802
        return self.opened

    def read(self) -> tuple[bool, Any]:
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self) -> None:
        self.released = True


def test_backoff_doubles_up_to_the_max() -> None:
    assert [backoff_s(i) for i in range(8)] == [1, 2, 4, 8, 16, 32, 60, 60]
    assert backoff_s(100) == RECONNECT_BACKOFF_MAX_S


def test_reader_keeps_only_the_latest_frame_and_reconnects() -> None:
    captures = [
        FakeCapture([], opened=False),
        FakeCapture([frame(value=1), frame(value=2), frame(value=3)]),
        FakeCapture([frame(value=9)]),
    ]
    waits: list[float] = []
    reader = FrameReader(SPACE, "rtsp://127.0.0.1:8554/x", lambda url: captures.pop(0), None)

    def wait(delay: float) -> None:
        waits.append(delay)
        if not captures:
            reader.stop()

    reader._wait = wait
    reader.run()
    snapshot = reader.latest()
    assert snapshot is not None
    assert int(snapshot.frame[0, 0, 0]) == 9
    assert snapshot.captured_at.tzinfo is UTC
    # open_failed espera 1 s; cada vez que lee frames, la espera vuelve a empezar en 1 s.
    assert waits == [1.0, 1.0, 1.0]
    assert reader.error == "stream_ended"


def test_reader_reads_a_real_video_file(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"  # fixture del test; el bridge nunca escribe a disco
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter.fourcc(*"mp4v"), 10, (640, 360))
    for i in range(20):
        writer.write(frame(640, 360, value=i * 10))
    writer.release()

    reader = FrameReader(SPACE, str(video))
    reader._wait = lambda delay: reader.stop()
    reader.run()
    snapshot = reader.latest()
    assert snapshot is not None
    assert snapshot.frame.shape == (360, 640, 3)
    assert int(snapshot.frame[0, 0, 0]) > 150  # el último frame, no el primero


# Entrega


def decode(jpeg: bytes) -> np.ndarray[Any, Any]:
    image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    return image


def test_encode_resizes_keeping_aspect_ratio_without_exif() -> None:
    jpeg = encode(frame(1280, 720))
    assert jpeg[:2] == b"\xff\xd8"
    assert b"Exif" not in jpeg
    assert decode(jpeg).shape[:2] == (288, UPLOAD_MAX_WIDTH)


def test_encode_keeps_small_frames() -> None:
    assert decode(encode(frame(320, 180))).shape[:2] == (180, 320)


def uploader_with(handler: Any) -> Uploader:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return Uploader(client, "http://127.0.0.1:8000/", "lab-token")


def test_deliver_posts_raw_jpeg_with_headers() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(202)

    captured = datetime(2026, 9, 21, 19, 42, 11, 482000, tzinfo=UTC)
    assert asyncio.run(uploader_with(handler).deliver(SPACE, frame(), captured)) is True
    request = seen[0]
    assert str(request.url) == "http://127.0.0.1:8000/v1/frames"
    assert request.headers["authorization"] == "Bearer lab-token"
    assert request.headers["content-type"] == "image/jpeg"
    assert request.headers["x-space-id"] == SPACE
    assert request.headers["x-captured-at"] == "2026-09-21T19:42:11.482Z"
    assert len(request.headers["x-frame-id"]) == 36
    assert request.content[:2] == b"\xff\xd8"


def test_failed_delivery_drops_the_frame_and_logs_once(caplog: pytest.LogCaptureFixture) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("refused")

    uploader = uploader_with(handler)

    async def three() -> list[bool]:
        return [await uploader.deliver(SPACE, frame(), datetime.now(UTC)) for _ in range(3)]

    with caplog.at_level(logging.WARNING):
        assert asyncio.run(three()) == [False, False, False]
    assert calls == 3  # no hay reintentos ni cola
    assert caplog.text.count("uploads failing") == 1


def test_nothing_touches_the_disk(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("disk write attempted")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(cv2, "imwrite", forbidden)
    uploader = uploader_with(lambda request: httpx.Response(202))
    assert asyncio.run(uploader.deliver(SPACE, frame(), datetime.now(UTC))) is True


# go2rtc


def test_video_source_loops_through_go2rtc() -> None:
    assert go2rtc.file_source("/videos/door.mp4") == "ffmpeg:/videos/door.mp4#input=loop#video=copy"
    assert go2rtc.stream_url(SPACE) == f"rtsp://127.0.0.1:8554/{SPACE}"


def test_add_stream_uses_the_local_api() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    async def add() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await go2rtc.add_stream(client, SPACE, "ffmpeg:/videos/a.mp4#input=loop")

    asyncio.run(add())
    assert seen[0].method == "PUT"
    assert seen[0].url.host == "127.0.0.1"
    assert seen[0].url.params["name"] == SPACE
    assert seen[0].url.params["src"] == "ffmpeg:/videos/a.mp4#input=loop"


# Canal de control


def test_control_url() -> None:
    assert control_url("http://127.0.0.1:8000/") == "ws://127.0.0.1:8000/v1/bridges/connect"
    assert control_url("https://api.example") == "wss://api.example/v1/bridges/connect"


def test_health_reports_reader_state() -> None:
    reader = FrameReader(SPACE, "x")
    assert health(reader) == {
        "type": "health",
        "space_id": SPACE,
        "ok": False,
        "fps": 0.0,
        "error": "not_started",
    }
    reader.error, reader.fps = None, 9.8
    assert health(reader)["ok"] is True


def test_channel_sends_hello_heartbeat_and_health_then_reconnects() -> None:
    sessions: list[list[dict[str, Any]]] = []
    auth: list[str | None] = []

    async def handler(ws: ServerConnection) -> None:
        auth.append(ws.request.headers.get("Authorization") if ws.request else None)
        messages: list[dict[str, Any]] = []
        sessions.append(messages)
        await ws.send(json.dumps({"type": "start_stream", "space_id": SPACE}))
        for _ in range(4):
            messages.append(json.loads(await ws.recv()))
        await ws.close()  # la nube corta: el bridge tiene que reconectar

    async def scenario() -> None:
        async with serve(handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            reader = FrameReader(SPACE, "x")
            channel = ControlChannel(
                f"http://127.0.0.1:{port}", "lab-token", "bridge-1", "0.0.0", [reader],
                heartbeat_s=0.05, health_s=0.08,
            )  # fmt: skip
            task = asyncio.create_task(channel.run())
            while len(sessions) < 2 or not sessions[1]:
                await asyncio.sleep(0.05)
            task.cancel()

    asyncio.run(asyncio.wait_for(scenario(), timeout=10))
    assert auth[0] == "Bearer lab-token"
    first = sessions[0]
    assert first[0] == {
        "type": "hello",
        "bridge_id": "bridge-1",
        "version": "0.0.0",
        "space_ids": [SPACE],
    }
    kinds = {m["type"] for m in first[1:]}
    assert kinds == {"heartbeat", "health"}
    assert sessions[1][0]["type"] == "hello"


# Logs


def test_rtsp_addresses_never_reach_a_log() -> None:
    assert redact("open rtsp://admin:secret@192.168.0.5:554/s1 failed") == (
        "open rtsp://[redacted] failed"
    )
    record = logging.LogRecord(
        "x", logging.INFO, __file__, 1, "camera %s", ("rtsp://u:p@cam/1",), None
    )
    RedactRtsp().filter(record)
    assert record.getMessage() == "camera rtsp://[redacted]"
