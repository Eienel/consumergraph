from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.datahub_mcp import DataHubMcpCatalog
from app.engine import ConsumerGraphEngine
from app.mcp_client import McpClient
from app.models import ChangeRequest
from app.writeback import save_writeback


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only ChangeSafe validation against a live DataHub MCP endpoint.")
    parser.add_argument("--column", required=True, help="Existing source column to pressure-test")
    parser.add_argument("--new-name", required=True, help="Proposed replacement column name")
    parser.add_argument("--max-hops", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument(
        "--writeback",
        action="store_true",
        help="After the read proof, persist the reviewed decision through DataHub MCP save_document.",
    )
    args = parser.parse_args()

    url = required_env("DATAHUB_MCP_URL")
    urn = required_env("DATAHUB_SOURCE_URN")
    client = McpClient(url, token=os.environ.get("DATAHUB_MCP_TOKEN"))
    adapter = DataHubMcpCatalog(client)
    repository = adapter.load(urn, max_hops=args.max_hops)
    source = repository.catalog.assets[0]
    if args.column not in {field.name for field in source.columns}:
        available = ", ".join(field.name for field in source.columns[:20])
        raise SystemExit(f"Column {args.column!r} was not found. First available fields: {available}")
    adapter.enrich_column(repository, source.id, args.column, max_hops=args.max_hops)
    analysis = ConsumerGraphEngine(repository).analyze_change(
        ChangeRequest(asset_id=source.id, kind="rename", column=args.column, new_name=args.new_name)
    )
    summary = {
        "mode": "live-datahub-read-only",
        "source": {"id": source.id, "urn": source.urn, "name": source.name},
        "schema_fields_loaded": len(source.columns),
        "lineage_consumers_loaded": len(repository.catalog.assets) - 1,
        "query_examples_loaded": len(source.queries),
        "verdict": analysis["verdict"],
        "severity": analysis["severity"],
        "affected_consumers": analysis["known_affected_consumers"],
        "unknown_coverage": analysis["unknown_coverage"],
    }
    if args.writeback:
        os.environ["CONSUMERGRAPH_MODE"] = "mcp"
        writeback = save_writeback(analysis, Path("runtime") / "live-validation")
        structured = writeback.get("datahub_result", {}).get("structuredContent", {})
        document_urn = structured.get("urn") if isinstance(structured, dict) else None
        if not document_urn:
            raise RuntimeError("DataHub save_document did not return a document URN")
        readback_result = client.call_tool("get_entities", {"urns": [document_urn]})
        readback_payload = readback_result.get("structuredContent")
        if readback_payload is None:
            texts = [
                item.get("text", "")
                for item in readback_result.get("content", [])
                if item.get("type") == "text"
            ]
            readback_payload = json.loads("\n".join(texts)) if texts else []
        entities = readback_payload if isinstance(readback_payload, list) else [readback_payload]
        if not any(isinstance(entity, dict) and entity.get("urn") == document_urn for entity in entities):
            raise RuntimeError(f"DataHub document could not be read back after save: {document_urn}")
        writeback["verified_readback"] = {"success": True, "urn": document_urn}
        summary["writeback"] = writeback
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
