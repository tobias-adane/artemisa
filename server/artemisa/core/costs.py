"""Costo de cada llamada con el usage real, y escritura en pipeline_runs."""

from decimal import Decimal
from typing import Protocol

from artemisa.core.config import Price
from artemisa.core.models import PipelineRun

PER_TOKEN = Decimal(1_000_000)
COST_PRECISION = Decimal("0.00000001")  # numeric(12, 8)


class Executor(Protocol):
    async def execute(self, query: str, *args: object) -> object: ...


def cost_usd(
    price: Price, input_tokens: int, cached_input_tokens: int, output_tokens: int
) -> Decimal:
    """El razonamiento viene dentro de output_tokens y se cobra como salida."""
    if price.input is None or price.output is None:
        raise ValueError("price has no token rates")
    cached_rate = price.input if price.cached_input is None else price.cached_input
    uncached = input_tokens - cached_input_tokens
    total = (
        uncached * Decimal(str(price.input))
        + cached_input_tokens * Decimal(str(cached_rate))
        + output_tokens * Decimal(str(price.output))
    ) / PER_TOKEN
    return total.quantize(COST_PRECISION)


async def record_run(db: Executor, run: PipelineRun) -> None:
    await db.execute(
        """insert into pipeline_runs (user_id, space_id, thread_id, step, role, provider,
             model, input_tokens, cached_input_tokens, visual_tokens, output_tokens,
             reasoning_tokens, cost_usd, latency_ms, ok, error)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)""",
        run.user_id,
        run.space_id,
        run.thread_id,
        run.step.value,
        run.role,
        run.provider,
        run.model,
        run.input_tokens,
        run.cached_input_tokens,
        run.visual_tokens,
        run.output_tokens,
        run.reasoning_tokens,
        run.cost_usd,
        run.latency_ms,
        run.ok,
        run.error,
    )
