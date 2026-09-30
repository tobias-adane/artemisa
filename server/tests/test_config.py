from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from artemisa.core.config import MODELS_YAML, ModelRegistry, load_registry


def test_registry_loads_every_role() -> None:
    registry = load_registry()
    assert {"describe", "analyze", "analyze_hard", "reason", "live_read", "chat"} <= set(
        registry.roles
    )


def test_providers_are_pinned_by_role() -> None:
    roles = load_registry().roles
    assert roles["describe"].provider == "openai"
    assert roles["analyze"].provider == "groq"
    assert roles["analyze"].model == "openai/gpt-oss-20b"


def test_unknown_fallback_is_rejected(tmp_path: Path) -> None:
    raw = yaml.safe_load(MODELS_YAML.read_text())
    raw["roles"]["analyze"]["fallback"] = "missing"
    with pytest.raises(ValidationError, match="unknown fallback"):
        ModelRegistry.model_validate(raw)


def test_role_without_price_is_rejected() -> None:
    raw = yaml.safe_load(MODELS_YAML.read_text())
    del raw["prices_usd_per_1m"]["openai/gpt-4.1-nano"]
    with pytest.raises(ValidationError, match="no token price"):
        ModelRegistry.model_validate(raw)
