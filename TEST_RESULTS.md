# SSSP MCP MVP v0.2 — Test Results

Run date: 2026-08-12

## Core test

PASS

Verified:
- create document
- append paragraph
- append math node
- MathJax parse validation
- replace node with expected checksum
- stale revision rejection
- Markdown export
- immutable snapshot

## MCP stdio smoke test

PASS

Verified lifecycle:
- `initialize` with protocol `2025-11-25`
- `notifications/initialized`
- `tools/list`
- 7 exposed SSSP tools
- `tools/call` create/append/validate/export/commit

## MCP Streamable HTTP smoke test

PASS

Verified:
- `POST /mcp/<token>` initialize
- HTTP `202` for `notifications/initialized`
- `tools/list`
- remote `tools/call`
- MCP protocol-version validation
- `Origin` allowlist rejection (`403`)
- `GET /mcp/<token>` returns `405` when server-initiated SSE is disabled
- secret endpoint path protection

## Damage regression fixtures

PASS

Current fixtures cover:
- decoded backspace/control-byte corruption (`\\b...` family)
- PUA markers
- zero-width markers
- unbalanced LaTeX braces
- `$` delimiter appearing inside canonical math node
- silent newline + `eg/eq/abla/...` escape-corruption risk signature

## Docker / deployment validation

PASS

GitHub Actions successfully builds the repository `Dockerfile` after all four test suites pass. The repo also contains a Render Blueprint (`render.yaml`) with `/healthz` health checks and an externally supplied `SSSP_ENDPOINT_TOKEN`.

## Known MVP limitations

- L3 semantic validation is heuristic, not a theorem/meaning checker.
- MathJax validation invokes a subprocess per math node; batch validation should replace this in a later version.
- No full multi-node transaction yet.
- No MCP resources/prompts yet; tools only.
- Remote v0.2 is stateless at the MCP transport layer and does not expose server-initiated SSE.
- URL-path token is for single-user development testing, not production OAuth/OIDC.
- Filesystem-backed canonical data requires persistent storage for production use.
