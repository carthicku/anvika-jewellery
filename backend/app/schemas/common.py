"""Shared response building blocks."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer


def _weight(value: Decimal) -> str:
    return f"{value:.3f}"


# Weights in grams/carats, serialised as "4.250".
WeightStr = Annotated[Decimal, PlainSerializer(_weight, return_type=str, when_used="json")]


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    pages: int


class OkOut(BaseModel):
    ok: bool = True
    message: str | None = None


class StrictIn(BaseModel):
    """Base for request bodies: unknown fields are rejected, strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
