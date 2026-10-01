"""artemisa-lab: el laboratorio de la Fase 0 en un solo proceso.

Por ahora corre solo el bridge (paso 4): VIDEO_SOURCE entra a go2rtc como la
cámara del space "Front Door" de user_lab, un hilo lo lee y el bridge entrega
un frame por segundo a la API y mantiene el canal de control. La API todavía no
existe (paso 5): las subidas y el canal fallan y reintentan.

Variables: DATABASE_URL, LAB_BRIDGE_TOKEN, ARTEMISA_API_URL y VIDEO_SOURCE (la
ruta del .mp4 como la ve go2rtc, por ejemplo /videos/puerta.mp4).
"""

import asyncio
import logging
import os
from importlib.metadata import version

import asyncpg
import httpx

from artemisa.bridge import go2rtc
from artemisa.bridge.control import ControlChannel
from artemisa.bridge.reader import FrameReader
from artemisa.bridge.uploader import Uploader
from artemisa.core.config import configure_logging

USER_ID = "user_lab"
VIDEO_SPACE = "Front Door"

log = logging.getLogger("artemisa.lab")


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
    bridge_id, space_id = await lab_ids(os.environ["DATABASE_URL"])

    async with httpx.AsyncClient() as client:
        await go2rtc.add_stream(client, space_id, go2rtc.file_source(video_source))
        log.info("VIDEO_SOURCE added to go2rtc as space %s (%s)", VIDEO_SPACE, space_id)

        reader = FrameReader(space_id, go2rtc.stream_url(space_id))
        reader.start()
        uploader = Uploader(client, api_url, token)
        channel = ControlChannel(api_url, token, bridge_id, version("artemisa"), [reader])
        try:
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(uploader.run([reader]))
                tasks.create_task(channel.run())
        finally:
            reader.stop()


def main() -> None:
    configure_logging()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("stopped")


if __name__ == "__main__":
    main()
