"""El esquema estricto que se manda a los proveedores (Groq pide additionalProperties: false)."""

from collections.abc import Iterator
from enum import StrEnum
from typing import Any

import pytest
from pydantic import BaseModel, Field

from artemisa.core.schemas import AnalysisOut, DescribeOut, LiveReadOut, ReasoningOut
from artemisa.providers.gateway import UNSUPPORTED_KEYWORDS, provider_schema


class Color(StrEnum):
    red = "red"
    blue = "blue"


class Inner(BaseModel):
    label: str = Field(min_length=1, max_length=20)
    score: float | None = Field(default=None, ge=0, le=1)


class Outer(BaseModel):
    name: str = Field(min_length=1)
    color: Color
    inner: Inner
    items: list[Inner] = []
    maybe: Inner | None = None
    count: int = Field(default=0, ge=0, le=50)


def objects(node: Any) -> Iterator[dict[str, Any]]:
    """Todos los objetos del esquema, incluidos los de $defs."""
    if isinstance(node, list):
        for item in node:
            yield from objects(item)
    elif isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            yield node
        for value in node.values():
            yield from objects(value)


def keys(node: Any) -> Iterator[str]:
    if isinstance(node, list):
        for item in node:
            yield from keys(item)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key != "properties":  # los nombres de campo no son palabras clave
                yield key
            yield from keys(value)


def test_every_object_forbids_additional_properties() -> None:
    schema = provider_schema(Outer)
    found = list(objects(schema))
    assert len(found) == 2  # Outer e Inner (en $defs)
    assert all(obj["additionalProperties"] is False for obj in found)


def test_every_property_is_required() -> None:
    schema = provider_schema(Outer)
    for obj in objects(schema):
        assert obj["required"] == list(obj["properties"])


def test_optional_fields_still_accept_null() -> None:
    props = provider_schema(Outer)["properties"]
    assert {"type": "null"} in props["maybe"]["anyOf"]
    inner = provider_schema(Outer)["$defs"]["Inner"]["properties"]
    assert {"type": "null"} in inner["score"]["anyOf"]


def test_unsupported_keywords_are_removed_everywhere() -> None:
    assert not UNSUPPORTED_KEYWORDS & set(keys(provider_schema(Outer)))


def test_refs_and_enums_are_kept() -> None:
    schema = provider_schema(Outer)
    assert schema["properties"]["color"] == {"$ref": "#/$defs/Color"}
    assert schema["$defs"]["Color"]["enum"] == ["red", "blue"]


def test_a_field_named_like_a_keyword_is_kept() -> None:
    class Tricky(BaseModel):
        format: str
        default: int

    assert set(provider_schema(Tricky)["properties"]) == {"format", "default"}


def test_pydantic_schema_is_not_modified() -> None:
    before = Outer.model_json_schema()
    provider_schema(Outer)
    assert Outer.model_json_schema() == before
    assert "additionalProperties" not in before


@pytest.mark.parametrize("model", [DescribeOut, AnalysisOut, ReasoningOut, LiveReadOut])
def test_real_output_schemas_are_strict(model: type[BaseModel]) -> None:
    schema = provider_schema(model)
    for obj in objects(schema):
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])
    assert not UNSUPPORTED_KEYWORDS & set(keys(schema))
