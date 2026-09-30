"""Un solo cliente para todos los modelos: Vercel AI Gateway con el SDK de openai.

El código pide un rol; models.yaml resuelve modelo, proveedor y parámetros.
Cada intento, exitoso o no, escribe una fila en pipeline_runs (04-MODELOS.md,
Validación y reintentos).
"""

import copy
import os
import time
from dataclasses import dataclass
from functools import cache
from typing import Any
from uuid import UUID

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from artemisa.core.config import ModelRegistry, RoleConfig, load_registry
from artemisa.core.costs import Executor, cost_usd, record_run
from artemisa.core.models import PipelineRun, PipelineStep

BASE_URL = "https://ai-gateway.vercel.sh/v1"
SCHEMA_RETRY = (
    "Your previous answer did not match the schema: {error}. Answer again with only the JSON."
)


# Restricciones que los proveedores rechazan en modo estricto. Pydantic las valida
# igual al recibir la respuesta, así que se quitan de la copia que se manda.
UNSUPPORTED_KEYWORDS = frozenset(
    {
        "default",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minItems",
        "maxItems",
        "pattern",
        "format",
    }
)


@cache
def provider_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """El esquema de Pydantic en la forma estricta que piden los proveedores.

    Sobre una copia: cada objeto (también los de $defs) lleva
    additionalProperties: false y todas sus propiedades en required, y se quitan
    las restricciones de UNSUPPORTED_KEYWORDS. Los campos opcionales siguen
    aceptando null por su anyOf.
    """
    strict: dict[str, Any] = strict_node(copy.deepcopy(schema.model_json_schema()))
    return strict


def strict_node(node: Any) -> Any:
    if isinstance(node, list):
        return [strict_node(item) for item in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in UNSUPPORTED_KEYWORDS:
            continue
        if key in ("properties", "$defs"):
            out[key] = {name: strict_node(sub) for name, sub in value.items()}
        else:
            out[key] = strict_node(value)
    if out.get("type") == "object" or "properties" in out:
        properties = out.get("properties", {})
        out["additionalProperties"] = False
        out["required"] = list(properties)
    return out


class ModelCallFailed(Exception):
    """Ningún intento produjo una salida válida. El mensaje nunca lleva contenido."""


@dataclass(frozen=True)
class Completion[T: BaseModel]:
    output: T
    role: str  # el rol que respondió: puede ser el fallback


@dataclass(frozen=True)
class RunContext:
    step: PipelineStep
    user_id: str | None = None
    space_id: UUID | None = None
    thread_id: UUID | None = None


class Gateway:
    def __init__(self, client: AsyncOpenAI, registry: ModelRegistry, db: Executor) -> None:
        self.client = client
        self.registry = registry
        self.db = db

    @classmethod
    def from_env(cls, db: Executor) -> "Gateway":
        client = AsyncOpenAI(
            api_key=os.environ["AI_GATEWAY_API_KEY"], base_url=BASE_URL, max_retries=0
        )
        return cls(client, load_registry(), db)

    async def complete[T: BaseModel](
        self,
        role: str,
        messages: list[ChatCompletionMessageParam],
        schema: type[T],
        context: RunContext,
    ) -> Completion[T]:
        """Pide el rol; si el proveedor falla o no responde a tiempo, pasa a su fallback.

        Si la salida no coincide con el esquema, hay un solo reintento en el mismo rol.
        Si vuelve a fallar, es un fallo del modelo y no se usa el fallback.
        """
        name: str | None = role
        while name is not None:
            config = self.registry.roles[name]
            conversation = list(messages)
            for attempt in range(2):
                result = await self._call(name, config, conversation, schema, context)
                if result is None:
                    break  # el proveedor falló: fallback
                response, latency_ms = result
                content = response.choices[0].message.content or ""
                try:
                    output = schema.model_validate_json(content)
                except ValidationError as exc:
                    await self._record(name, config, context, response, latency_ms, "schema")
                    if attempt == 1:
                        raise ModelCallFailed(f"{name}: output did not match schema") from None
                    conversation += [
                        {"role": "assistant", "content": content},
                        {"role": "user", "content": SCHEMA_RETRY.format(error=exc)},
                    ]
                    continue
                await self._record(name, config, context, response, latency_ms, None)
                return Completion(output, name)
            name = config.fallback
        raise ModelCallFailed(f"{role}: provider unavailable")

    async def _call(
        self,
        name: str,
        config: RoleConfig,
        messages: list[ChatCompletionMessageParam],
        schema: type[BaseModel],
        context: RunContext,
    ) -> tuple[ChatCompletion, int] | None:
        extra_body: dict[str, Any] = {"providerOptions": {"gateway": {"only": [config.provider]}}}
        if config.reasoning_effort is not None:
            extra_body["reasoning"] = {"effort": config.reasoning_effort}
        started = time.monotonic()
        try:
            response = await self.client.chat.completions.create(
                model=config.model,
                messages=messages,
                temperature=config.temperature if config.temperature is not None else openai.omit,
                max_completion_tokens=config.max_output_tokens or openai.omit,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "schema": provider_schema(schema)},
                },
                store=False,
                timeout=config.timeout_s,
                extra_body=extra_body,
            )
        except openai.APITimeoutError:
            error = "timeout"
        except openai.APIStatusError as exc:
            error = f"http {exc.status_code}"
        except openai.APIConnectionError:
            error = "connection"
        else:
            return response, elapsed_ms(started)
        await record_run(
            self.db,
            PipelineRun(
                **context_fields(context),
                role=name,
                provider=config.provider,
                model=config.model,
                latency_ms=elapsed_ms(started),
                ok=False,
                error=error,
            ),
        )
        return None

    async def _record(
        self,
        name: str,
        config: RoleConfig,
        context: RunContext,
        response: ChatCompletion,
        latency_ms: int,
        error: str | None,
    ) -> None:
        usage = response.usage
        input_tokens = output_tokens = cached = reasoning = cost = None
        if usage is not None:
            input_tokens, output_tokens = usage.prompt_tokens, usage.completion_tokens
            if usage.prompt_tokens_details is not None:
                cached = usage.prompt_tokens_details.cached_tokens
            if usage.completion_tokens_details is not None:
                reasoning = usage.completion_tokens_details.reasoning_tokens
            cost = cost_usd(
                self.registry.price(config.model), input_tokens, cached or 0, output_tokens
            )
        await record_run(
            self.db,
            PipelineRun(
                **context_fields(context),
                role=name,
                provider=config.provider,
                model=config.model,
                input_tokens=input_tokens,
                cached_input_tokens=cached,
                output_tokens=output_tokens,
                reasoning_tokens=reasoning,
                cost_usd=cost,
                latency_ms=latency_ms,
                ok=error is None,
                error=error,
            ),
        )


def context_fields(context: RunContext) -> dict[str, Any]:
    return {
        "step": context.step,
        "user_id": context.user_id,
        "space_id": context.space_id,
        "thread_id": context.thread_id,
    }


def elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)
