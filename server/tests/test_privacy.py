"""Revisión de privacidad del paso 5: el frame se suelta y las librerías no loguean secretos."""

import asyncio
import gc
import logging
import re
import weakref
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import httpx2
import numpy as np
import pytest
from websockets.asyncio.client import connect
from websockets.asyncio.server import ServerConnection, serve

from artemisa.core.config import STALE_FRAME_S, quiet_libraries
from artemisa.pipeline import motion
from artemisa.pipeline.motion import InboxFrame, MotionLoop

ROOT = Path(__file__).resolve().parents[2]
SECRET = "bridge-secret-token-123"


def jpeg() -> bytes:
    ok, buf = cv2.imencode(".jpg", np.full((360, 640, 3), 40, np.uint8))
    assert ok
    return buf.tobytes()


async def no_handler(kind: Any, frame: InboxFrame) -> None:
    return None


# Hallazgo 1: el frame también se suelta si el space deja de mandar


def test_stale_frame_is_released_from_memory() -> None:
    loop = MotionLoop("space", 0.02, no_handler)
    frame = InboxFrame(jpeg(), datetime.now(UTC), 100.0)
    ref = weakref.ref(frame)
    loop.inbox.put(frame)
    loop.tick(100.0)  # lo mira: queda en el inbox y en _last_seen
    del frame
    gc.collect()
    assert ref() is not None

    loop.tick(100.0 + STALE_FRAME_S)  # justo en el límite todavía vale
    gc.collect()
    assert ref() is not None

    loop.tick(100.0 + STALE_FRAME_S + 1)  # el space dejó de mandar
    gc.collect()
    assert ref() is None
    assert loop.inbox.latest is None


def test_loop_resumes_after_the_space_comes_back() -> None:
    async def scenario() -> bool:
        loop = MotionLoop("space", 0.02, no_handler)
        loop.inbox.put(InboxFrame(jpeg(), datetime.now(UTC), 100.0))
        loop.tick(100.0)
        loop.tick(160.0)  # se soltó
        again = InboxFrame(jpeg(), datetime.now(UTC), 200.0)
        loop.inbox.put(again)
        loop.tick(200.0)
        await asyncio.gather(*loop._tasks)
        return loop._last_seen is again

    assert asyncio.run(scenario())


def test_stale_frame_s_is_one_constant_shared_with_03() -> None:
    table = (ROOT / "docs" / "03-ALGORITMO.md").read_text(encoding="utf-8")
    match = re.search(r"\|\s*`STALE_FRAME_S`\s*\|\s*([0-9.]+)\s*\|", table)
    assert match is not None
    assert float(match.group(1)) == STALE_FRAME_S
    assert "STALE_FRAME_S =" not in Path(motion.__file__).read_text(encoding="utf-8")


# Hallazgo 2: websockets y httpx2 en WARNING


@pytest.fixture
def restore_log_levels() -> Iterator[None]:
    names = ("httpx", "httpx2", "websockets")
    saved = {name: logging.getLogger(name).level for name in names}
    yield
    for name, level in saved.items():
        logging.getLogger(name).setLevel(level)


def handshake_logs(caplog: pytest.LogCaptureFixture) -> str:
    """Un handshake real con el token en el header Authorization, con el log en DEBUG."""

    async def scenario() -> None:
        async def handler(ws: ServerConnection) -> None:
            await ws.close()

        async with serve(handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            headers = {"Authorization": f"Bearer {SECRET}"}
            async with connect(f"ws://127.0.0.1:{port}", additional_headers=headers):
                pass

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        asyncio.run(asyncio.wait_for(scenario(), timeout=10))
    return caplog.text


def test_websockets_never_logs_the_token_even_in_debug(
    caplog: pytest.LogCaptureFixture, restore_log_levels: None
) -> None:
    assert SECRET in handshake_logs(caplog)  # control: sin el ajuste, el token sale
    quiet_libraries()
    assert SECRET not in handshake_logs(caplog)


def gateway_style_request(caplog: pytest.LogCaptureFixture) -> str:
    """Un pedido por httpx2, que es lo que usa el SDK de OpenAI para llamar al gateway."""
    caplog.clear()
    with caplog.at_level(logging.INFO):
        transport = httpx2.MockTransport(lambda request: httpx2.Response(200))
        with httpx2.Client(transport=transport) as client:
            client.post("http://gateway.test/v1/chat/completions", content=b"x")
    return caplog.text


def test_httpx2_does_not_log_a_line_per_request(
    caplog: pytest.LogCaptureFixture, restore_log_levels: None
) -> None:
    assert "HTTP Request" in gateway_style_request(caplog)  # control: sin el ajuste, loguea
    quiet_libraries()
    assert "HTTP Request" not in gateway_style_request(caplog)
