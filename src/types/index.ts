export type AgeRating = "Family" | "Teen" | "Adult" | "18+";

export interface Personality {
  id: number;
  name: string;
  bio?: string | null;
  traits: Record<string, string>;
  niche: string;
  age_rating: AgeRating;
  system_prompt?: string | null;
  created_at?: string | null;
}

export interface Looks {
  id: number;
  name: string;
  age?: number | null;
  gender?: string | null;
  ethnicity?: string | null;
  nationality?: string | null;
  hair_color?: string | null;
  hair_style?: string | null;
  eye_color?: string | null;
  style?: string | null;
  body?: Record<string, string>;
  base_prompt?: string | null;
  reference_image_path?: string | null;
  face_embedding?: string | null;
  base_portrait_path?: string | null;
  created_at?: string | null;
  face_lock_stale?: boolean;
}

export interface Influencer {
  id: number;
  personality_id: number;
  looks_id: number;
  name: string;
  is_active: boolean;
  created_at?: string | null;
  /** Disk path; use mediaUrl() for <img src>. */
  avatar_path?: string | null;
  age_rating?: string | null;
  niche?: string | null;
  /** face_seed | base_portrait | none */
  face_lock?: string | null;
  generation_count?: number;
}

export interface InfluencerDetail extends Influencer {
  personality?: Personality | null;
  looks?: Looks | null;
}

export interface Generation {
  id: number;
  influencer_id: number;
  parent_generation_id?: number | null;
  user_prompt: string;
  expanded_prompt: string;
  workflow_type: string;
  model_used: string;
  llm_used: string;
  aspect_ratio: string;
  seed?: number | null;
  status: string;
  output_path?: string | null;
  output_thumbnail_path?: string | null;
  is_nsfw: boolean;
  is_vaulted: boolean;
  teaser_path?: string | null;
  vault_file_path?: string | null;
  wardrobe_item_id?: number | null;
  error_message?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
}

export interface VaultedGeneration {
  id: number;
  influencer_id: number;
  user_prompt: string;
  teaser_path?: string | null;
  vault_file_path?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
  is_nsfw?: boolean;
}

export interface VaultStatus {
  configured: boolean;
  unlocked: boolean;
  pending_nsfw?: number;
}

export interface WardrobeItem {
  id: number;
  name: string;
  description?: string | null;
  category: string;
  prompt_keywords: string;
  is_shared: boolean;
}

export interface Schedule {
  id: number;
  influencer_id: number;
  schedule_time: string;
  frequency: string;
  prompt_template: string;
  is_active: boolean;
  next_trigger?: string | null;
}

export interface BootstrapStatus {
  ready: boolean;
  progress: number;
  stage: string;
  message: string;
  steps: Array<{ id: string; label: string; status: string; detail?: string }>;
}

export interface QueueStatus {
  pending: number;
  processing: number;
  paused: boolean;
}

export interface SystemStats {
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  gpu_name?: string | null;
  temperature_c?: number | null;
  queue_pending: number;
  queue_processing: number;
}

export interface SettingItem {
  key: string;
  value: string;
}
