from __future__ import annotations

import json
from pathlib import Path

from .models import Asset, Catalog


class CatalogRepository:
    def __init__(self, path: Path):
        self.path = path
        self.catalog = Catalog.model_validate_json(path.read_text(encoding="utf-8"))
        self.assets = {asset.id: asset for asset in self.catalog.assets}

    @classmethod
    def from_catalog(cls, catalog: Catalog) -> "CatalogRepository":
        repository = cls.__new__(cls)
        repository.path = None
        repository.catalog = catalog
        repository.assets = {asset.id: asset for asset in catalog.assets}
        return repository

    def get_asset(self, asset_id: str) -> Asset:
        try:
            return self.assets[asset_id]
        except KeyError as exc:
            raise KeyError(f"Unknown asset: {asset_id}") from exc

    def outgoing(self, asset_id: str):
        return [edge for edge in self.catalog.edges if edge.source == asset_id]

    def downstream(self, asset_id: str, max_hops: int = 8) -> list[tuple[Asset, int]]:
        seen = {asset_id}
        queue = [(asset_id, 0)]
        results: list[tuple[Asset, int]] = []
        while queue:
            current, hops = queue.pop(0)
            if hops >= max_hops:
                continue
            for edge in self.outgoing(current):
                if edge.target in seen:
                    continue
                seen.add(edge.target)
                next_hops = hops + 1
                asset = self.get_asset(edge.target)
                results.append((asset, next_hops))
                queue.append((edge.target, next_hops))
        return results

    def serialize(self) -> dict:
        return json.loads(self.catalog.model_dump_json())
