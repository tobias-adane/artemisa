"""go2rtc: la única forma de leer cámaras (06-ARQUITECTURA.md, go2rtc adentro).

El bridge agrega cada fuente por la API de go2rtc y la lee como un stream RTSP
local. go2rtc guarda la fuente en su configuración, que vive en tmpfs.
"""

import httpx

API_URL = "http://127.0.0.1:1984"
RTSP_URL = "rtsp://127.0.0.1:8554"


def file_source(path: str) -> str:
    """VIDEO_SOURCE: un .mp4 que go2rtc repite en loop, solo con su video."""
    return f"ffmpeg:{path}#input=loop#video=copy"


def stream_url(name: str) -> str:
    return f"{RTSP_URL}/{name}"


async def add_stream(client: httpx.AsyncClient, name: str, source: str) -> None:
    response = await client.put(f"{API_URL}/api/streams", params={"name": name, "src": source})
    response.raise_for_status()
