# Cursor setup for InfluencerForge

This guide gets Cursor ready so agents and humans share the same path.

## 1. Open the repo

1. **File → Open Folder…** → select `influencer-forge`
2. When prompted, **Trust** the workspace
3. Install recommended extensions (popup or Extensions view): ESLint, Prettier, Rust Analyzer, Even Better TOML, Python / basedpyright

## 2. One-time toolchains (host machine)

Run in Cursor’s terminal:

```bash
# Node
node -v   # 20+

# Rust
rustc --version || curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Project deps
npm install
cd forge-python && uv sync --all-groups && cd ..
```

macOS also needs Xcode CLT; Linux needs Tauri webkit packages (see Tauri prerequisites).

## 3. Point Cursor Agent at project rules

- `AGENTS.md` at repo root is auto-discovered by many agents
- `.cursor/rules/*.mdc` enforce stack conventions while editing matching files
- Prefer prompts like: “Follow AGENTS.md and complete the next roadmap todo with tests + docs”

## 4. Recommended agent workflow

1. Read `PROJECT_SPECIFICATION.md` + relevant `docs/modules/*`
2. Implement one todo/pass
3. Add/adjust tests
4. Update docs/`CHANGELOG` if behavior changed
5. Commit with Conventional Commit + `AI-Generated: true` trailer
6. Ask before push

## 5. Dev servers inside Cursor

**Terminal A — API only**

```bash
cd forge-python && uv run forge-orchestrator
```

**Terminal B — UI only**

```bash
npm run dev
```

**Full desktop**

```bash
npm run tauri dev
```

## 6. If the agent needs something from you

Typical asks:

- Approve installing system packages (webkit, Xcode CLT)
- Confirm cloud API keys (never commit them)
- Confirm push/release

You do **not** need HuggingFace models for Phase 1 stub mode.
