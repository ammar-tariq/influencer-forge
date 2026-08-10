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

1. **Studio home** checklist links you through Create → Influencers → Generate → Vault.
2. **New influencer** is 3 steps: Personality → Face (gender) → Body (height, figure, skin, etc.). After create you land on that influencer’s **profile**.
3. On the profile, **Face lock setup** shows identity-shot progress. Edit the prompt, re-roll, or upload a Face Seed, then **Lock this face**. Until locked, later gens won’t use img2img identity.
4. **Influencers** (sidebar) lists everyone; open a card for personality/looks, all their posts, Create post, or Archive.
5. **Library** (`/history`) filters with `?influencer={id}` — also linked from each profile (“All posts” / “Their posts”).
6. **Create post** defaults to **full body** and offers Pose / Dressing / Setting presets (including nude). You can still add free notes.
7. Progress for the active job shows in the right-hand Progress panel.

## Face consistency (img2img lock)

When a look has a **Face Seed** upload or a **base portrait** (locked on the influencer profile), generation uses `image_img2img.json`:

1. Reference is staged as a **large sharp head** over a blurred body prior (keeps face/hair; frees pose/outfit).
2. ComfyUI LoadImage → VAEEncode → KSampler with **moderate denoise** (~0.55–0.68, hard-capped at 0.72). Higher values were wiping identity and turning detailed prompts graphic.
3. Face-locked prompts lead with identity tokens and stay short; CFG ~5.
4. History `model_used` shows `sdxl-img2img`

Bikini/lingerie prompts no longer auto-append `nude` or ban the outfit in negatives. Upload a Face Seed for the strongest lock. Without a reference, gens stay plain txt2img (`sdxl`). InstantID/IP-Adapter remains a later upgrade.

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
Studio / Influencers cards use face seed / base portrait / latest generation. Generate polls the job and shows the result. Library and influencer profiles open full-size previews.

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
