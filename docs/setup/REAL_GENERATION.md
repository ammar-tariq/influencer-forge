# When does InfluencerForge stop being “just CRUD”?

**Answer:** when Dashboard readiness is `mode: real` and History shows `model_used` other than `stub`.

## Checklist

| Step | Command / action |
|------|------------------|
| 1. Clone ComfyUI | `git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git src-tauri/resources/comfyui/ComfyUI` |
| 2. Install ComfyUI Python deps | follow upstream ComfyUI README inside that folder |
| 3. Drop SDXL checkpoint | `.../ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors` |
| 4. Enable flag | `export IFORGE_ENABLE_COMFYUI=1` |
| 5. Launch | `npm run tauri dev` or `uv run forge-orchestrator` |
| 6. Verify API | `curl localhost:8765/api/readiness` → `"real_ready": true` |

## Stub vs real

- Default: stub placeholders allowed (`IFORGE_ALLOW_STUB_FALLBACK=1`) so UI/queue can be developed offline.
- Generate page toggle **Require real ComfyUI output** sets `require_real: true` and fails the job instead of painting a fake PNG.
- Set `IFORGE_ALLOW_STUB_FALLBACK=0` globally to force real-only.

## Guided create + scene builder

1. **Studio home** checklist links you through Create → Influencers → Generate. Use the sidebar **Privacy vault** switch for NSFW.
2. **New influencer** is 3 steps: Personality → Face (gender) → Body (height, figure, skin, etc.). After create, the app queues **four** full-body identity shots (`POST /api/generations/batch`) and opens that influencer’s **profile**.
3. On the profile, **Face lock setup** shows those options as they finish (queue concurrency is 1). Edit the prompt and **Generate 4 face options** again, re-roll a card, or upload a Face Seed, then **Use this face**. Until locked, later gens won’t use FaceID / img2img identity.
4. **Edit** personality/looks on the profile anytime (`PATCH` APIs). Changing hair/eyes/ethnicity while locked shows a “re-lock face” banner (lock is not auto-cleared).
5. **Influencers** (sidebar) lists everyone; open a card for personality/looks, all their posts, Create post, or Archive.
6. **Library** (`/history`) filters with `?influencer={id}` — also linked from each profile (“All posts” / “Their posts”). Open a post and use **Delete post** (confirm) to remove it and its media (`DELETE /api/generations/{id}`).
7. **Create post** defaults to **full body** and offers Pose / Dressing / Setting presets (including nude). You can still add free notes. Wardrobe (if assigned) is the sole clothing source; dressing presets apply only when no wardrobe is selected. Nude/topless and wardrobe cannot be combined.
8. Progress for the active job shows in the right-hand Progress panel.

## Prompt override contract

## Face Seed vs looks sliders

When a Face Seed / base portrait is set and the job is **not** identity-explore (Create post, Library regenerate):

- ComfyUI runs **FaceID** (or img2img fallback) with the reference image.
- Text looks prompt is **body sliders only** — age, ethnicity, nationality, hair, eyes, and style text are omitted so they cannot invent a different person.
- If FaceID **and** img2img are unavailable, the job **fails** (no plain txt2img / stub) so a different face is never invented.
- Identity-explore (wizard / “try faces”) skips the reference on purpose.

Clothing and identity are resolved on the orchestrator (`prompt_layers.resolve_prompt_layers`) before LLM expand / ComfyUI:

| Priority | Clothing source |
|----------|-----------------|
| 1 | **Wardrobe** keywords (exclusive) — notes clothing words are stripped |
| 2 | **Dressing** preset (when no wardrobe) |
| 3 | Custom notes (vibe / expression / lighting only when wardrobe is set) |

- Wardrobe + nude/topless dressing is rejected (`400` / UI clears the other).
- NSFW path no longer injects blanket `nude` when resolved clothing is a wardrobe or named outfit.
- **Identity explore** (`identity_explore: true` on create/batch/regenerate during face setup): no FaceID / img2img reference so each shot can be a new face; selected looks traits stay in the prompt.
- **Create post** (after face lock): FaceID/img2img on; hybrid looks (age/gender/ethnicity/nationality/body kept; hair/eyes omitted when a face ref is active); prompt varies pose, clothing, setting, framing, non-clothing notes.

## Face consistency (FaceID → img2img)

When a look has a **Face Seed** or locked **base portrait**, generation prefers:

1. **IP-Adapter FaceID Plus SDXL** (`image_ipadapter_faceid.json`) when `ComfyUI_IPAdapter_plus` + FaceID weights are installed → `model_used` = `sdxl-faceid`
2. Else **img2img** (`image_img2img.json`): soft-canvas head prior + moderate denoise (~0.55–0.68, cap 0.72) → `sdxl-img2img`
3. Else plain txt2img (`sdxl`)

Install notes: `src-tauri/resources/comfyui/README.md`. Readiness item `ipadapter_faceid` is optional and does not block core `real` mode.

Bikini/lingerie prompts no longer auto-append `nude` or ban the outfit in negatives. Upload a Face Seed for the strongest lock.

## Video (AnimateDiff)

1. Install **ComfyUI-AnimateDiff-Evolved** + **ComfyUI-VideoHelperSuite**, **ffmpeg** / `imageio-ffmpeg`, and an `mm_sdxl_*` motion module (see ComfyUI README).
2. Generate with type **Video**. Output is `media/generations/{id}.mp4` when VHS encodes successfully (`model_used` = `animate_diff` or `animate_diff-faceid`). Defaults are Mac-safe: **12 frames @ 384×640**, 6 fps (~2s), autoplay muted in the UI.
3. FaceID on video is **on by default** at that light size so gender/identity stay locked. If ComfyUI OOMs, set `IFORGE_VIDEO_FACEID=0`.
4. Without motion modules / ffmpeg, the job errors (or falls back to stub if stub fallback is allowed). Library / Generate preview use `<video>` only for real `.mp4` paths.

## Explicit / NSFW generations

For **Adult** or **18+** influencers (Adult alone is enough — you do not need the separate 18+ rating):

1. Open **Generate**, select the influencer (NSFW mode defaults on for Adult and 18+).
2. Enable **NSFW / explicit mode** (or use words like `topless` / `nude` in the prompt).
3. Prefer waist-up / full-body phrasing — face-only “portrait” framing hides the body.
4. Leave Wardrobe empty (skipped automatically in NSFW mode).

**Blocked:** Family / Teen age ratings, and looks age under 18.

The pipeline then uses adult framing + clothing negatives, and injects an NSFW LoRA when present under `ComfyUI/models/loras/` (filename must contain `nsfw`, `nude`, or `explicit`).

**Recommended LoRA (download yourself — not in git):**

1. Download the SDXL `.safetensors` from  
   [Muapi fanvue woman033 NSFW photorealistic character LoRA (SDXL)](https://huggingface.co/Muapi/fanvue-onlyfans-ai-model-woman033-nsfw-photorealistic-character-lora-sdxl-sd1.5)
2. Install:
   ```bash
   ./scripts/install-nsfw-lora.sh ~/Downloads/fanvue-onlyfans-ai-model-woman033-nsfw-photorealistic-character-lora-sdxl-sd1.5.safetensors
   ```
   Note: this is a **character** LoRA — it can tug against Face Seed identity. Prefer a generic NSFW body LoRA if you need strict face lock.

RealVisXL can still refuse some scenes; stronger wording and re-rolls help.

### Privacy Vault

1. In the sidebar, turn on **Privacy vault** and set a PIN (min 4 chars). Setup leaves the vault **unlocked**.
2. With the vault on, new NSFW jobs **auto-vault**: encrypt to `vault/{id}.bin`, write a blurred teaser, delete cleartext PNG/thumb.
3. **Library** and influencer profiles show blur teasers for vaulted rows while the vault is on. Opening a vaulted post always asks for the PIN again.
4. While the vault is off, vaulted NSFW posts are hidden. Turning it back on (PIN) encrypts any pending NSFW and shows teasers.
5. Turning the switch **off** locks the vault and wipes the short-lived decrypt cache under `media/vault_cache/`.

## Viewing images in the app

Orchestrator serves files from the app data `media/` folder at `http://127.0.0.1:8765/media/...`:

| On disk | URL |
|---------|-----|
| `media/generations/{id}.png` | `/media/generations/{id}.png` |
| `media/generations/{id}.mp4` | `/media/generations/{id}.mp4` |
| `media/thumbnails/{id}_thumb.png` | `/media/thumbnails/{id}_thumb.png` |
| `media/uploads/face_*.png` | `/media/uploads/face_*.png` |

The UI never uses raw filesystem paths as `<img src>` — it maps them with `mediaUrl()`.
Studio / Influencers cards use face seed / base portrait / latest generation. Generate polls the job and shows the result. Library and influencer profiles open full-size previews.

## Scene polish (LLM)

Image/video still run through local ComfyUI. Settings → **LLM provider** only rewrites the short scene text before the queue expands the full prompt:

| Provider | Behavior |
|----------|----------|
| Local | GGUF enrich via `llama-cpp-python` when a `.gguf` is found (`llm_local_model` or `models/llm/*.gguf`); otherwise offline template |
| OpenAI | `gpt-4o-mini` enrich when `openai_api_key` is set; falls back to template on failure |
| Claude | Anthropic Haiku enrich when `anthropic_api_key` is set; falls back to template |
| Gemini | Gemini Flash enrich when `gemini_api_key` is set; falls back to template |

Blank password fields in Settings keep the existing key.

Local LLM setup (optional):

```bash
cd forge-python && uv sync --group llm
# place a GGUF under Application Support/…/models/llm/
# or enable IFORGE_ENABLE_MODEL_DOWNLOADS=1 for the Llama 3.2 1B bootstrap entry
```

## System tray

Desktop builds expose a tray menu (Show / Pause queue / Resume queue / Quit). Pause and Resume emit Tauri events that the React shell maps to `POST /api/queue/pause` and `/api/queue/resume`.

## AnimateDiff video hardening

Create post → **Video**:

- Rejected at enqueue if AnimateDiff nodes / motion module are missing.
- Needs **ffmpeg** (or `imageio-ffmpeg`) before Comfy runs — clear error otherwise.
- Face Seed + FaceID on by default at 384×640; if FaceID weights/nodes are missing, the job **fails** unless you set `IFORGE_VIDEO_FACEID=0` (identity may drift).
- No Pillow stub for video/lip_sync (avoids fake “completed” PNGs).
- Talking head prefers Wav2Lip after `./scripts/install-wav2lip.sh` + ComfyUI restart; otherwise ffmpeg face+audio mux.
- NSFW generations inject a matching LoRA from `models/loras/` when the filename contains nsfw/nude/explicit (see recommended download above).

## Talking head (lip-sync)

Create post → **Talking head (face + audio)**:

1. Influencer must have a Face Seed or base portrait.
2. Upload wav/mp3/m4a/… — stored via `POST /api/uploads/audio`.
3. Orchestrator muxes face still + audio with **ffmpeg** into `{id}.mp4` (`model_used=talking_head_ffmpeg`).

This is a playable talking-head container (still face + voice). Animated mouth sync via **ComfyUI-Wav2Lip** is not wired yet (no custom node in the bundle). Readiness item `talking_head` turns green when `ffmpeg` is on `PATH`.

## Scheduler & Library edits

- **Scheduler**: local reminders (`GET /api/schedules/reminders`); pause/resume/delete schedules; due items deep-link to Create post with the template in notes. Export `.ics` via `GET /api/schedules/export.ics` (or per-schedule) for Google/Apple Calendar import (no OAuth).
- **Library**: image generations support rotate ±90°, margin/numeric crop, watermark, and overlay via `POST /api/post-process` (writes `{id}_edited.png`).

## Dev: app “crashes” mid-generation

If `npm run tauri dev` logs `File src-tauri/resources/comfyui/ComfyUI/temp changed. Rebuilding application…`, the desktop process is being **hot-reloaded**, not randomly crashing. ComfyUI writes into `temp/` while sampling; Tauri’s watcher used to treat that as a Rust source change.

Fix: `src-tauri/.taurignore` ignores `resources/comfyui/`. Restart `tauri dev` after pulling that file. Fallback: `npm run tauri dev -- --no-watch`.

## GPU note

SDXL needs a capable GPU (or a slow CPU run). Without hardware, readiness may be green but jobs will be slow or OOM — that is a runtime issue, not CRUD.

## Apple Silicon

Ignore `comfy-aimdo unsupported operating system: Darwin` — that is NVIDIA-only.
A healthy Mac log includes `Device: mps` and `To see the GUI go to: http://127.0.0.1:8188`.

Existing single-file checkpoints (e.g. `/Volumes/external/hfModels/RealVisXL_V5.0/…`) can be symlinked into
`ComfyUI/models/checkpoints/` or discovered via `IFORGE_EXTRA_MODEL_DIRS`.
