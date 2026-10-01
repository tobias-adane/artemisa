"""POST /v1/frames (06-ARQUITECTURA.md, Subida de frames).

El JPEG llega como cuerpo crudo y se lee en memoria, con tope de tamaño. No se
usa el manejo de archivos subidos del framework, que puede escribir a disco.
Ni el cuerpo ni el token se loguean nunca.
"""

import time
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request, Response

from artemisa.api.auth import authenticate_bridge
from artemisa.pipeline.motion import InboxFrame

MAX_FRAME_BYTES = 300 * 1024
MAX_CLOCK_SKEW_S = 30

router = APIRouter()


def parse_headers(request: Request) -> tuple[UUID, UUID, datetime] | None:
    try:
        space_id = UUID(request.headers["x-space-id"])
        frame_id = UUID(request.headers["x-frame-id"])
        captured_at = datetime.fromisoformat(request.headers["x-captured-at"])
    except (KeyError, ValueError):
        return None
    if captured_at.tzinfo is None:
        return None
    if request.headers.get("content-type") != "image/jpeg":
        return None
    return space_id, frame_id, captured_at.astimezone(UTC)


async def read_body(request: Request, limit: int) -> bytes | None:
    """El cuerpo en memoria; None si supera el límite."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        return None
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            return None
    return bytes(body)


@router.post("/v1/frames")
async def post_frame(request: Request) -> Response:
    frames = request.app.state.frames
    bridge_id = await authenticate_bridge(frames.db, request.headers.get("authorization"))
    if bridge_id is None:
        return Response(status_code=401)

    parsed = parse_headers(request)
    if parsed is None:
        return Response(status_code=422)
    space_id, frame_id, captured_at = parsed
    if abs((datetime.now(UTC) - captured_at).total_seconds()) > MAX_CLOCK_SKEW_S:
        return Response(status_code=422)

    space = await frames.space(space_id)
    if space is None or space.bridge_id != bridge_id:
        return Response(status_code=403)

    body = await read_body(request, MAX_FRAME_BYTES)
    if body is None:
        return Response(status_code=413)
    if not frames.first_time(frame_id):
        return Response(status_code=202)  # duplicado: ya lo tenemos, se descarta
    frames.put(space, InboxFrame(body, captured_at, time.monotonic()))
    return Response(status_code=202)
