# Public contracts

The stable seam between this public CLI and the LUDO **gateway** (the single public
door over the broker). The CLI depends **only** on what's here — never on the agent
or NATS.

- `openapi.yaml` — **Contract A** (REST + SSE): the gateway's public API — migrations
  (list / detail / approve) + resumable event stream + health/status.
- `session-event.schema.json` — **Contract B** (events): the lifecycle event envelope
  the CLI consumes when streaming a migration.

**Source of truth is the gateway** (`euroblaze/ludo-gateway/contracts/`). These files
are *published copies* synced on intentional contract releases. Do not hand-edit;
re-vendor from the gateway.
