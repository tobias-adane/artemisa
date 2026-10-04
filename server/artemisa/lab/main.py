"""artemisa-lab: el laboratorio de la Fase 0 en un solo proceso.

Corre la API (paso 5), el bridge (paso 4) y el worker (paso 7). VIDEO_SOURCE
entra a go2rtc como la cámara del space "Front Door" de user_lab; el bridge
entrega un frame por segundo a la API, que detecta movimiento y describe, y el
worker narra cada thread y, cuando hace falta, lo razona (Paso 3, paso 8). Las
señales analyze_now y boost van directo por memoria. El lado servidor del canal
de control llega en el paso 9: hasta entonces el bridge avisa que no conecta.

Variables: DATABASE_URL, LAB_BRIDGE_TOKEN, AI_GATEWAY_API_KEY, ARTEMISA_API_URL
(donde escucha la API, por ejemplo http://127.0.0.1:8000) y VIDEO_SOURCE (la
ruta del .mp4 como la ve go2rtc, por ejemplo /videos/puerta.mp4).
"""

import asyncio
import logging
import os
from importlib.metadata import version
from urllib.parse import urlsplit

import asyncpg
import httpx
import uvicorn
from fastapi import FastAPI

from artemisa.api.app import create_app
from artemisa.bridge import go2rtc
from artemisa.bridge.control import ControlChannel
from artemisa.bridge.reader import FrameReader
from artemisa.bridge.uploader import Uploader
from artemisa.core.config import configure_logging
from artemisa.pipeline.analyze import Analysis
from artemisa.pipeline.reason import Reasoning
from artemisa.providers.gateway import Gateway
from artemisa.worker.main import Signals
from artemisa.worker.scheduler import Scheduler

USER_ID = "user_lab"
VIDEO_SPACE = "Front Door"

log = logging.getLogger("artemisa.lab")


class Stopped(Exception):
    """La API terminó (Ctrl+C): se corta todo lo demás."""


def api_server(api_url: str, app: FastAPI) -> uvicorn.Server:
    address = urlsplit(api_url)
    config = uvicorn.Config(
        app,
        host=address.hostname or "127.0.0.1",
        port=address.port or 8000,
        log_config=None,  # usa los logs de artemisa, con el filtro de rtsp://
        access_log=False,  # sin una línea por frame
    )
    return uvicorn.Server(config)


async def lab_ids(database_url: str) -> tuple[str, str]:
    """El bridge de user_lab y su space "Front Door" (los crean lab_only y el seed)."""
    conn = await asyncpg.connect(database_url)
    try:
        bridge_id = await conn.fetchval(
            "select id from bridges where user_id = $1 order by created_at limit 1", USER_ID
        )
        space_id = await conn.fetchval(
            "select id from spaces where user_id = $1 and name = $2", USER_ID, VIDEO_SPACE
        )
    finally:
        await conn.close()
    if bridge_id is None or space_id is None:
        raise SystemExit("No lab bridge or Front Door space: apply lab_only, run seed_demo.")
    return str(bridge_id), str(space_id)


async def run() -> None:
    video_source = os.environ.get("VIDEO_SOURCE", "")
    if not video_source:
        raise SystemExit("Set VIDEO_SOURCE to a .mp4 path as go2rtc sees it, e.g. /videos/x.mp4")
    api_url = os.environ["ARTEMISA_API_URL"]
    token = os.environ["LAB_BRIDGE_TOKEN"]
    database_url = os.environ["DATABASE_URL"]
    bridge_id, space_id = await lab_ids(database_url)

    # Cada análisis en curso toma una conexión (hasta 4 por usuario): el pool deja lugar
    # para la API.
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    gateway = Gateway.from_env(pool)
    # API y worker en el mismo proceso: las señales van por memoria en los dos sentidos.
    signals = Signals(pool)
    worker = Scheduler(pool, Analysis(gateway, Reasoning(gateway, signals)))
    app = create_app(pool, gateway, signals)
    signals.worker, signals.api = worker, app.state.frames
    server = api_server(api_url, app)

    async def serve() -> None:
        await server.serve()
        raise Stopped

    async with httpx.AsyncClient() as client:
        await go2rtc.add_stream(client, space_id, go2rtc.file_source(video_source))
        log.info("VIDEO_SOURCE added to go2rtc as space %s (%s)", VIDEO_SPACE, space_id)

        reader = FrameReader(space_id, go2rtc.stream_url(space_id))
        reader.start()
        uploader = Uploader(client, api_url, token)
        channel = ControlChannel(api_url, token, bridge_id, version("artemisa"), [reader])
        try:
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(serve())
                tasks.create_task(uploader.run([reader]))
                tasks.create_task(channel.run())
                tasks.create_task(worker.run())
        except* Stopped:
            log.info("stopped")
        finally:
            reader.stop()
            await pool.close()


def main() -> None:
    configure_logging()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("stopped")


if __name__ == "__main__":
    main()
