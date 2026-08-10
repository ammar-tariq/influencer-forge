# Contributing to InfluencerForge

Thanks for helping build a local-first, open-source influencer studio.

## Ground rules

1. Follow [PROJECT_SPECIFICATION.md](./PROJECT_SPECIFICATION.md) — do not invent alternate architecture without discussion.
2. Every feature ships with **tests** (Python pytest and/or Vitest) and **docs** updates when behavior changes.
3. Use **Conventional Commits**: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`.
4. AI-assisted commits must include the trailer:

   ```
   AI-Generated: true
   ```

5. Prefer small PRs aligned to the roadmap phases.

## Local setup

See [README.md](./README.md) and [docs/setup/CURSOR.md](./docs/setup/CURSOR.md).

## Development loop

1. Start API: `cd forge-python && uv run forge-orchestrator`
2. Or full app: `npm run tauri dev`
3. Run tests before opening a PR:

```bash
npm test && npm run typecheck
cd forge-python && uv run ruff check src tests && uv run pytest -q
```

## PR checklist

- [ ] Tests added/updated
- [ ] Docs updated (`README`, `docs/modules`, `CHANGELOG` as needed)
- [ ] No secrets committed
- [ ] Lint/typecheck pass
- [ ] Screenshots for UI changes

## Code of conduct

See [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).
