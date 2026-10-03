"""Sesionización: cómo nacen y terminan los threads (03-ALGORITMO.md, Sesionización).

La API suma cada layer al thread abierto del space; si ese thread ya no recibe
layers, lo termina y crea uno nuevo en composing. Nunca narra ni cierra un
thread: eso es trabajo del worker.

Correcciones al pseudocódigo de 03, explicadas allí: el layer se inserta en la
misma transacción que el thread, last_layer_at nunca retrocede y start_time
nunca avanza.
"""

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from artemisa.core.config import THREAD_GAP_S

Decision = Literal["new", "touch", "end_and_new"]


class Connection(Protocol):
    async def execute(self, query: str, *args: object) -> object: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...
    def transaction(self) -> AbstractAsyncContextManager[object]: ...


class Pool(Protocol):
    def acquire(self) -> AbstractAsyncContextManager[Connection]: ...


@dataclass(frozen=True)
class OpenThread:
    id: UUID
    last_layer_at: datetime


def decide(current: OpenThread | None, t: datetime) -> Decision:
    """touch: el layer se suma al thread abierto. end_and_new: ese thread termina y nace otro."""
    if current is None:
        return "new"
    if (t - current.last_layer_at).total_seconds() <= THREAD_GAP_S:
        return "touch"
    return "end_and_new"


async def add_layer(
    pool: Pool,
    space_id: UUID,
    user_id: str,
    description: str,
    flags: Sequence[str],
    captured_at: datetime,
) -> tuple[UUID, Decision]:
    """Suma un layer al thread de su space, en una sola transacción con el thread.

    Así nunca existe un thread sin al menos una observación.
    """
    async with pool.acquire() as conn, conn.transaction():
        # Un solo escritor por space. El índice único de threads es la red de seguridad.
        await conn.execute(
            "select pg_advisory_xact_lock(hashtext('space'), hashtext($1))", str(space_id)
        )
        row = await conn.fetchrow(
            """select id, last_layer_at from threads
               where space_id = $1 and status in ('composing', 'active') and end_time is null""",
            space_id,
        )
        current = OpenThread(row["id"], row["last_layer_at"]) if row is not None else None
        decision = decide(current, captured_at)
        if current is not None and decision == "touch":
            thread_id = current.id
            # greatest y least: un frame capturado antes puede terminar de describirse después.
            await conn.execute(
                """update threads set last_layer_at = greatest(last_layer_at, $2),
                                      start_time = least(start_time, $2)
                   where id = $1""",
                thread_id,
                captured_at,
            )
        else:
            if current is not None:
                # Ya no recibe layers. El worker lo narra si hace falta y lo cierra.
                await conn.execute(
                    "update threads set end_time = last_layer_at where id = $1", current.id
                )
            thread_id = await conn.fetchval(
                """insert into threads (user_id, space_id, status, start_time, last_layer_at)
                   values ($1, $2, 'composing', $3, $3) returning id""",
                user_id,
                space_id,
                captured_at,
            )
        await conn.execute(
            """insert into layers (user_id, thread_id, space_id, description, flags, captured_at)
               values ($1, $2, $3, $4, $5::layer_flag[], $6)""",
            user_id,
            thread_id,
            space_id,
            description,
            list(flags),
            captured_at,
        )
    return thread_id, decision
