"""Guarda de 05-DATOS.md: ninguna migración guarda imágenes ni credenciales."""

import re
from pathlib import Path

SUPABASE = Path(__file__).resolve().parents[2] / "supabase"

FORBIDDEN_TYPE = re.compile(r"\bbytea\b", re.IGNORECASE)
FORBIDDEN_NAME = re.compile(r"image|frame|video|clip|snapshot|jpeg|rtsp|password", re.IGNORECASE)
# Una definición de columna: dentro de un create table, o con alter table ... add column.
COLUMN = re.compile(
    r"^\s*(?:alter\s+table\s+\S+\s+add\s+(?:column\s+)?(?:if\s+not\s+exists\s+)?)?"
    r'"?([a-z_][a-z0-9_]*)"?\s+[a-z]',
    re.IGNORECASE,
)
KEYWORDS = {
    "alter", "and", "as", "begin", "check", "comment", "constraint", "create", "declare",
    "delete", "do", "drop", "else", "end", "exclude", "execute", "for", "foreign", "from",
    "grant", "if", "index", "insert", "language", "not", "on", "or", "partition", "perform",
    "primary", "raise", "references", "return", "returns", "revoke", "select", "set", "then",
    "unique", "update", "using", "values", "where", "with",
}  # fmt: skip


def forbidden_columns(sql: str) -> list[str]:
    found: list[str] = []
    for line in sql.splitlines():
        code = line.split("--", 1)[0]
        if FORBIDDEN_TYPE.search(code):
            found.append(code.strip())
            continue
        match = COLUMN.match(code)
        if match is None or match.group(1).lower() in KEYWORDS:
            continue
        if FORBIDDEN_NAME.search(match.group(1)):
            found.append(code.strip())
    return found


def test_migrations_have_no_visual_or_credential_columns() -> None:
    offenders = {
        path.name: bad
        for path in sorted(SUPABASE.glob("*/*.sql"))
        if (bad := forbidden_columns(path.read_text()))
    }
    assert offenders == {}


def test_there_are_migrations_to_check() -> None:
    assert list(SUPABASE.glob("migrations/*.sql"))


def test_guard_catches_forbidden_columns() -> None:
    sql = """
    create table t (
      id uuid primary key,
      frame_url text,
      payload bytea,
      camera_password text
    );
    alter table t add column snapshot_at timestamptz;
    """
    assert len(forbidden_columns(sql)) == 4


def test_guard_allows_normal_columns() -> None:
    sql = """
    create table threads (
      id uuid primary key,
      narrative text not null, -- nunca un frame
      classification classification not null
    );
    """
    assert forbidden_columns(sql) == []
