"""Una conexión de base simulada que registra lo que se le pide, para los tests sin Postgres."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

THREAD = UUID("00000000-0000-4000-8000-0000000000c1")

LABELS = (
    ("pg_advisory_xact_lock", "lock"),
    ("select id, last_layer_at from threads", "select_open"),
    ("set last_layer_at", "touch"),
    ("set end_time", "end"),
    ("insert into threads", "insert_thread"),
    ("insert into layers", "insert_layer"),
)


def label(query: str) -> str:
    text = " ".join(query.split()).lower()
    return next((name for key, name in LABELS if key in text), text)


class FakeConnection:
    """Registra begin, cada sentencia y commit o rollback, en orden."""

    def __init__(self, open_thread: dict[str, Any] | None = None) -> None:
        self.open_thread = open_thread
        self.events: list[str] = []
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.queries: dict[str, str] = {}  # el SQL de cada sentencia, por su etiqueta

    async def execute(self, query: str, *args: object) -> object:
        self._record(query, args)
        return "OK"

    async def fetchrow(self, query: str, *args: object) -> Any:
        self._record(query, args)
        return self.open_thread

    async def fetchval(self, query: str, *args: object) -> Any:
        self._record(query, args)
        return THREAD

    def _record(self, query: str, args: tuple[object, ...]) -> None:
        self.events.append(label(query))
        self.statements.append((label(query), args))
        self.queries[label(query)] = " ".join(query.split())

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        self.events.append("begin")
        try:
            yield
        except BaseException:
            self.events.append("rollback")
            raise
        self.events.append("commit")


class FakePool:
    def __init__(self, open_thread: dict[str, Any] | None = None) -> None:
        self.connection = FakeConnection(open_thread)
        self.acquired = 0

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[FakeConnection]:
        self.acquired += 1
        yield self.connection
