from decimal import Decimal

from artemisa.core.config import Price
from artemisa.core.costs import cost_usd

NANO = Price(input=0.10, cached_input=0.025, output=0.40)
OSS_20B = Price(input=0.075, output=0.30)


def test_cost_uses_real_usage() -> None:
    # 574 de entrada, 40 de salida: el ejemplo de describe en 04-MODELOS.md.
    assert cost_usd(NANO, 574, 0, 40) == Decimal("0.00007340")


def test_cached_tokens_use_cached_rate() -> None:
    assert cost_usd(NANO, 1_000_000, 1_000_000, 0) == Decimal("0.02500000")


def test_without_cached_rate_cached_tokens_pay_full_input() -> None:
    assert cost_usd(OSS_20B, 1_000_000, 400_000, 0) == Decimal("0.07500000")


def test_output_includes_reasoning() -> None:
    assert cost_usd(OSS_20B, 1400, 0, 350) == Decimal("0.00021000")
