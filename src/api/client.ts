import type {
  BootstrapStatus,
  Generation,
  Influencer,
  InfluencerDetail,
  Looks,
  Personality,
  QueueStatus,
  Schedule,
  SettingItem,
  SystemStats,
  VaultedGeneration,
  VaultStatus,
  WardrobeItem,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";

/** Bumped after full reset so reused /media/... filenames don't show ghost images. */
let mediaEpoch = "0";

export function setMediaEpoch(epoch: string | number | undefined | null) {
  if (epoch == null || epoch === "") return;
  mediaEpoch = String(epoch);
}

export function getMediaEpoch() {
  return mediaEpoch;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    let message = text || res.statusText;
    try {
      const body = JSON.parse(text) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail != null) message = JSON.stringify(body.detail);
    } catch {
      // keep raw body
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,
  health: async () => {
    const h = await request<{ status: string; version: string; media_epoch?: string }>(
      "/api/health",
    );
    if (h.media_epoch) setMediaEpoch(h.media_epoch);
    return h;
  },
  bootstrap: () => request<BootstrapStatus>("/api/bootstrap/status"),
  comfyStatus: () =>
    request<{
      enabled: boolean;
      healthy: boolean;
      url: string;
      root: string;
      process_running: boolean;
    }>("/api/comfyui/status"),
  readiness: () =>
    request<{
      mode: "real" | "stub";
      real_ready: boolean;
      allow_stub_fallback: boolean;
      animatediff_ready?: boolean;
      faceid_ready?: boolean;
      summary: string;
      checklist: Array<{
        id: string;
        label: string;
        ok: boolean;
        detail: string;
        fix: string;
      }>;
      checkpoints: string[];
    }>("/api/readiness"),
  queue: () => request<QueueStatus>("/api/queue"),
  pauseQueue: () => request("/api/queue/pause", { method: "POST" }),
  resumeQueue: () => request("/api/queue/resume", { method: "POST" }),
  stats: () => request<SystemStats>("/api/system/stats"),
  suggestions: (niche: string) =>
    request<{ suggestions: string[] }>(`/api/suggestions?niche=${encodeURIComponent(niche)}`),

  listPersonalities: () => request<Personality[]>("/api/personalities"),
  createPersonality: (body: Omit<Personality, "id" | "system_prompt" | "created_at">) =>
    request<Personality>("/api/personalities", { method: "POST", body: JSON.stringify(body) }),
  updatePersonality: (
    id: number,
    body: Partial<Omit<Personality, "id" | "system_prompt" | "created_at">>,
  ) =>
    request<Personality>(`/api/personalities/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  listLooks: () => request<Looks[]>("/api/looks"),
  createLooks: (body: Partial<Looks> & { name: string }) =>
    request<Looks>("/api/looks", { method: "POST", body: JSON.stringify(body) }),
  updateLooks: (
    id: number,
    body: Partial<
      Pick<
        Looks,
        | "name"
        | "age"
        | "gender"
        | "ethnicity"
        | "nationality"
        | "hair_color"
        | "hair_style"
        | "eye_color"
        | "style"
        | "body"
      >
    >,
  ) =>
    request<Looks>(`/api/looks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  uploadFaceSeed: async (looksId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/api/looks/${looksId}/face-seed`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<Looks>;
  },

  listInfluencers: () => request<Influencer[]>("/api/influencers"),
  getInfluencer: async (id: number): Promise<InfluencerDetail> => {
    try {
      return await request<InfluencerDetail>(`/api/influencers/${id}`);
    } catch {
      // Fallback when a stale orchestrator lacks GET /api/influencers/{id}.
      const [influencers, personalities, looks] = await Promise.all([
        request<Influencer[]>("/api/influencers"),
        request<Personality[]>("/api/personalities"),
        request<Looks[]>("/api/looks"),
      ]);
      const base = influencers.find((i) => i.id === id);
      if (!base) throw new Error("Influencer not found");
      return {
        ...base,
        personality: personalities.find((p) => p.id === base.personality_id) ?? null,
        looks: looks.find((l) => l.id === base.looks_id) ?? null,
        face_lock: base.face_lock ?? (looks.find((l) => l.id === base.looks_id)?.reference_image_path
          ? "face_seed"
          : looks.find((l) => l.id === base.looks_id)?.base_portrait_path
            ? "base_portrait"
            : "none"),
      };
    }
  },
  createInfluencer: (body: { personality_id: number; looks_id: number; name?: string }) =>
    request<Influencer>("/api/influencers", { method: "POST", body: JSON.stringify(body) }),
  archiveInfluencer: (id: number) =>
    request<{ status: string }>(`/api/influencers/${id}/archive`, { method: "POST" }),
  deleteInfluencer: (id: number) =>
    request<{ status: string; generations_removed: number; files_removed: number }>(
      `/api/influencers/${id}`,
      { method: "DELETE" },
    ),
  lockFace: (id: number, body: { generation_id?: number; clear?: boolean }) =>
    request<InfluencerDetail>(`/api/influencers/${id}/face-lock`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listWardrobe: () => request<WardrobeItem[]>("/api/wardrobe"),
  listInfluencerWardrobe: (influencerId: number) =>
    request<WardrobeItem[]>(`/api/influencers/${influencerId}/wardrobe`),
  createWardrobe: (body: Omit<WardrobeItem, "id"> & { description?: string | null }) =>
    request<WardrobeItem>("/api/wardrobe", { method: "POST", body: JSON.stringify(body) }),
  assignWardrobe: (influencerId: number, itemId: number) =>
    request(`/api/influencers/${influencerId}/wardrobe/${itemId}`, { method: "POST" }),
  unassignWardrobe: (influencerId: number, itemId: number) =>
    request(`/api/influencers/${influencerId}/wardrobe/${itemId}`, { method: "DELETE" }),

  listGenerations: (params?: { influencer_id?: number; is_nsfw?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.influencer_id != null) q.set("influencer_id", String(params.influencer_id));
    if (params?.is_nsfw != null) q.set("is_nsfw", String(params.is_nsfw));
    const suffix = q.toString() ? `?${q}` : "";
    return request<Generation[]>(`/api/generations${suffix}`);
  },
  getGeneration: (id: number) => request<Generation>(`/api/generations/${id}`),
  uploadAudio: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/api/uploads/audio`, { method: "POST", body: fd });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    return res.json() as Promise<{ path: string; filename: string }>;
  },
  createGeneration: (body: {
    influencer_id: number;
    user_prompt: string;
    workflow_type?: string;
    aspect_ratio?: string;
    seed?: number;
    wardrobe_item_id?: number;
    is_nsfw?: boolean;
    require_real?: boolean;
    identity_explore?: boolean;
    audio_path?: string;
  }) =>
    request<Generation>("/api/generations", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createGenerationBatch: (body: {
    influencer_id: number;
    user_prompt: string;
    workflow_type?: string;
    aspect_ratio?: string;
    wardrobe_item_id?: number;
    is_nsfw?: boolean;
    require_real?: boolean;
    count?: number;
    identity_explore?: boolean;
  }) =>
    request<{ generations: Generation[] }>("/api/generations/batch", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  regenerate: (id: number, opts?: { identity_explore?: boolean; require_real?: boolean }) => {
    const q = new URLSearchParams();
    if (opts?.identity_explore != null) q.set("identity_explore", String(opts.identity_explore));
    if (opts?.require_real != null) q.set("require_real", String(opts.require_real));
    const suffix = q.toString() ? `?${q}` : "";
    return request<Generation>(`/api/generations/${id}/regenerate${suffix}`, { method: "POST" });
  },
  deleteGeneration: (id: number) =>
    request<{ status: string; id: number; files_removed: number }>(`/api/generations/${id}`, {
      method: "DELETE",
    }),
  replaceGeneration: (
    id: number,
    body: {
      user_prompt: string;
      workflow_type?: string;
      aspect_ratio?: string;
      wardrobe_item_id?: number | null;
      is_nsfw?: boolean;
      require_real?: boolean;
    },
  ) =>
    request<Generation>(`/api/generations/${id}/replace`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  postProcess: (body: {
    generation_id: number;
    rotate_degrees?: number;
    crop?: [number, number, number, number];
    watermark_text?: string;
    overlay_text?: string;
  }) =>
    request<{ output_path: string }>("/api/post-process", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listSettings: () => request<SettingItem[]>("/api/settings"),
  putSetting: (key: string, value: string) =>
    request<SettingItem>("/api/settings", { method: "PUT", body: JSON.stringify({ key, value }) }),
  fullReset: async (include_app_models = false) => {
    const res = await request<{
      status: string;
      data_dir: string;
      removed: Record<string, unknown>;
      media_epoch?: string;
    }>("/api/system/reset", {
      method: "POST",
      body: JSON.stringify({ confirm: "RESET", include_app_models }),
    });
    setMediaEpoch(res.media_epoch ?? Date.now());
    return res;
  },

  listSchedules: () => request<Schedule[]>("/api/schedules"),
  createSchedule: (body: {
    influencer_id: number;
    schedule_time: string;
    frequency: string;
    prompt_template: string;
    cron_expression?: string;
  }) => request<Schedule>("/api/schedules", { method: "POST", body: JSON.stringify(body) }),
  patchSchedule: (id: number, body: { is_active?: boolean }) =>
    request<Schedule>(`/api/schedules/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteSchedule: (id: number) =>
    request<{ status: string }>(`/api/schedules/${id}`, { method: "DELETE" }),
  reminders: () =>
    request<{
      reminders: Array<{
        schedule_id?: number;
        influencer_id?: number;
        prompt_template?: string;
        triggered_at?: string;
      }>;
    }>("/api/schedules/reminders"),
  /** Download .ics for Google Calendar / Apple Calendar import. */
  downloadSchedulesIcs: async (scheduleId?: number) => {
    const path =
      scheduleId == null
        ? "/api/schedules/export.ics"
        : `/api/schedules/${scheduleId}/export.ics`;
    const filename =
      scheduleId == null
        ? "influencerforge-schedules.ics"
        : `influencerforge-schedule-${scheduleId}.ics`;
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  vaultStatus: () => request<VaultStatus>("/api/vault/status"),
  vaultSetup: (pin: string) =>
    request("/api/vault/setup", { method: "POST", body: JSON.stringify({ pin }) }),
  vaultUnlock: (pin: string) =>
    request("/api/vault/unlock", { method: "POST", body: JSON.stringify({ pin }) }),
  vaultLock: () => request("/api/vault/lock", { method: "POST" }),
  vaultEndView: () => request("/api/vault/end-view", { method: "POST" }),
  vaultGeneration: (id: number) =>
    request<{ vault_file_path: string; teaser_path: string }>(`/api/vault/generations/${id}`, {
      method: "POST",
    }),
  listVaultGenerations: () => request<VaultedGeneration[]>("/api/vault/generations"),
  vaultPendingNsfw: () =>
    request<{ vaulted: number[]; errors: Array<{ id: string; error: string }>; count: number }>(
      "/api/vault/generations/pending",
      { method: "POST" },
    ),
};

/** Full reveal URL for a vaulted generation (requires unlocked vault session). */
export function vaultRevealUrl(id: number): string {
  return `${BASE}/api/vault/generations/${id}/image`;
}

/**
 * Map absolute on-disk paths from the API to HTTP URLs served by the orchestrator.
 * Never use raw filesystem paths as <img src> in the webview.
 */
function withMediaEpoch(url: string): string {
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}e=${encodeURIComponent(mediaEpoch)}`;
}

export function mediaUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  // Already an HTTP(S) URL
  if (/^https?:\/\//i.test(path)) {
    // Still bust our local media URLs after reset.
    if (path.includes("/media/")) return withMediaEpoch(path);
    return path;
  }
  const normalized = path.replace(/\\/g, "/");
  const name = normalized.split("/").pop();
  if (!name) return undefined;

  if (normalized.includes("/uploads/") || name.startsWith("face_")) {
    return withMediaEpoch(`${BASE}/media/uploads/${encodeURIComponent(name)}`);
  }
  if (
    normalized.includes("/thumbnails/") ||
    name.includes("_thumb") ||
    name.includes("_teaser")
  ) {
    return withMediaEpoch(`${BASE}/media/thumbnails/${encodeURIComponent(name)}`);
  }
  return withMediaEpoch(`${BASE}/media/generations/${encodeURIComponent(name)}`);
}
