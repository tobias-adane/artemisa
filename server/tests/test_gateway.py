"""El cliente del gateway, contra un gateway simulado (sin red)."""

import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI

from artemisa.core.config import load_registry
from artemisa.core.models import PipelineStep
from artemisa.core.schemas import AnalysisOut
from artemisa.providers.gateway import BASE_URL, Gateway, ModelCallFailed, RunContext

VALID = {
    "narrative": "A package arrived.",
    "classification": "normal",
    "confidence": 0.9,
    "reasoning": "Same van as most weeks.",
    "escalate": False,
}
SECRET = "Maya walks in with a stranger"  # contenido que nunca debe llegar a pipeline_runs
CONTEXT = RunContext(step=PipelineStep.analyze, user_id="user_lab")
MESSAGES: list[Any] = [{"role": "user", "content": SECRET}]


class FakeDb:
    def __init__(self) -> None:
        self.rows: list[tuple[object, ...]] = []

    async def execute(self, query: str, *args: object) -> object:
        assert query.lstrip().startswith("insert into pipeline_runs")
        self.rows.append(args)
        return "INSERT 0 1"


def completion(content: str, model: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": 1400,
                "completion_tokens": 350,
                "total_tokens": 1750,
                "prompt_tokens_details": {"cached_tokens": 0},
                "completion_tokens_details": {"reasoning_tokens": 200},
            },
        },
    )


def run(
    handler: Callable[[dict[str, Any]], httpx.Response],
) -> tuple[list[dict[str, Any]], FakeDb, Any]:
    requests: list[dict[str, Any]] = []

    def transport(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        return handler(body)

    client = AsyncOpenAI(
        api_key="test",
        base_url=BASE_URL,
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)),
    )
    db = FakeDb()
    gateway = Gateway(client, load_registry(), db)
    try:
        result: Any = asyncio.run(gateway.complete("analyze", MESSAGES, AnalysisOut, CONTEXT))
    except ModelCallFailed as exc:
        result = exc
    return requests, db, result


def row(db: FakeDb, i: int) -> dict[str, object]:
    names = (
        "user_id space_id thread_id step role provider model input_tokens cached_input_tokens "
        "visual_tokens output_tokens reasoning_tokens cost_usd latency_ms ok error"
    ).split()
    return dict(zip(names, db.rows[i], strict=True))


def test_request_pins_provider_and_parameters() -> None:
    requests, db, result = run(lambda b: completion(json.dumps(VALID), b["model"]))
    body = requests[0]
    assert body["model"] == "openai/gpt-oss-20b"
    assert body["providerOptions"] == {"gateway": {"only": ["groq"]}}
    assert body["reasoning"] == {"effort": "low"}
    assert body["max_completion_tokens"] == 800
    assert body["store"] is False
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert result.output.narrative == "A package arrived."
    assert result.role == "analyze"


def test_success_writes_one_run_with_real_usage() -> None:
    _, db, _ = run(lambda b: completion(json.dumps(VALID), b["model"]))
    assert len(db.rows) == 1
    r = row(db, 0)
    assert r["ok"] is True and r["error"] is None
    assert (r["step"], r["role"], r["provider"]) == ("analyze", "analyze", "groq")
    assert (r["input_tokens"], r["output_tokens"], r["reasoning_tokens"]) == (1400, 350, 200)
    assert str(r["cost_usd"]) == "0.00021700"
    assert r["visual_tokens"] is None


def test_schema_mismatch_retries_once_with_the_error() -> None:
    answers = iter(['{"narrative": ""}', json.dumps(VALID)])
    requests, db, result = run(lambda b: completion(next(answers), b["model"]))
    assert len(requests) == 2
    assert "did not match the schema" in requests[1]["messages"][-1]["content"]
    assert [row(db, i)["error"] for i in range(2)] == ["schema", None]
    assert result.role == "analyze"


def test_second_schema_mismatch_fails_without_fallback() -> None:
    requests, db, result = run(lambda b: completion("not json", b["model"]))
    assert isinstance(result, ModelCallFailed)
    assert {r["model"] for r in requests} == {"openai/gpt-oss-20b"}
    assert len(db.rows) == 2


def test_provider_error_goes_to_fallback() -> None:
    def handler(body: dict[str, Any]) -> httpx.Response:
        if body["model"] == "openai/gpt-oss-20b":
            return httpx.Response(503, json={"error": {"message": "down"}})
        return completion(json.dumps(VALID), body["model"])

    requests, db, result = run(handler)
    assert requests[1]["model"] == "openai/gpt-4.1-mini"
    assert requests[1]["providerOptions"] == {"gateway": {"only": ["openai"]}}
    assert "reasoning" not in requests[1]
    assert result.role == "analyze_fallback"
    assert [(row(db, i)["role"], row(db, i)["error"]) for i in range(2)] == [
        ("analyze", "http 503"),
        ("analyze_fallback", None),
    ]


def test_timeout_goes_to_fallback() -> None:
    def handler(body: dict[str, Any]) -> httpx.Response:
        if body["model"] == "openai/gpt-oss-20b":
            raise httpx.ReadTimeout("slow")
        return completion(json.dumps(VALID), body["model"])

    _, db, result = run(handler)
    assert row(db, 0)["error"] == "timeout"
    assert result.role == "analyze_fallback"


def test_every_provider_down_fails() -> None:
    _, db, result = run(lambda b: httpx.Response(500, json={"error": {"message": "x"}}))
    assert isinstance(result, ModelCallFailed)
    assert len(db.rows) == 2


@pytest.mark.parametrize("answer", ["not json", json.dumps(VALID)])
def test_runs_never_contain_prompt_or_answer(answer: str) -> None:
    _, db, result = run(lambda b: completion(answer, b["model"]))
    for args in db.rows:
        for value in args:
            assert SECRET not in str(value) and "not json" not in str(value)
    assert SECRET not in str(result)
