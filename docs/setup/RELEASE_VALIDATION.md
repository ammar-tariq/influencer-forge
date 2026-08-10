# Cross-platform release validation

InfluencerForge targets **Windows, macOS, and Linux** desktop builds. CI assembles portable Python and runs `tauri-action` on a matrix; this doc is the human sign-off checklist.

## Automated (CI)

| Check | Where |
|-------|--------|
| Lint / typecheck / unit tests | `.github/workflows/lint.yml` |
| Assemble portable Python + Tauri bundles | `.github/workflows/build.yml` (macos / ubuntu / windows) |

Trigger a release build with a `v*` tag or `workflow_dispatch`.

## Manual smoke (each OS you ship)

1. Install the artifact (DMG / AppImage / NSIS).
2. App starts; orchestrator health at `http://127.0.0.1:8765/api/health`.
3. Splash bootstrap completes (model downloads skipped unless `IFORGE_ENABLE_MODEL_DOWNLOADS=1`).
4. Create an influencer → Create post (stub or real ComfyUI).
5. Settings → System shows CPU/RAM (GPU via `nvidia-smi` on NVIDIA hosts; “Apple Silicon (MPS)” on Mac).
6. Scheduler → Export `.ics` opens/downloads; Google sync only after Settings OAuth.
7. Talking head: ffmpeg on PATH; Wav2Lip after `scripts/install-wav2lip.sh` + ComfyUI restart.
8. Full reset from Settings recovers a clean local store.

## Out of scope for CI

- Multi-GB SDXL / FaceID weights (download separately or symlink via `IFORGE_EXTRA_MODEL_DIRS`)
- GPU OOM behavior on every device class
- Code-signing / notarization secrets (configure in the release environment when ready)
