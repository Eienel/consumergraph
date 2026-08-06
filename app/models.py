from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Column(BaseModel):
    name: str
    type: str
    nullable: bool = True


class Asset(BaseModel):
    id: str
    urn: str | None = None
    name: str
    type: str
    platform: str
    owner: str
    domain: str
    criticality: int = Field(default=1, ge=1, le=5)
    columns: list[Column] = []
    queries: list[str] = []


class Edge(BaseModel):
    source: str
    target: str
    column_map: dict[str, list[str]] = {}


class Catalog(BaseModel):
    assets: list[Asset]
    edges: list[Edge]


class ChangeRequest(BaseModel):
    asset_id: str
    kind: Literal["rename", "remove", "type_change"]
    column: str
    new_name: str | None = None
    new_type: str | None = None


class WritebackRequest(BaseModel):
    analysis: dict

