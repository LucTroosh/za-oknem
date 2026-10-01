import { describe, expect, it } from "vitest";

import {
  ageFreshness,
  ageLabel,
  asFreshness,
  effectiveFreshness,
  worstFreshness,
} from "./freshness";

const NOW = Date.parse("2026-10-01T12:00:00Z");
const ago = (min: number) => new Date(NOW - min * 60_000).toISOString();
const B = { freshMs: 2 * 3600_000, recentMs: 6 * 3600_000 };

describe("worstFreshness / asFreshness", () => {
  it("picks the worst label; garbage counts as UNAVAILABLE", () => {
    expect(worstFreshness("FRESH", "RECENT")).toBe("RECENT");
    expect(worstFreshness("STALE", "FRESH", "RECENT")).toBe("STALE");
    expect(worstFreshness("FRESH", "UNAVAILABLE")).toBe("UNAVAILABLE");
    expect(worstFreshness("FRESH", "nonsense")).toBe("UNAVAILABLE");
    expect(worstFreshness("FRESH")).toBe("FRESH");
    expect(asFreshness(undefined)).toBe("UNAVAILABLE");
  });
});

describe("effectiveFreshness", () => {
  it("is the worse of data and source_status", () => {
    expect(effectiveFreshness({ freshness: "FRESH", source_status: { freshness: "STALE" } })).toBe("STALE");
    expect(effectiveFreshness({ freshness: "STALE", source_status: { freshness: "FRESH" } })).toBe("STALE");
    expect(effectiveFreshness({ freshness: "FRESH" })).toBe("UNAVAILABLE");
  });
});

describe("ageFreshness", () => {
  it("classifies by the given bounds (inclusive)", () => {
    expect(ageFreshness(ago(120), NOW, B)).toBe("FRESH");
    expect(ageFreshness(ago(121), NOW, B)).toBe("RECENT");
    expect(ageFreshness(ago(360), NOW, B)).toBe("RECENT");
    expect(ageFreshness(ago(361), NOW, B)).toBe("STALE");
  });
  it("future timestamps count as age 0; unusable ones are UNAVAILABLE", () => {
    expect(ageFreshness(ago(-30), NOW, B)).toBe("FRESH");
    expect(ageFreshness("garbage", NOW, B)).toBe("UNAVAILABLE");
    expect(ageFreshness(null, NOW, B)).toBe("UNAVAILABLE");
  });
});

describe("ageLabel", () => {
  it("formats minutes, hours and days", () => {
    expect(ageLabel(ago(0.5), NOW)).toBe("przed chwilą");
    expect(ageLabel(ago(-10), NOW)).toBe("przed chwilą");
    expect(ageLabel(ago(12), NOW)).toBe("12 min temu");
    expect(ageLabel(ago(59), NOW)).toBe("59 min temu");
    expect(ageLabel(ago(60), NOW)).toBe("1 godz. temu");
    expect(ageLabel(ago(47 * 60), NOW)).toBe("47 godz. temu");
    expect(ageLabel(ago(72 * 60), NOW)).toBe("3 dni temu");
  });
  it("is null for unusable input", () => {
    expect(ageLabel("nope", NOW)).toBeNull();
    expect(ageLabel(undefined, NOW)).toBeNull();
  });
});
