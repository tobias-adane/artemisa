"""Configuración: el registro de modelos (models.yaml) y los logs."""

import logging
import re
from datetime import date
from functools import cache
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

MODELS_YAML = Path(__file__).with_name("models.yaml")

# tts queda abierto hasta el paso 15 (00-DECISIONES.md, punto 10).
UNPRICED_ROLES = frozenset({"tts"})


class RoleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["openai", "groq"]
    model: str
    temperature: float | None = None
    max_output_tokens: int | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    image_detail: Literal["low", "high", "auto"] | None = None
    timeout_s: float
    fallback: str | None = None
    stream: bool = False
    voice: str | None = None
    format: str | None = None


class Price(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: float | None = None
    cached_input: float | None = None
    output: float | None = None
    per_1m_characters: float | None = None


class ModelRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_at: date
    roles: dict[str, RoleConfig]
    prices_usd_per_1m: dict[str, Price]

    @model_validator(mode="after")
    def check_roles(self) -> Self:
        for name, role in self.roles.items():
            if role.fallback is not None and role.fallback not in self.roles:
                raise ValueError(f"role {name}: unknown fallback {role.fallback}")
            if name in UNPRICED_ROLES:
                continue
            price = self.prices_usd_per_1m.get(role.model)
            if price is None or price.input is None or price.output is None:
                raise ValueError(f"role {name}: no token price for {role.model}")
        return self

    def price(self, model: str) -> Price:
        return self.prices_usd_per_1m[model]


@cache
def load_registry(path: Path = MODELS_YAML) -> ModelRegistry:
    return ModelRegistry.model_validate(yaml.safe_load(path.read_text()))


# Logs: ninguna dirección RTSP llega a un log (CLAUDE.md, regla 4).

RTSP_PATTERN = re.compile(r"rtsps?://\S+", re.IGNORECASE)


def redact(text: str) -> str:
    return RTSP_PATTERN.sub("rtsp://[redacted]", text)


class RedactRtsp(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        if record.exc_info and record.exc_info[1] is not None:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactRtsp())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # sin una línea por frame
