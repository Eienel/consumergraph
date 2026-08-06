from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def render_markdown(analysis: dict) -> str:
    change = analysis["change"]
    affected = analysis["known_affected_consumers"]
    lines = [
        f"# ConsumerGraph change decision: {change['asset_id']}.{change['column']}",
        "",
        f"- Verdict: **{analysis['verdict']}**",
        f"- Severity: **{analysis['severity']}**",
        f"- Change type: `{change['kind']}`",
        f"- Known affected consumers: **{len(affected)}**",
        "",
        "## Affected consumers",
        "",
    ]
    for item in affected:
        lines.append(f"- {item['name']} ({item['type']}) — owner: {item['owner']}, domain: {item['domain']}")
    lines.extend(
        [
            "",
            "## Compatibility SQL",
            "",
            "```sql",
            analysis["generated"]["compatibility_sql"],
            "```",
            "",
            "## Regression test",
            "",
            "```sql",
            analysis["generated"]["regression_tests"],
            "```",
            "",
            f"> Coverage warning: {analysis['unknown_coverage']}",
        ]
    )
    return "\n".join(lines)


def save_writeback(analysis: dict, runtime_dir: Path) -> dict:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    doc_id = _slug(f"consumergraph-{analysis['change']['asset_id']}-{analysis['change']['column']}-{timestamp}")
    markdown = render_markdown(analysis)
    record = {"id": doc_id, "created_at": timestamp, "markdown": markdown, "analysis": analysis}
    path = runtime_dir / f"{doc_id}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    mode = os.getenv("CONSUMERGRAPH_MODE", "demo").lower()
    if mode != "datahub":
        return {"mode": "demo", "document_id": doc_id, "local_path": str(path), "markdown": markdown}

    try:
        from datahub.sdk import DataHubClient, Document
    except ImportError as exc:
        raise RuntimeError("Install the DataHub extra with: pip install -e '.[datahub]'") from exc

    client = DataHubClient.from_env()
    source_urn = analysis["source"].get("urn")
    related_assets = [source_urn] if source_urn else []
    doc = Document.create_document(
        id=doc_id,
        title=f"ConsumerGraph decision: {analysis['source']['name']}.{analysis['change']['column']}",
        text=markdown,
        subtype="Runbook",
        related_assets=related_assets,
        custom_properties={
            "consumergraph.verdict": analysis["verdict"],
            "consumergraph.severity": analysis["severity"],
        },
    )
    client.entities.upsert(doc)
    return {"mode": "datahub", "document_id": doc_id, "urn": str(doc.urn), "markdown": markdown}

