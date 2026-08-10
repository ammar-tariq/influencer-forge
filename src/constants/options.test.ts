import { describe, expect, it } from "vitest";
import {
  OTHER,
  NICHES,
  composeScenePrompt,
  resolveSelectValue,
  splitSelectValue,
} from "./options";

describe("resolveSelectValue", () => {
  it("returns listed option as-is", () => {
    expect(resolveSelectValue("Tech", "ignored")).toBe("Tech");
  });

  it("returns trimmed custom text when Other is selected", () => {
    expect(resolveSelectValue(OTHER, "  indie music  ")).toBe("indie music");
  });

  it("returns empty string when Other and blank custom", () => {
    expect(resolveSelectValue(OTHER, "   ")).toBe("");
  });
});

describe("splitSelectValue", () => {
  it("keeps listed values on the select", () => {
    expect(splitSelectValue("Fitness", NICHES)).toEqual({ value: "Fitness", other: "" });
  });

  it("maps custom stored values to Other", () => {
    expect(splitSelectValue("indie music", NICHES)).toEqual({
      value: OTHER,
      other: "indie music",
    });
  });
});

describe("composeScenePrompt", () => {
  it("builds a full-body dressed scene and marks nude as NSFW", () => {
    const dressed = composeScenePrompt({
      framing: "full_body",
      pose: "standing",
      dressing: "casual",
      setting: "studio",
    });
    expect(dressed.prompt).toContain("full body");
    expect(dressed.prompt).toContain("casual");
    expect(dressed.nsfw).toBe(false);

    const nude = composeScenePrompt({
      framing: "full_body",
      pose: "standing",
      dressing: "nude",
      setting: "bedroom",
    });
    expect(nude.nsfw).toBe(true);
    expect(nude.prompt).toContain("fully nude");
  });
});
