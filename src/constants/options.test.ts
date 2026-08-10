import { describe, expect, it } from "vitest";
import { OTHER, resolveSelectValue } from "./options";

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
