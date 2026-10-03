import { describe, expect, it } from "vitest";

import { type AlertItem, type AlertsBlock, alertAreasLabel, alertKey, summarizeAlerts } from "./alerts";

describe("alertAreasLabel", () => {
  it("joins unique voivodeship names", () => {
    expect(
      alertAreasLabel([
        { wojewodztwo: "wielkopolskie" },
        { wojewodztwo: "wielkopolskie" },
        { wojewodztwo: "łódzkie" },
      ]),
    ).toBe("wielkopolskie, łódzkie");
  });

  it("skips entries without a usable name instead of guessing", () => {
    expect(alertAreasLabel([{ wojewodztwo: null }, { powiat: "x" }, {}])).toBe("");
  });
});

const block = (items: number, statuses: Record<string, [string, string | null]>) =>
  ({
    scope: "national",
    source: "imgw",
    attribution: "x",
    items: Array.from({ length: items }, (_, i) => ({ external_id: String(i) })),
    source_status: Object.fromEntries(
      Object.entries(statuses).map(([id, [freshness, last]]) => [
        id,
        { freshness, last_success_at: last },
      ]),
    ),
  }) as unknown as AlertsBlock;

// Fixed device clock: statuses age relative to this, never to the wall clock.
const NOW = Date.parse("2026-09-30T12:00:00Z");
const HOURS_AGO = (h: number) => new Date(NOW - h * 3_600_000).toISOString();

describe("summarizeAlerts (ADR-012)", () => {
  it("confirms no alerts only when every source is fresh", () => {
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["FRESH", HOURS_AGO(1)] }), NOW)).toEqual({
      kind: "none-confirmed",
      sources: ["IMGW – ostrzeżenia hydrologiczne"],
    });
  });

  it("never claims 'no alerts' when a source is stale", () => {
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["STALE", "2026-09-29T00:00:00Z"] }), NOW)).toEqual({
      kind: "unavailable",
      lastSuccessAt: "2026-09-29T00:00:00Z",
    });
  });

  it("never claims 'no alerts' when a source was never fetched", () => {
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["UNAVAILABLE", null] }), NOW)).toEqual({
      kind: "unavailable",
      lastSuccessAt: null,
    });
  });

  it("never claims 'no alerts' when no source status is present", () => {
    expect(summarizeAlerts(block(0, {}), NOW).kind).toBe("unavailable");
  });

  it("degrades instead of throwing when source_status is missing (older API)", () => {
    const legacy = { ...block(0, {}), source_status: undefined } as unknown as AlertsBlock;
    expect(summarizeAlerts(legacy, NOW).kind).toBe("unavailable");
  });

  it("flags a non-empty list as possibly outdated when a source is stale", () => {
    const last = HOURS_AGO(30);
    expect(summarizeAlerts(block(2, { imgw_warningshydro: ["STALE", last] }), NOW)).toEqual({
      kind: "list-maybe-outdated",
      lastSuccessAt: last,
    });
  });

  it("uses the oldest last success across unhealthy sources", () => {
    const summary = summarizeAlerts(
      block(0, { a: ["STALE", "2026-09-29T10:00:00Z"], b: ["STALE", "2026-09-28T10:00:00Z"] }),
      NOW,
    );
    expect(summary).toEqual({ kind: "unavailable", lastSuccessAt: "2026-09-28T10:00:00Z" });
  });

  it("stops trusting a FRESH status once the screen has been open past the 6h bound", () => {
    // The response was FRESH when fetched, but the device never refetched.
    const last = HOURS_AGO(7);
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["FRESH", last] }), NOW)).toEqual({
      kind: "unavailable",
      lastSuccessAt: last,
    });
    expect(summarizeAlerts(block(1, { imgw_warningshydro: ["FRESH", last] }), NOW).kind).toBe(
      "list-maybe-outdated",
    );
  });

  it("still trusts a status right at the bound", () => {
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["RECENT", HOURS_AGO(6)] }), NOW).kind).toBe(
      "none-confirmed",
    );
  });

  it("does not trust an unparseable last_success_at", () => {
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["FRESH", "not-a-date"] }), NOW).kind).toBe(
      "unavailable",
    );
  });
});

describe("alertKey", () => {
  it("differs for the same external_id from another source or revision", () => {
    const base = { external_id: "31", source: "imgw_warningshydro", published_at: "t1" };
    const keys = new Set(
      [base, { ...base, source: "imgw_warningsmeteo" }, { ...base, published_at: "t2" }].map(
        (a) => alertKey(a as AlertItem),
      ),
    );
    expect(keys.size).toBe(3);
  });
});

it("expires a confirmed empty meteo snapshot after 15 min on the device", () => {
  const b = block(0, { imgw_warningsmeteo: ["FRESH", new Date(NOW - 14 * 60 * 1000).toISOString()] });
  expect(summarizeAlerts(b, NOW).kind).toBe("none-confirmed");
  expect(summarizeAlerts(b, NOW + 2 * 60 * 1000).kind).toBe("unavailable");
});
