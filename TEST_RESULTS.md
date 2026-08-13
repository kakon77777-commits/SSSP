# SSSP MCP v0.3 — Test Results

Run date: 2026-08-13

## Cloudflare Worker verification

PASS

Verified in the Cloudflare Workers runtime:

- `GET /healthz` and `GET /.well-known/sssp.json` advertise the public unauthenticated endpoint;
- MCP `initialize` with protocol `2025-11-25`;
- `tools/list` exposes exactly the seven SSSP tools;
- create, append, validate, read, replace, export, and commit tool calls;
- revision and checksum-protected replacement;
- immutable/idempotent snapshot creation;
- canonical state survives Durable Object eviction and a new MCP request;
- untrusted browser Origin rejection (`403`);
- actual request-body size enforcement even with a misleading `Content-Length` (`413`).

Vitest result: 2 files passed, 6 tests passed.

## Type, site, dependency, and bundle checks

PASS

- `wrangler types` generated the configured bindings;
- strict TypeScript checking passed;
- both localized public pages, seven tool names, metadata, local assets, PNG, and deployment config validated;
- production dependency audit reported 0 vulnerabilities;
- Wrangler deployment dry-run bundled the Worker and recognized the Durable Object, rate-limit, and asset bindings;
- local startup profiling completed successfully (3.63 MiB bundle, 836.95 KiB gzip, 214.2 ms active CPU on this machine).

## Python reference implementation regressions

PASS

- canonical core workflow;
- damage regression fixtures;
- MCP stdio lifecycle and seven tools;
- token-scoped local Streamable HTTP lifecycle, protocol validation, Origin rejection, and disabled server-initiated SSE.

## Known research-MVP boundaries

- The public endpoint is intentionally unauthenticated and shared. It is not suitable for secrets, personal data, private drafts, credentials, or confidential research.
- Anyone who knows a `document_id` can attempt to read or mutate its nodes; `actor` is an unverified display label.
- Rate limits and storage quotas reduce abuse and cost exposure but are not authentication or authorization.
- L3 semantic validation remains heuristic; SSSP does not claim theorem or meaning verification.
- There is no multi-node transaction tool, private tenant ownership boundary, or MCP resources/prompts surface yet.
- The local Python remote server remains a v0.2 reference path with filesystem storage; the public v0.3 Worker uses Durable Object SQLite.
