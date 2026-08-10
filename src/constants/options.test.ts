import { describe, expect, it } from "vitest";
import { OTHER, composeScenePrompt, resolveSelectValue } from "./options";

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
