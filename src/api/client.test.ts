import { describe, expect, it } from "vitest";
import { mediaUrl, setMediaEpoch } from "./client";

describe("mediaUrl", () => {
  it("maps generation paths to local media routes", () => {
    setMediaEpoch("0");
    expect(mediaUrl("/tmp/media/generations/12.png")).toContain("/media/generations/12.png");
    expect(mediaUrl("/tmp/media/thumbnails/12_thumb.png")).toContain("/media/thumbnails/12_thumb.png");
    expect(mediaUrl(null)).toBeUndefined();
  });

  it("maps face-seed uploads under /media/uploads", () => {
    expect(mediaUrl("/tmp/media/uploads/face_1_seed.png")).toContain("/media/uploads/face_1_seed.png");
    expect(mediaUrl("/legacy/uploads/face_2_photo.jpg")).toContain("/media/uploads/face_2_photo.jpg");
  });

  it("appends media epoch so reset invalidates cached filenames", () => {
    setMediaEpoch("99");
    const url = mediaUrl("/tmp/media/generations/1.png");
    expect(url).toContain("/media/generations/1.png");
    expect(url).toContain("e=99");
    setMediaEpoch("0");
  });

  it("passes through http URLs with epoch for local media", () => {
    setMediaEpoch("7");
    expect(mediaUrl("http://127.0.0.1:8765/media/generations/1.png")).toBe(
      "http://127.0.0.1:8765/media/generations/1.png?e=7",
    );
    setMediaEpoch("0");
  });
});
