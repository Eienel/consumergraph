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
    columns: list[Column] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)


class Edge(BaseModel):
    source: str
    target: str
    hops: int = Field(default=1, ge=1)
    column_map: dict[str, list[str]] = Field(default_factory=dict)


class Catalog(BaseModel):
    assets: list[Asset]
    edges: list[Edge]


class ChangeRequest(BaseModel):
    asset_id: str
    kind: Literal["rename", "remove", "type_change"]
    column: str
    new_name: str | None = None
    new_type: str | None = None
    replacement_relation: str | None = None


class WritebackRequest(BaseModel):
    analysis: dict
