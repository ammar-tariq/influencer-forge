import type {
  BootstrapStatus,
  Generation,
  Influencer,
  Looks,
  Personality,
  QueueStatus,
  Schedule,
  SettingItem,
  SystemStats,
  WardrobeItem,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,
  health: () => request<{ status: string; version: string }>("/api/health"),
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

  listLooks: () => request<Looks[]>("/api/looks"),
  createLooks: (body: Partial<Looks> & { name: string }) =>
    request<Looks>("/api/looks", { method: "POST", body: JSON.stringify(body) }),
  uploadFaceSeed: async (looksId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/api/looks/${looksId}/face-seed`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<Looks>;
  },

  listInfluencers: () => request<Influencer[]>("/api/influencers"),
  createInfluencer: (body: { personality_id: number; looks_id: number; name?: string }) =>
    request<Influencer>("/api/influencers", { method: "POST", body: JSON.stringify(body) }),

  listWardrobe: () => request<WardrobeItem[]>("/api/wardrobe"),
  createWardrobe: (body: Omit<WardrobeItem, "id">) =>
    request<WardrobeItem>("/api/wardrobe", { method: "POST", body: JSON.stringify(body) }),
  assignWardrobe: (influencerId: number, itemId: number) =>
    request(`/api/influencers/${influencerId}/wardrobe/${itemId}`, { method: "POST" }),

  listGenerations: (params?: { influencer_id?: number; is_nsfw?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.influencer_id != null) q.set("influencer_id", String(params.influencer_id));
    if (params?.is_nsfw != null) q.set("is_nsfw", String(params.is_nsfw));
    const suffix = q.toString() ? `?${q}` : "";
    return request<Generation[]>(`/api/generations${suffix}`);
  },
  getGeneration: (id: number) => request<Generation>(`/api/generations/${id}`),
  createGeneration: (body: {
    influencer_id: number;
    user_prompt: string;
    workflow_type?: string;
    aspect_ratio?: string;
    seed?: number;
    wardrobe_item_id?: number;
    is_nsfw?: boolean;
    require_real?: boolean;
  }) => request<Generation>("/api/generations", { method: "POST", body: JSON.stringify(body) }),
  regenerate: (id: number) =>
    request<Generation>(`/api/generations/${id}/regenerate`, { method: "POST" }),
  postProcess: (body: {
    generation_id: number;
    rotate_degrees?: number;
    watermark_text?: string;
    overlay_text?: string;
  }) => request<{ output_path: string }>("/api/post-process", { method: "POST", body: JSON.stringify(body) }),

  listSettings: () => request<SettingItem[]>("/api/settings"),
  putSetting: (key: string, value: string) =>
    request<SettingItem>("/api/settings", { method: "PUT", body: JSON.stringify({ key, value }) }),
  fullReset: (include_app_models = false) =>
    request<{ status: string; data_dir: string; removed: Record<string, unknown> }>(
      "/api/system/reset",
      {
        method: "POST",
        body: JSON.stringify({ confirm: "RESET", include_app_models }),
      },
    ),

  listSchedules: () => request<Schedule[]>("/api/schedules"),
  createSchedule: (body: {
    influencer_id: number;
    schedule_time: string;
    frequency: string;
    prompt_template: string;
    cron_expression?: string;
  }) => request<Schedule>("/api/schedules", { method: "POST", body: JSON.stringify(body) }),
  reminders: () => request<{ reminders: unknown[] }>("/api/schedules/reminders"),

  vaultStatus: () => request<{ configured: boolean; unlocked: boolean }>("/api/vault/status"),
  vaultSetup: (pin: string) =>
    request("/api/vault/setup", { method: "POST", body: JSON.stringify({ pin }) }),
  vaultUnlock: (pin: string) =>
    request("/api/vault/unlock", { method: "POST", body: JSON.stringify({ pin }) }),
  vaultLock: () => request("/api/vault/lock", { method: "POST" }),
  vaultGeneration: (id: number) =>
    request(`/api/vault/generations/${id}`, { method: "POST" }),
};

/**
 * Map absolute on-disk paths from the API to HTTP URLs served by the orchestrator.
 * Never use raw filesystem paths as <img src> in the webview.
 */
export function mediaUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  // Already an HTTP(S) URL
  if (/^https?:\/\//i.test(path)) return path;
  const normalized = path.replace(/\\/g, "/");
  const name = normalized.split("/").pop();
  if (!name) return undefined;

  if (normalized.includes("/uploads/") || name.startsWith("face_")) {
    return `${BASE}/media/uploads/${encodeURIComponent(name)}`;
  }
  if (
    normalized.includes("/thumbnails/") ||
    name.includes("_thumb") ||
    name.includes("_teaser")
  ) {
    return `${BASE}/media/thumbnails/${encodeURIComponent(name)}`;
  }
  return `${BASE}/media/generations/${encodeURIComponent(name)}`;
}
