# SSSP MCP MVP v0.1 — Test Results

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

## Damage regression fixtures

PASS

Current fixtures cover:
- decoded backspace/control-byte corruption (`\\b...` family)
- PUA markers
- zero-width markers
- unbalanced LaTeX braces
- `$` delimiter appearing inside canonical math node
- silent newline + `eg/eq/abla/...` escape-corruption risk signature

## Known MVP limitations

- L3 semantic validation is heuristic, not a theorem/meaning checker.
- MathJax validation invokes a subprocess per math node; batch validation should replace this in a later version.
- No full multi-node transaction yet.
- No MCP resources/prompts yet; tools only.
- No HTTP/authentication; stdio only.
