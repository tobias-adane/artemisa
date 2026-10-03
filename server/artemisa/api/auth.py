"""Autenticación del bridge con su token (sha256 en bridge_secrets).

La comparación es en tiempo constante y recorre todas las cajas, sin cortar al
encontrar la buena. El token nunca se loguea.
"""

import hashlib
import hmac
from typing import Any, Protocol
from uuid import UUID


class Database(Protocol):
    async def execute(self, query: str, *args: object) -> object: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def authenticate_bridge(db: Database, authorization: str | None) -> UUID | None:
    if authorization is None or not authorization.startswith("Bearer "):
        return None
    digest = token_hash(authorization.removeprefix("Bearer "))
    rows = await db.fetch(
        "select bridge_id, token_hash from bridge_secrets where token_hash is not null"
    )
    match: UUID | None = None
    for row in rows:
        if hmac.compare_digest(row["token_hash"].encode(), digest.encode()):
            match = row["bridge_id"]
    return match
