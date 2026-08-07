# Example reviewed output

Proposed change: rename `customer_360.customer_id` to `buyer_id`.

ChangeSafe found four known downstream consumers across Finance, Growth,
Support, and ML. The raw producer change failed with `no such column:
customer_id`. The compatibility view in this directory restored all four
consumers, and the regression query returned zero alias mismatches.

Runtime packages also include complete impact evidence in `impact.json` and the
owner-facing migration plan in `MIGRATION.md`.
