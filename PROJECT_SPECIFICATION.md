# INFLUENCERFORGE 🧠🎬

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust](https://img.shields.io/badge/Rust-1.80+-orange.svg)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)

**InfluencerForge** is a cross-platform (Windows, macOS, Linux) desktop application that enables users to create, manage, and generate content for unlimited AI-powered virtual influencers. Everything runs **100% locally** with **zero technical setup** (no Python, no Git, no terminal commands required). Built with Tauri v2, React, and Python.

---

## Table of Contents

- [Project Vision](#project-vision)
- [Core Architecture](#core-architecture)
- [Feature Modules](#feature-modules)
- [Database Schema](#database-schema)
- [Folder Structure](#folder-structure)
- [Open Source Standards](#open-source-standards)
- [AI Coding Standards](#ai-coding-standards)
- [Development Roadmap](#development-roadmap)
- [Contributing Guide](#contributing-guide)
- [Security Policy](#security-policy)

---

## Project Vision

**InfluencerForge** is the ultimate local-first AI influencer studio.

Users create influencers by combining a **Personality** (name, bio, traits, niche, age rating) with a **Looks** (physical appearance defined via text sliders OR by uploading a "Face Seed" reference photo—used solely as a blueprint to extract facial structure, never modified or stored in outputs). The system ensures **perfect face consistency** across all generated images and videos using IP-Adapter/InstantID.

### Key Capabilities

- Generate images and videos (AnimateDiff, Wav2Lip).
- View full history with filtering and regeneration.
- Schedule reminders with Google/Apple Calendar integration.
- Choose between local free models (Llama 3.2, SDXL) or paid cloud APIs (OpenAI, Claude, Gemini).
- Store all NSFW/18+ content in an encrypted **Privacy Vault** protected by a local PIN.
- Monitor system health (GPU/CPU/RAM/Temps) in real time.

---

## Core Architecture

The application consists of three tightly integrated layers, all bundled into a single portable executable:

| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **Frontend (UI)** | Tauri v2 (Rust backend + WebView2) + React 18 + TypeScript + TailwindCSS + Vite | Renders the UI, handles user interactions, displays real-time data, communicates with the Python backend via HTTP/WebSocket. |
| **Orchestrator (Backend)** | Python 3.10+ (embedded portable) + FastAPI + Uvicorn | Runs as a local HTTP server (`127.0.0.1:8765`). Manages AI engines, job queue, SQLite, scheduler, and serves API endpoints. |
| **AI Engines (Worker)** | ComfyUI (headless, port 8188) + llama-cpp-python + optional cloud API clients | Executes the actual generation workloads. |

### Communication Flow

React UI → HTTP Request → FastAPI (Port 8765) → ComfyUI API (Port 8188) OR LLM (local/cloud)
↓
SQLite DB
↓
Response → UI


### Process Management (Rust)

- Tauri spawns embedded Python (orchestrator).
- Python spawns ComfyUI as a subprocess.
- On app exit, Rust gracefully terminates Python → Python terminates ComfyUI.

---

## Feature Modules

| Module | Description | Priority |
| :--- | :--- | :--- |
| **Module 1: First-Launch Bootstrap** | Splash screen with progress bar; auto-downloads SDXL, LLM (GGUF), and ComfyUI nodes from HuggingFace. | P0 (Critical) |
| **Module 2: Character Creation** | 2-Step Wizard: Personality (name, bio, traits, niche, age rating) + Looks (text sliders or Reference Image upload for Face Seed extraction). | P0 (Critical) |
| **Module 3: Wardrobe System** | Create outfits with prompt keywords; assign them to specific influencers or share globally. | P1 (High) |
| **Module 4: Content Generation** | Image + Video (AnimateDiff, Wav2Lip) generation with a queued async system; NSFW toggle triggers specialized LoRAs. | P0 (Critical) |
| **Module 5: History & Library** | Gallery with filters (Influencer, Date, SFW/NSFW); click for details; "Regenerate" button to rerun exact seeds. | P0 (Critical) |
| **Module 6: Scheduling & Notifications** | Schedule daily/weekly posts; Google/Apple Calendar integration; on-app-launch reminders to generate. | P1 (High) |
| **Module 7: Model Settings** | Choose LLM provider (Local, OpenAI, Claude, Gemini); choose Image/Video models; enter API keys. | P1 (High) |
| **Module 8: Privacy Vault** | PIN-protected AES-256-GCM encrypted storage for all NSFW content; auto-generates blurred teasers. | P1 (High) |
| **Module 9: Post-Production** | Crop, rotate, watermark, text overlay (Pillow). | P2 (Medium) |
| **Module 10: System Monitor** | Real-time GPU/VRAM/CPU/RAM/Temperature display; queue status. | P2 (Medium) |
| **Module 11: System Tray** | Background operation; pause/resume generation; quick quit. | P2 (Medium) |

---

## Database Schema

**Location:** `%APPDATA%/InfluencerForge/data.db` (Windows), `~/Library/Application Support/InfluencerForge/data.db` (macOS), `~/.config/InfluencerForge/data.db` (Linux).

### Table: `personalities`

Stores the "mind" of the influencer.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `name` | TEXT | NOT NULL | e.g., "Elena", "Sophie" |
| `bio` | TEXT | | Short biography |
| `traits` | TEXT (JSON) | NOT NULL | `{"humor": "witty", "tone": "friendly", "expertise": "AI"}` |
| `niche` | TEXT | NOT NULL | "Tech", "Gaming", "Fashion", "Adult", etc. |
| `age_rating` | TEXT | NOT NULL | "Family", "Teen", "Adult", "18+" |
| `system_prompt` | TEXT | | Pre-generated system prompt for LLM content generation |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

### Table: `looks`

Stores the physical "body" of the influencer (the face seed).

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `name` | TEXT | NOT NULL | e.g., "Elena's Look" |
| `age` | INTEGER | | 18-80 |
| `ethnicity` | TEXT | | "Caucasian", "Asian", "Black", etc. |
| `hair_color` | TEXT | | "Blonde", "Brown", "Black", etc. |
| `hair_style` | TEXT | | "Long straight", "Short curly", etc. |
| `eye_color` | TEXT | | "Blue", "Green", "Brown" |
| `style` | TEXT | | "Casual", "Elegant", "Sporty" |
| `base_prompt` | TEXT | | Text prompt used to generate the base portrait |
| `reference_image_path` | TEXT | | Path to uploaded reference photo (optional) |
| `face_embedding` | BLOB | | IP-Adapter/InstantID embedding vector |
| `lora_path` | TEXT | | Path to trained LoRA `.safetensors` (optional) |
| `base_portrait_path` | TEXT | | Path to generated base portrait thumbnail |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

### Table: `influencers`

Combines Personality + Looks into a single usable character.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `personality_id` | INTEGER | FOREIGN KEY (personalities.id) | |
| `looks_id` | INTEGER | FOREIGN KEY (looks.id) | |
| `name` | TEXT | NOT NULL | Derived from personality.name |
| `is_active` | BOOLEAN | DEFAULT 1 | If false, this influencer is archived |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

### Table: `wardrobe_items`

Clothing/outfits that can be applied to influencers.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `name` | TEXT | NOT NULL | e.g., "Casual Hoodie" |
| `description` | TEXT | | Detailed description |
| `category` | TEXT | NOT NULL | UI presets: Top, Bottom, Full Outfit, Accessory, Footwear, Outerwear, Swimwear, Lingerie, or custom Other |
| `prompt_keywords` | TEXT | NOT NULL | "gray oversized hoodie, relaxed fit" |
| `preview_image` | TEXT | | Path to thumbnail |
| `is_shared` | BOOLEAN | DEFAULT 0 | If TRUE, appears in ALL influencers' wardrobes |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

### Table: `influencer_wardrobe`

Many-to-many relationship.

| Column | Type | Constraints |
| :--- | :--- | :--- |
| `influencer_id` | INTEGER | FOREIGN KEY (influencers.id) |
| `wardrobe_item_id` | INTEGER | FOREIGN KEY (wardrobe_items.id) |
| `added_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP |

### Table: `generations`

Full audit log of all generated content.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `influencer_id` | INTEGER | FOREIGN KEY (influencers.id) | |
| `parent_generation_id` | INTEGER | FOREIGN KEY (generations.id) NULLABLE | For regenerations |
| `user_prompt` | TEXT | NOT NULL | What the user typed |
| `expanded_prompt` | TEXT | NOT NULL | LLM-expanded prompt sent to ComfyUI |
| `negative_prompt` | TEXT | | Negative prompt used |
| `workflow_type` | TEXT | NOT NULL | "image" or "video" |
| `model_used` | TEXT | NOT NULL | "sdxl", "flux", "animate_diff" |
| `llm_used` | TEXT | NOT NULL | "local_llama3.2", "gpt-4", etc. |
| `aspect_ratio` | TEXT | NOT NULL | "9:16", "16:9", "1:1" |
| `seed` | INTEGER | | Random seed for reproducibility |
| `steps` | INTEGER | | Number of inference steps |
| `cfg_scale` | FLOAT | | Classifier-free guidance scale |
| `output_path` | TEXT | | Path to generated file |
| `output_thumbnail_path` | TEXT | | Path to compressed thumbnail |
| `is_nsfw` | BOOLEAN | DEFAULT 0 | TRUE if age rating was 18+ |
| `is_vaulted` | BOOLEAN | DEFAULT 0 | TRUE if moved to Privacy Vault |
| `vault_file_path` | TEXT | | Path inside encrypted vault |
| `teaser_path` | TEXT | | Path to blurred/censored version |
| `status` | TEXT | NOT NULL | "pending", "queued", "processing", "completed", "failed" |
| `error_message` | TEXT | | If status = "failed" |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | |
| `completed_at` | DATETIME | | Timestamp when generation finished |

### Table: `schedules`

Content scheduling and reminders.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `influencer_id` | INTEGER | FOREIGN KEY (influencers.id) | |
| `schedule_time` | TIME | NOT NULL | e.g., "09:00:00" |
| `frequency` | TEXT | NOT NULL | "daily", "weekly", "monthly", "custom" |
| `cron_expression` | TEXT | | If frequency = "custom" |
| `prompt_template` | TEXT | NOT NULL | e.g., "Good morning! Today I'm wearing {wardrobe} in a {scene}." |
| `scene_suggestions` | TEXT | | JSON array of suggested scenes |
| `wardrobe_item_id` | INTEGER | FOREIGN KEY (wardrobe_items.id) NULLABLE | Specific outfit or random |
| `is_active` | BOOLEAN | DEFAULT 1 | |
| `calendar_event_id` | TEXT | | Google/Apple Calendar event ID |
| `calendar_provider` | TEXT | | "google", "apple", NULL |
| `last_triggered` | DATETIME | | Last time this schedule ran |
| `next_trigger` | DATETIME | | Next scheduled run time |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

### Table: `settings`

Global application settings (key-value store).

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `key` | TEXT | PRIMARY KEY | e.g., "llm_provider", "openai_api_key" |
| `value` | TEXT | NOT NULL | JSON string or plain value |
| `updated_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

### Table: `vault_metadata`

Encrypted metadata for the Privacy Vault.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | Always 1 |
| `pin_hash` | TEXT | NOT NULL | Argon2id hash of the user's PIN |
| `pin_salt` | TEXT | NOT NULL | Salt used for hashing |
| `vault_path` | TEXT | NOT NULL | Path to the encrypted vault folder |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

---

## Folder Structure

influencer-forge/
├── src-tauri/ # Rust Backend
│ ├── src/
│ │ ├── main.rs
│ │ ├── process_manager.rs # Spawns/kills Python & ComfyUI
│ │ ├── system_tray.rs
│ │ ├── ipc_handlers.rs
│ │ └── paths.rs
│ ├── resources/ # Bundled at compile time
│ │ ├── python/ # Embedded Python 3.10+ (portable)
│ │ │ ├── python.exe / python
│ │ │ ├── Lib/site-packages/ # fastapi, uvicorn, sqlcipher3, etc.
│ │ │ └── python._pth
│ │ ├── comfyui/ # Full ComfyUI source + custom nodes
│ │ │ ├── ComfyUI/
│ │ │ ├── custom_nodes/
│ │ │ │ ├── ComfyUI-IPAdapter/
│ │ │ │ ├── ComfyUI-AnimateDiff/
│ │ │ │ └── ComfyUI-Wav2Lip/
│ │ │ └── main.py
│ │ ├── workflows/ # Pre-built JSON workflows
│ │ │ ├── face_seed.json
│ │ │ ├── image_faceid.json
│ │ │ ├── video_animate.json
│ │ │ └── lip_sync.json
│ │ ├── bootstrap/
│ │ │ ├── installer.py # First-launch model downloader
│ │ │ └── orchestrator.py # Main FastAPI server
│ │ └── assets/ # App icons, splash images
│ └── tauri.conf.json
├── src/ # React Frontend
│ ├── components/
│ │ ├── common/ # Sidebar, Header, QueueStatus
│ │ ├── wizard/ # PersonalityForm, LooksForm, FaceUploader
│ │ ├── generation/ # GenerateForm, AspectRatioSelector
│ │ ├── history/ # HistoryGallery, HistoryFilters
│ │ ├── scheduler/ # ScheduleForm, ScheduleList
│ │ ├── vault/ # VaultUnlock, VaultGallery
│ │ ├── settings/ # ModelSettings, LLMProviderSelector
│ │ ├── wardrobe/ # WardrobeGallery, WardrobeForm
│ │ ├── system/ # SystemMonitor
│ │ └── post/ # PostProductionEditor
│ ├── pages/
│ │ ├── Splash.tsx
│ │ ├── Dashboard.tsx
│ │ ├── Wizard.tsx
│ │ ├── Generate.tsx
│ │ ├── History.tsx
│ │ ├── Scheduler.tsx
│ │ ├── Vault.tsx
│ │ ├── Settings.tsx
│ │ └── Wardrobe.tsx
│ ├── hooks/ # useQueue, useSystemStats, useVault
│ ├── api/ # client.ts
│ ├── types/ # index.ts
│ ├── App.tsx
│ └── main.tsx
├── forge-python/ # Python Source Code (reference)
│ ├── orchestrator.py
│ ├── db.py
│ ├── llm_manager.py
│ ├── comfyui_client.py
│ ├── scheduler.py
│ ├── system_monitor.py
│ ├── vault.py
│ ├── queue_worker.py
│ ├── post_processing.py
│ ├── model_downloader.py
│ ├── config.py
│ └── requirements.txt
├── .github/
│ └── workflows/
│ ├── build.yml # CI: Build for Windows, Mac, Linux
│ └── lint.yml # CI: Run linters
├── .gitignore
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CHANGELOG.md
├── README.md
└── PROJECT_SPECIFICATION.md # This file


---

## Open Source Standards

### 1. License
- **MIT License** recommended (permissive, allows commercial use of outputs and code).
- *Location:* `LICENSE` file in root.

### 2. Code of Conduct
- **Contributor Covenant v2.1**.
- *Location:* `CODE_OF_CONDUCT.md`.

### 3. Security Policy
- Define how to report vulnerabilities privately.
- *Location:* `SECURITY.md`.

### 4. Changelog
- Keep a `CHANGELOG.md` following **Keep a Changelog** standards.
- Versioning follows **Semantic Versioning (SemVer)**.

### 5. Contributing Guide
- Outline the CLA (if any), setup instructions, PR process.
- *Location:* `CONTRIBUTING.md`.

---

## AI Coding Standards

### Python (Backend)
| Tool | Purpose | Configuration |
| :--- | :--- | :--- |
| `uv` | Dependency management | `pyproject.toml` |
| `ruff format` | Code formatting | Default settings |
| `ruff check` | Linting (replaces Flake8, isort) | Strict rules |
| `mypy` | Type checking | `--strict` mode |
| `pytest` | Unit tests | Minimum 80% coverage |
| `pydantic` | Data validation | All models |

### Rust (Tauri Backend)
| Tool | Purpose | Configuration |
| :--- | :--- | :--- |
| `rustfmt` | Code formatting | Default settings |
| `clippy` | Linting | `-D warnings` |
| `anyhow` | Error handling | For binaries |
| `thiserror` | Error handling | For libraries |
| `serde` | Serialization | All structs |

### TypeScript/React (Frontend)
| Tool | Purpose | Configuration |
| :--- | :--- | :--- |
| `prettier` | Code formatting | Default settings |
| `eslint` | Linting | With `@typescript-eslint` |
| `tsc` | Type checking | `--noEmit` in CI |
| `react-query` | Server state | API calls, caching |
| `zustand` | Client state | Global UI state |
| `vitest` | Unit tests | For components |

### Git & CI/CD
- **Commit Messages**: Enforce **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`).
- **Pre-commit Hooks**: Use `pre-commit` (Python) and/or `husky` (Node).
- **GitHub Actions**:
  - `lint.yml`: Runs on PRs (formatting, linting, type checking).
  - `build.yml`: Builds Tauri app for Windows (`.exe`), macOS (`.dmg`), Linux (`.AppImage`).

---

## Development Roadmap

### Phase 1: Foundation (MVP) - *4-6 weeks*

**Goal:** App launches, downloads models, creates basic influencer, generates simple image.

| Task | Description | Priority |
| :--- | :--- | :--- |
| 1.1 | Tauri v2 project setup with React | P0 |
| 1.2 | `Splash.tsx` with progress bar | P0 |
| 1.3 | `installer.py` model downloader (HuggingFace) | P0 |
| 1.4 | Rust `process_manager.rs` (spawn Python/ComfyUI) | P0 |
| 1.5 | SQLite DB setup (all tables) | P0 |
| 1.6 | `orchestrator.py` with `/api/health` endpoint | P0 |
| 1.7 | Personality & Looks creation (text sliders only) | P0 |
| 1.8 | Basic image generation (SDXL + simple prompt) | P0 |
| 1.9 | History gallery (read-only) | P0 |

---

### Phase 2: Core Features - *6-8 weeks*

| Task | Description | Priority |
| :--- | :--- | :--- |
| 2.1 | Face Seed upload (IP-Adapter extraction) | P0 |
| 2.2 | Wardrobe system (CRUD + assignment) | P1 |
| 2.3 | Full queue system with async worker | P0 |
| 2.4 | Regeneration functionality | P0 |
| 2.5 | System Monitor (GPU/CPU/RAM) | P1 |
| 2.6 | Video generation (AnimateDiff) | P0 |
| 2.7 | History filters and detail modal | P0 |

---

### Phase 3: Advanced Features - *8-10 weeks*

| Task | Description | Priority |
| :--- | :--- | :--- |
| 3.1 | Privacy Vault (PIN, AES encryption, teasers) | P1 |
| 3.2 | Scheduler (APScheduler + Google/Apple Calendar) | P1 |
| 3.3 | Model Settings (LLM provider switching, API keys) | P1 |
| 3.4 | Wav2Lip (talking head videos) | P1 |
| 3.5 | Post-production editing (Pillow) | P2 |
| 3.6 | System tray | P2 |
| 3.7 | "Smart Daily Content" suggestions | P2 |
| 3.8 | Cross-platform testing (Windows, macOS, Linux) | P0 |

---

## Contributing Guide

*Full guide in `CONTRIBUTING.md`.*

**Quick Start:**

1. **Fork the repository** and clone it locally.
2. **Setup pre-requisites**:
   - Node.js 20+, Rust 1.80+, Python 3.10+.
   - Install Tauri CLI: `cargo install tauri-cli`.
3. **Install dependencies**:
   - Frontend: `npm install`.
   - Python: `uv venv` and `uv pip sync`.
4. **Run the app in development mode**: `cargo tauri dev`.
5. **Write tests** for any new feature or bug fix.
6. **Commit** using Conventional Commits (e.g., `feat(generate): add IP-Adapter support`).
7. **Open a Pull Request** against the `main` branch.

**PR Requirements:**
- All linters and type checkers pass.
- Tests pass (if applicable).
- New features include documentation updates.
- Screenshots or screen recordings for UI changes.

---

## Security Policy

*Full policy in `SECURITY.md`.*

- **Vault Encryption**: All NSFW content is encrypted using AES-256-GCM. The encryption key is derived from the user's PIN using Argon2id + HKDF. **We do not store the PIN.**
- **No Telemetry**: This application sends **zero** data to the developers. It is fully offline-capable (except for cloud LLM API calls which go directly to OpenAI/Google/Anthropic, not through our servers).
- **Data Storage**: All data stays on the user's machine in `%APPDATA%/InfluencerForge`.
- **Reporting Vulnerabilities**: Report privately via email to `security@influencerforge.dev` or through the GitHub Security Advisory tab. Do NOT open a public issue.

---

**End of Specification**

*Last Updated: August 2026*