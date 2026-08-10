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

export function resolveSelectValue(selected: string, otherText: string): string {
  if (selected === OTHER) {
    return otherText.trim();
  }
  return selected;
}
