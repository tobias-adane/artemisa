"""Los enums de Python coinciden con los tipos de la migración (leyendo el SQL)."""

import re
from enum import Enum
from pathlib import Path

import pytest

from artemisa.core.schemas import Classification, Flag

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
ENUM = re.compile(r"create\s+type\s+(\w+)\s+as\s+enum\s*\(([^)]*)\)", re.IGNORECASE)


def sql_enums() -> dict[str, list[str]]:
    sql = "\n".join(path.read_text() for path in sorted(MIGRATIONS.glob("*.sql")))
    return {name: re.findall(r"'([^']*)'", values) for name, values in ENUM.findall(sql)}


@pytest.mark.parametrize(
    ("python_enum", "sql_type"),
    [(Classification, "classification"), (Flag, "layer_flag")],
)
def test_python_enum_matches_sql(python_enum: type[Enum], sql_type: str) -> None:
    assert [member.value for member in python_enum] == sql_enums()[sql_type]
