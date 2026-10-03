"""Postgres real para los tests (TEST_DATABASE_URL). Nunca la base de Supabase de laboratorio.

La base de test tiene que traer lo propio de Supabase que la migración da por
sentado (los roles anon y authenticated, auth.jwt() y la publicación
supabase_realtime): el CI lo crea con tests/supabase_shim.sql antes de correr
pytest. Los tests aplican solo supabase/migrations/0001_fase0.sql.
"""

import asyncio
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg

MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "0001_fase0.sql"
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def unsafe_reason(url: str) -> str | None:
    """Por qué la URL no se puede usar para los tests, o None si es segura.

    Los tests borran el esquema public: solo corren contra una base local cuyo
    nombre termina en _test. Sin parámetros en la URL, que podrían cambiar el host.
    """
    parts = urlsplit(url)
    if parts.hostname not in LOCAL_HOSTS:
        return f"the host {parts.hostname!r} is not local"
    if parts.query:
        return "the URL must not have query parameters"
    name = parts.path.lstrip("/")
    if not name.endswith("_test"):
        return f"the database name {name!r} must end in _test"
    return None


def prepare(url: str) -> None:
    """Esquema public vacío y la migración de la Fase 0, una vez por corrida."""

    async def run() -> None:
        conn = await asyncpg.connect(url)
        try:
            await conn.execute("drop schema if exists public cascade; create schema public")
            await conn.execute(MIGRATION.read_text(encoding="utf-8"))
        finally:
            await conn.close()

    asyncio.run(run())
