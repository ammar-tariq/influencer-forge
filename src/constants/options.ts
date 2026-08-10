/** Shared select lists for the studio UI. Always include a path to custom "Other". */

export const OTHER = "Other";

export const NICHES = [
  "Tech",
  "Gaming",
  "Fashion",
  "Beauty",
  "Fitness",
  "Lifestyle",
  "Travel",
  "Food",
  "Finance",
  "Education",
  "Music",
  "Art",
  "Comedy",
  "Sports",
  "Parenting",
  "Automotive",
  "Photography",
  "Adult",
  OTHER,
] as const;

export const TONES = [
  "Friendly",
  "Witty",
  "Professional",
  "Playful",
  "Bold",
  "Calm",
  "Sarcastic",
  "Inspirational",
  "Luxury",
  "Edgy",
  OTHER,
] as const;

export const HUMORS = [
  "Witty",
  "Dry",
  "Goofy",
  "Deadpan",
  "Wholesome",
  "None / serious",
  OTHER,
] as const;

export const AGE_RATINGS = ["Family", "Teen", "Adult", "18+"] as const;

export const GENDERS = ["Female", "Male", "Trans girl", OTHER] as const;

export const ETHNICITIES = [
  "Caucasian",
  "East Asian",
  "South Asian",
  "Southeast Asian",
  "Black / African",
  "African American",
  "Latino / Hispanic",
  "Middle Eastern",
  "Native American",
  "Pacific Islander",
  "Mixed / Multiracial",
  OTHER,
] as const;

export const SKIN_TONES = [
  "Fair / porcelain",
  "Light",
  "Light-medium",
  "Medium / olive",
  "Tan",
  "Brown",
  "Deep brown",
  "Dark",
  OTHER,
] as const;

export const HEIGHTS = [
  "Petite (under 5'3\" / 160cm)",
  "Average (5'4\"–5'7\" / 163–170cm)",
  "Tall (5'8\"–5'11\" / 173–180cm)",
  "Very tall (6'+ / 183cm+)",
  OTHER,
] as const;

export const BODY_TYPES = [
  "Slim",
  "Athletic",
  "Fit",
  "Curvy",
  "Hourglass",
  "Pear",
  "Apple",
  "Muscular",
  "Soft / plump",
  "Plus-size",
  OTHER,
] as const;

export const BREAST_SIZES = [
  "Flat / small",
  "Small",
  "Medium",
  "Full / large",
  "Very large",
  "Not applicable",
  OTHER,
] as const;

export const CHEST_BUILDS = [
  "Slim chest",
  "Average chest",
  "Broad chest",
  "Muscular chest",
  "Not applicable",
  OTHER,
] as const;

export const WAIST_SIZES = ["Narrow waist", "Average waist", "Soft midsection", OTHER] as const;

export const HIP_SIZES = ["Narrow hips", "Average hips", "Wide hips", OTHER] as const;

export const BUTT_SIZES = ["Flat", "Small", "Round / medium", "Full / large", "Very large", OTHER] as const;

export const MUSCLE_TONES = [
  "Soft",
  "Lightly toned",
  "Athletic definition",
  "Very muscular",
  OTHER,
] as const;

export const BODY_HAIR = [
  "Smooth / shaved",
  "Natural light",
  "Natural",
  "Hairy",
  OTHER,
] as const;

export const HAIR_COLORS = [
  "Black",
  "Dark brown",
  "Brown",
  "Light brown",
  "Blonde",
  "Platinum blonde",
  "Auburn",
  "Red",
  "Copper",
  "Gray",
  "White",
  "Pink",
  "Blue",
  "Purple",
  "Green",
  "Silver",
  OTHER,
] as const;

export const HAIR_STYLES = [
  "Long straight",
  "Long wavy",
  "Long curly",
  "Medium straight",
  "Medium wavy",
  "Short straight",
  "Short curly",
  "Bob",
  "Pixie",
  "Ponytail",
  "Bun",
  "Braids",
  "Cornrows",
  "Afro",
  "Dreadlocks",
  "Undercut",
  "Bald / shaved",
  OTHER,
] as const;

export const EYE_COLORS = [
  "Brown",
  "Dark brown",
  "Hazel",
  "Amber",
  "Green",
  "Blue",
  "Gray",
  "Black",
  "Heterochromia",
  OTHER,
] as const;

export const LOOK_STYLES = [
  "Casual",
  "Elegant",
  "Sporty",
  "Streetwear",
  "Business",
  "Bohemian",
  "Glam",
  "Minimalist",
  "Vintage",
  "Techwear",
  "Athleisure",
  "Gothic",
  "Y2K",
  "Preppy",
  OTHER,
] as const;

export const WARDROBE_CATEGORIES = [
  "Top",
  "Bottom",
  "Full Outfit",
  "Accessory",
  "Footwear",
  "Outerwear",
  "Swimwear",
  "Lingerie",
  OTHER,
] as const;

export const SCHEDULE_FREQUENCIES = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "custom", label: "Custom / Other" },
] as const;

export const ASPECT_RATIOS = [
  { value: "9:16", label: "9:16 · Portrait / Reels" },
  { value: "1:1", label: "1:1 · Square" },
  { value: "16:9", label: "16:9 · Landscape" },
] as const;

export const WORKFLOW_TYPES = [
  { value: "image", label: "Image" },
  { value: "video", label: "Video (AnimateDiff path)" },
] as const;

/** Camera framing — default full body so the whole influencer is visible. */
export const FRAMINGS = [
  { value: "full_body", label: "Full body", prompt: "full body shot, head to toe visible in frame" },
  { value: "three_quarter", label: "3/4 body", prompt: "three-quarter body shot from thighs up" },
  { value: "waist_up", label: "Waist up", prompt: "waist-up medium shot" },
  { value: "upper_body", label: "Upper body", prompt: "upper body shot, chest and shoulders" },
  { value: "close_up", label: "Face close-up", prompt: "close-up face portrait" },
  { value: "from_behind", label: "From behind", prompt: "full body from behind, looking over shoulder" },
] as const;

export const POSES = [
  { value: "standing", label: "Standing", prompt: "standing naturally, relaxed posture" },
  { value: "hands_hips", label: "Hands on hips", prompt: "standing with hands on hips" },
  { value: "walking", label: "Walking", prompt: "walking toward camera" },
  { value: "sitting", label: "Sitting", prompt: "sitting pose" },
  { value: "leaning", label: "Leaning", prompt: "leaning against a wall" },
  { value: "lying", label: "Lying down", prompt: "lying on a bed or couch" },
  { value: "kneeling", label: "Kneeling", prompt: "kneeling pose" },
  { value: "arched", label: "Arched back", prompt: "arched back pose" },
  { value: "other", label: "Other / custom", prompt: "" },
] as const;

export const DRESSINGS = [
  { value: "casual", label: "Casual clothes", prompt: "wearing casual everyday outfit", nsfw: false },
  { value: "elegant", label: "Elegant / dress", prompt: "wearing an elegant dress", nsfw: false },
  { value: "athleisure", label: "Athleisure / gym", prompt: "wearing athleisure gym outfit", nsfw: false },
  { value: "streetwear", label: "Streetwear", prompt: "wearing stylish streetwear", nsfw: false },
  { value: "swimwear", label: "Swimwear / bikini", prompt: "wearing a bikini swimsuit", nsfw: false },
  { value: "lingerie", label: "Lingerie", prompt: "wearing lingerie", nsfw: true },
  { value: "topless", label: "Topless", prompt: "topless, bare breasts, no top", nsfw: true },
  { value: "nude", label: "Fully nude", prompt: "fully nude, no clothing", nsfw: true },
  { value: "other", label: "Other / custom", prompt: "", nsfw: false },
] as const;

export const SETTINGS = [
  { value: "studio", label: "Studio", prompt: "clean photo studio background" },
  { value: "bedroom", label: "Bedroom", prompt: "in a modern bedroom" },
  { value: "beach", label: "Beach", prompt: "on a sunny beach" },
  { value: "outdoors", label: "Outdoors / park", prompt: "outdoors in a park, golden hour" },
  { value: "city", label: "City street", prompt: "on a city street" },
  { value: "gym", label: "Gym", prompt: "inside a fitness gym" },
  { value: "bathroom", label: "Bathroom / mirror", prompt: "bathroom mirror selfie setting" },
  { value: "other", label: "Other / custom", prompt: "" },
] as const;

export function resolveSelectValue(selected: string, otherText: string): string {
  if (selected === OTHER) {
    return otherText.trim();
  }
  return selected;
}

export function composeScenePrompt(input: {
  framing: string;
  pose: string;
  dressing: string;
  setting: string;
  poseOther?: string;
  dressingOther?: string;
  settingOther?: string;
  notes?: string;
}): { prompt: string; nsfw: boolean } {
  const framing = FRAMINGS.find((f) => f.value === input.framing)?.prompt ?? FRAMINGS[0].prompt;
  const poseOpt = POSES.find((p) => p.value === input.pose);
  const dressOpt = DRESSINGS.find((d) => d.value === input.dressing);
  const setOpt = SETTINGS.find((s) => s.value === input.setting);

  const pose =
    input.pose === "other" ? (input.poseOther || "").trim() : (poseOpt?.prompt ?? "");
  const dressing =
    input.dressing === "other" ? (input.dressingOther || "").trim() : (dressOpt?.prompt ?? "");
  const setting =
    input.setting === "other" ? (input.settingOther || "").trim() : (setOpt?.prompt ?? "");

  const parts = [framing, pose, dressing, setting, (input.notes || "").trim()].filter(Boolean);
  const prompt = parts.join(", ");
  const nsfw =
    Boolean(dressOpt?.nsfw) ||
    /\b(nude|topless|naked|lingerie)\b/i.test(`${dressing} ${input.notes || ""}`);
  return { prompt, nsfw };
}
