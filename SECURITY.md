# Security Policy

## Supported versions

Security fixes are accepted on the `main` branch for the latest release line.

## Reporting a vulnerability

Please report vulnerabilities **privately**:

- GitHub Security Advisory on this repository, or
- Email: `security@influencerforge.dev`

Do **not** open a public issue for security bugs.

## Local-first guarantees

- No telemetry to InfluencerForge developers.
- Vault content uses AES-256-GCM with an Argon2id-derived key.
- Cloud LLM API keys, when used, are stored locally in SQLite settings and sent only to the chosen provider.
