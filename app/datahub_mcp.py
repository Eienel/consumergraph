from __future__ import annotations

import json
import re
from typing import Any

from .catalog import CatalogRepository
from .mcp_client import McpClient
from .models import Asset, Catalog, Column, Edge


def _tool_payload(result: dict[str, Any]) -> Any:
    if result.get("structuredContent") is not None:
        return result["structuredContent"]
    texts = [item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"]
    text = "\n".join(texts).strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def _items(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        if isinstance(payload.get(key), list):
            return [item for item in payload[key] if isinstance(item, dict)]
    for value in payload.values():
        if isinstance(value, dict):
            found = _items(value, keys)
            if found:
                return found
    return []


def _first(value: Any, *paths: str, default: Any = None) -> Any:
    for path in paths:
        current = value
        for part in path.split("."):
            if isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if index < len(current) else None
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                current = None
                break
        if current not in (None, "", []):
            return current
    return default


def _id_from_urn(urn: str) -> str:
    match = re.search(r",([^,()]+),(?:PROD|DEV|TEST)\)\s*$", urn)
    raw = match.group(1) if match else urn.rsplit(":", 1)[-1]
    return re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_").lower()


class DataHubMcpCatalog:
    """Hydrates the deterministic engine through DataHub's official MCP tools."""

    def __init__(self, client: McpClient):
        self.client = client

    def _entity(self, item: dict[str, Any], fallback_urn: str) -> Asset:
        urn = str(_first(item, "urn", "entity.urn", default=fallback_urn))
        platform = _first(item, "platform.name", "platform", "properties.platform", default="datahub")
        if isinstance(platform, dict):
            platform = platform.get("name") or platform.get("displayName") or "datahub"
        return Asset(
            id=_id_from_urn(urn),
            urn=urn,
            name=str(_first(item, "properties.name", "name", "entity.name", default=_id_from_urn(urn))),
            type=str(_first(item, "type", "entity.type", default="dataset")).lower(),
            platform=str(platform),
            owner=str(
                _first(
                    item,
                    "ownership.owners.0.owner.properties.displayName",
                    "ownership.owners.0.owner.username",
                    "owners.0.owner.properties.displayName",
                    "owner",
                    default="Unassigned",
                )
            ),
            domain=str(
                _first(
                    item,
                    "domain.domain.properties.name",
                    "domain.properties.name",
                    "domain.name",
                    "domain",
                    default="Unassigned",
                )
            ),
            criticality=3,
        )

    def load(self, source_urn: str, max_hops: int = 3) -> CatalogRepository:
        entity_result = self.client.call_tool("get_entities", {"urns": [source_urn]})
        entity_items = _items(_tool_payload(entity_result), ("entities", "results", "searchResults"))
        source = self._entity(entity_items[0] if entity_items else {}, source_urn)

        fields = _items(
            _tool_payload(self.client.call_tool("list_schema_fields", {"urn": source_urn})),
            ("fields", "schemaFields", "results"),
        )
        source.columns = [
            Column(
                name=str(_first(field, "fieldPath", "name", "field", default="unknown")),
                type=str(_first(field, "type", "nativeDataType", "schemaFieldDataType", default="UNKNOWN")),
                nullable=bool(_first(field, "nullable", default=True)),
            )
            for field in fields
        ]

        query_items = _items(
            _tool_payload(self.client.call_tool("get_dataset_queries", {"urn": source_urn, "count": 20})),
            ("queries", "results"),
        )
        source.queries = [
            str(_first(query, "properties.statement.value", "query", "sql", "text"))
            for query in query_items
            if _first(query, "properties.statement.value", "query", "sql", "text")
        ]

        lineage_items = _items(
            _tool_payload(
                self.client.call_tool(
                    "get_lineage",
                    {"urn": source_urn, "upstream": False, "max_hops": max_hops, "max_results": 100},
                )
            ),
            ("lineage", "results", "entities", "searchResults"),
        )
        lineage_by_urn = {
            str(_first(item, "urn", "entity.urn", default="")): item for item in lineage_items
            if _first(item, "urn", "entity.urn", default="")
        }
        downstream_urns = [urn for urn in lineage_by_urn if urn != source_urn]
        details: dict[str, dict[str, Any]] = {}
        if downstream_urns:
            detail_result = self.client.call_tool("get_entities", {"urns": downstream_urns})
            for item in _items(_tool_payload(detail_result), ("entities", "results", "searchResults")):
                urn = str(_first(item, "urn", "entity.urn", default=""))
                if urn:
                    details[urn] = item

        assets = [source]
        edges: list[Edge] = []
        for urn in downstream_urns:
            lineage_item = lineage_by_urn[urn]
            asset = self._entity(details.get(urn, lineage_item), urn)
            assets.append(asset)
            degree = _first(lineage_item, "degree", "hops", default=1)
            try:
                hops = max(1, int(str(degree).rstrip("+")))
            except ValueError:
                hops = 1
            edges.append(Edge(source=source.id, target=asset.id, hops=hops))
        return CatalogRepository.from_catalog(Catalog(assets=assets, edges=edges))

    def enrich_column(self, repository: CatalogRepository, source_id: str, column: str, max_hops: int = 3) -> None:
        source = repository.get_asset(source_id)
        if not source.urn:
            return
        lineage_items = _items(
            _tool_payload(
                self.client.call_tool(
                    "get_lineage",
                    {
                        "urn": source.urn,
                        "column": column,
                        "upstream": False,
                        "max_hops": max_hops,
                        "max_results": 100,
                    },
                )
            ),
            ("lineage", "results", "entities", "searchResults"),
        )
        edges = {edge.target: edge for edge in repository.catalog.edges if edge.source == source_id}
        for item in lineage_items:
            urn = str(_first(item, "urn", "entity.urn", default=""))
            target_id = _id_from_urn(urn) if urn else ""
            edge = edges.get(target_id)
            if not edge:
                continue
            targets = _first(item, "lineageColumns", default=[])
            edge.column_map[column] = [str(target) for target in targets] if targets else [column]
