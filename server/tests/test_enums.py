"""Los enums de Python coinciden con los tipos de la migración (leyendo el SQL)."""

import re
from enum import Enum
from pathlib import Path

import pytest

from artemisa.core import models

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
ENUM = re.compile(r"create\s+type\s+(\w+)\s+as\s+enum\s*\(([^)]*)\)", re.IGNORECASE)


def sql_enums() -> dict[str, list[str]]:
    sql = "\n".join(path.read_text() for path in sorted(MIGRATIONS.glob("*.sql")))
    return {name: re.findall(r"'([^']*)'", values) for name, values in ENUM.findall(sql)}


PYTHON_ENUMS: dict[str, type[Enum]] = {
    "classification": models.Classification,
    "action_level": models.ActionLevel,
    "thread_status": models.ThreadStatus,
    "space_status": models.SpaceStatus,
    "bridge_status": models.BridgeStatus,
    "layer_flag": models.LayerFlag,
    "dispatch_channel": models.DispatchChannel,
    "dispatch_target": models.DispatchTarget,
    "dispatch_status": models.DispatchStatus,
    "push_interruption": models.PushInterruption,
    "alert_sensitivity": models.AlertSensitivity,
    "home_type": models.HomeType,
    "pipeline_step": models.PipelineStep,
    "message_role": models.MessageRole,
}


def test_every_sql_enum_has_a_python_mirror() -> None:
    assert set(PYTHON_ENUMS) == set(sql_enums())


@pytest.mark.parametrize(("sql_type", "python_enum"), PYTHON_ENUMS.items())
def test_python_enum_matches_sql(sql_type: str, python_enum: type[Enum]) -> None:
    assert [member.value for member in python_enum] == sql_enums()[sql_type]
