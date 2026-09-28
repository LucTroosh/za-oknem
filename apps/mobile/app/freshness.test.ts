import { describe, expect, it } from "vitest";

import { FRESH_MAX_AGE_MS, RECENT_MAX_AGE_MS, freshnessOf } from "./freshness";

// now is an explicit parameter (not the live clock), so exact boundaries are
// deterministic here — unlike a test against a function that calls Date.now()
// internally.
function observedAt(now: number, ageMs: number): string {
  return new Date(now - ageMs).toISOString();
}

describe("freshnessOf", () => {
  const now = Date.now();

  it("is FRESH at age 0", () => {
    expect(freshnessOf(observedAt(now, 0), now)).toBe("FRESH");
  });

  it("is FRESH exactly at the fresh threshold", () => {
    expect(freshnessOf(observedAt(now, FRESH_MAX_AGE_MS), now)).toBe("FRESH");
  });

  it("is RECENT just past the fresh threshold", () => {
    expect(freshnessOf(observedAt(now, FRESH_MAX_AGE_MS + 1), now)).toBe("RECENT");
  });

  it("is RECENT exactly at the recent threshold", () => {
    expect(freshnessOf(observedAt(now, RECENT_MAX_AGE_MS), now)).toBe("RECENT");
  });

  it("is STALE just past the recent threshold", () => {
    expect(freshnessOf(observedAt(now, RECENT_MAX_AGE_MS + 1), now)).toBe("STALE");
  });
});
