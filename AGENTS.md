# AGENTS.md — guidance for AI coding agents (Cursor and others)

This repository is **open source**. Prefer clarity, documentation, and tests over clever shortcuts.

## Source of truth

1. `PROJECT_SPECIFICATION.md` — product requirements and schema
2. `README.md` + `docs/` — contributor path
3. This file — agent operating rules

## Locked MVP decisions

- Generation backend Phase 1: **stub** (Pillow), not ComfyUI weights in git
- Python runtime Phase 1: **system Python / uv venv**; embedded portable Python later
- Orchestrator listens on `127.0.0.1:8765` only

## Required practices

- Keep the phase flow: scaffold → process/DB → splash/UI → wizard → queue → history → ComfyUI → advanced → packaging
- Integrate tests with every module change
- Document user-facing and contributor-facing changes
- After completing an AI pass, create a git commit with trailer `AI-Generated: true`
- Do **not** push unless a human explicitly asks
- Do **not** edit plan files under `.cursor/plans/` unless asked
- Ask the human when blocked (credentials, product choices, destructive git ops)

## Cursor-specific

- Project rules live in `.cursor/rules/`
- Setup walkthrough: `docs/setup/CURSOR.md`
- Recommended extensions: see `.vscode/extensions.json`

## Useful commands

```bash
npm run tauri dev
npm test
cd forge-python && uv run pytest -q && uv run forge-orchestrator
```
