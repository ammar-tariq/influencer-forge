import { describe, expect, it } from "vitest";
import { mediaUrl } from "./client";

describe("mediaUrl", () => {
  it("maps generation paths to local media routes", () => {
    expect(mediaUrl("/tmp/media/generations/12.png")).toContain("/media/generations/12.png");
    expect(mediaUrl("/tmp/media/thumbnails/12_thumb.png")).toContain("/media/thumbnails/12_thumb.png");
    expect(mediaUrl(null)).toBeUndefined();
  });
});
