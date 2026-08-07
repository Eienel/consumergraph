# ChangeSafe architecture

## Prize-focused boundary

ChangeSafe owns the last mile between DataHub impact context and a reviewable
code change. It does not rebuild DataHub search, lineage, query history,
contracts, or catalog chat.

```text
DataHub MCP
  get_entities + list_schema_fields + get_lineage + get_dataset_queries
        |
        v
Deterministic impact engine
  affected consumers + evidence + unknown coverage
        |
        v
Change package
  compatibility SQL + regression SQL + migration note + impact JSON
        |
        +--> reviewed Git branch and commit
        |
        +--> save_document decision in DataHub
```

## Deliberate constraints

- No paid model or API is required.
- An LLM never decides whether a breaking change is safe.
- Missing query history degrades confidence; it does not erase lineage.
- Generated code always requires human review.
- Git application refuses dirty repositories and existing destination files.
- Demo and MCP modes are explicit. There is no automatic mock fallback.

## Laptop capacity decision

The development machine has roughly 8 GB total RAM. DataHub Quickstart itself
recommends allocating 8 GB or more to Docker, so running the full stack here
would be unreliable. Verification is split honestly:

1. Real SQLite execution proves the break and repair mechanism.
2. A real HTTP server contract test proves MCP lifecycle, session, and tool calls.
3. A temporary real Git repository proves branch and commit creation.
4. Live DataHub verification remains a deployment gate requiring an authenticated
   hosted tenant or a larger machine for Quickstart plus the showcase datapack.
