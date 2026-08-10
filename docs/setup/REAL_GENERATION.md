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

## Face consistency (img2img lock)

When a look has a **Face Seed** upload or a **base portrait** (first SFW headshot), generation uses `image_img2img.json`:

1. Reference image is resized into `ComfyUI/input/iforge_face_{id}.png`
2. ComfyUI LoadImage → VAEEncode → KSampler (denoise ~0.72 SFW / ~0.82 NSFW)
3. History `model_used` shows `sdxl-img2img`

Upload a Face Seed in the Wizard for the strongest lock. Without either reference, gens stay plain txt2img (`sdxl`). InstantID/IP-Adapter remains a later upgrade.

## Explicit / NSFW generations

For Adult or **18+** influencers:

1. Open **Generate**, select the influencer (NSFW mode defaults on for `18+`).
2. Enable **NSFW / explicit mode** (or use words like `topless` / `nude` in the prompt).
3. Prefer waist-up / full-body phrasing — face-only “portrait” framing hides the body.
4. Leave Wardrobe empty (skipped automatically in NSFW mode).

The pipeline then uses adult framing + clothing negatives. RealVisXL can still refuse some scenes; stronger wording and re-rolls help. Family/Teen ratings block NSFW.

### Privacy Vault

1. Open **Vault** → set a PIN (min 4 chars). Setup leaves the vault **unlocked**.
2. With the vault unlocked, new NSFW jobs **auto-vault**: encrypt to `vault/{id}.bin`, write a blurred teaser, delete cleartext PNG/thumb.
3. History shows teasers + “In vault” for vaulted rows. Full image: unlock → Vault gallery (or History when unlocked).
4. If NSFW finished while locked, use **Vault pending NSFW** after unlock.
5. **Lock** wipes the short-lived decrypt cache under `media/vault_cache/`.

## Viewing images in the app

Orchestrator serves files from the app data `media/` folder at `http://127.0.0.1:8765/media/...`:

| On disk | URL |
|---------|-----|
| `media/generations/{id}.png` | `/media/generations/{id}.png` |
| `media/thumbnails/{id}_thumb.png` | `/media/thumbnails/{id}_thumb.png` |
| `media/uploads/face_*.png` | `/media/uploads/face_*.png` |

The UI never uses raw filesystem paths as `<img src>` — it maps them with `mediaUrl()`.
Studio cards use face seed / base portrait / latest generation. Generate polls the job and shows the result. History opens a full-size preview.

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
