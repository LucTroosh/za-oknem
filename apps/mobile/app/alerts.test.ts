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

describe("summarizeAlerts (ADR-012)", () => {
  it("confirms no alerts only when every source is fresh", () => {
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["FRESH", "t"] }))).toEqual({
      kind: "none-confirmed",
      sources: ["IMGW – ostrzeżenia hydrologiczne"],
    });
  });

  it("never claims 'no alerts' when a source is stale", () => {
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["STALE", "2026-09-29T00:00:00Z"] }))).toEqual({
      kind: "unavailable",
      lastSuccessAt: "2026-09-29T00:00:00Z",
    });
  });

  it("never claims 'no alerts' when a source was never fetched", () => {
    expect(summarizeAlerts(block(0, { imgw_warningshydro: ["UNAVAILABLE", null] }))).toEqual({
      kind: "unavailable",
      lastSuccessAt: null,
    });
  });

  it("never claims 'no alerts' when no source status is present", () => {
    expect(summarizeAlerts(block(0, {})).kind).toBe("unavailable");
  });

  it("flags a non-empty list as possibly outdated when a source is stale", () => {
    expect(summarizeAlerts(block(2, { imgw_warningshydro: ["STALE", "t0"] }))).toEqual({
      kind: "list-maybe-outdated",
      lastSuccessAt: "t0",
    });
  });

  it("uses the oldest last success across unhealthy sources", () => {
    const summary = summarizeAlerts(
      block(0, { a: ["STALE", "2026-09-29T10:00:00Z"], b: ["STALE", "2026-09-28T10:00:00Z"] }),
    );
    expect(summary).toEqual({ kind: "unavailable", lastSuccessAt: "2026-09-28T10:00:00Z" });
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
