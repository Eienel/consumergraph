# ConsumerGraph

**ConsumerGraph is a DataHub-powered system that discovers how teams, dashboards, pipelines, and models converge on shared data, then turns those dependencies into enforceable contracts and safe migration code.**

The hackathon MVP combines two workflows:

- **ConsumerSpec** infers a dependency contract from lineage, queries, usage, ownership, and cross-domain consumption.
- **ChangeSafe** tests a proposed schema change against that contract, generates compatibility SQL and regression tests, and writes the approved decision back to DataHub.

## Why it exists

Repository tests know whether producer code works. They usually do not know that Finance, Marketing, Support, and an ML model all depend on the same column. DataHub contains that organizational dependency graph; ConsumerGraph converts it into actionable change protection.

## Current vertical slice

1. Select a shared dataset.
2. Calculate its cross-team and cross-domain convergence score.
3. Inspect inferred column dependencies and their evidence.
4. Propose a rename, removal, or type change.
5. See known affected consumers and explicit unknown coverage.
6. Generate compatibility SQL and regression tests.
7. Approve the decision and persist it locally or as a DataHub Document.

The analysis engine is deterministic. A local LLM may later explain results, but it is not allowed to decide whether a change is safe.

## Quick start

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://localhost:8000>.

The default `CONSUMERGRAPH_MODE=demo` requires no DataHub instance or paid API.

## DataHub write-back

Install the DataHub SDK extra:

```bash
pip install -e ".[datahub,dev]"
```

Configure:

```bash
CONSUMERGRAPH_MODE=datahub
DATAHUB_GMS_URL=http://localhost:8080
DATAHUB_GMS_TOKEN=<personal-access-token>
```

When a migration is approved, ConsumerGraph uses `DataHubClient` and `Document.create_document(...)` to publish the decision, generated SQL, tests, affected owners, confidence, and coverage warning. The document is linked to the source dataset when its URN is available.

For a rich local catalog, load the official showcase datapack:

```bash
datahub datapack load showcase-ecommerce
```

## Tests

```bash
pytest
```

## Safety model

- Observed usage is evidence, not automatically binding policy.
- Missing lineage is reported as unknown coverage.
- Generated migrations require human approval.
- Destructive changes with known consumers are blocked by default.
- No raw business-customer records are required; the MVP analyzes organizational metadata consumers.

## Roadmap

The same dependency intelligence can later power IncidentGraph, TimeFence, TrainServe, and—through a warehouse execution layer—business-customer journey convergence.

## License

Apache License 2.0.

