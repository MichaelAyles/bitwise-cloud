# Plugin & Frontend

## Context

Created a new `bitwise-cloud` Claude Code plugin — a thin Python MCP server that wraps the hosted Bitwise Cloud API. Users install via `/plugin marketplace add https://bitwise.mikeayles.com/plugin`. No local engine, no PDF parsing, no embeddings — just HTTP calls.

## New Package: `bitwise_cloud/`

At repo root, sibling to `mcp_embedded_docs/`.

### Files
- `__init__.py` — package init with version
- `config.py` — API key/URL from env vars or `~/.config/bitwise-cloud/config.json`
- `client.py` — async httpx client for all API endpoints + local file hashing
- `server.py` — FastMCP server with 6 tools (set_api_key, list_docs, upload_doc, check_progress, search_docs, find_register)
- `__main__.py` — entry point: `python -m bitwise_cloud serve`

## New Plugin: `plugins/bitwise-cloud/`

- `.claude-plugin/plugin.json` — metadata
- `.mcp.json` — MCP server config
- `skills/setup/SKILL.md` — guide to get API key and configure
- `skills/list-docs/SKILL.md` — scan local PDFs, check cloud status
- `skills/upload-doc/SKILL.md` — upload PDF, monitor progress
- `skills/search-docs/SKILL.md` — search cloud index

## Modified Files
- `pyproject.toml` — added `bitwise_cloud` package and CLI entry point
- `.claude-plugin/marketplace.json` — added cloud plugin entry
- `frontend/src/pages/Setup.tsx` — updated plugin tab to show marketplace install command
