import { describe, expect, it } from "vitest";

import { airView, formatNumber, readingLine, sourceState, withUnit, AIR_AGE } from "./readings";

const NOW = Date.parse("2026-10-01T12:00:00Z");
const ago = (min: number) => new Date(NOW - min * 60_000).toISOString();
const param = (value: unknown, min: number, freshness = "FRESH", unit = "µg/m³") => ({
  value,
  unit,
  observed_at: ago(min),
  freshness,
});
const fmt = (v: number, u: unknown) => withUnit(String(v), u);
const ok = { state: null, lastSuccessAt: null } as const;

describe("formatNumber / withUnit", () => {
  it("keeps 0 and negatives, never prints -0, uses a decimal comma", () => {
    expect(formatNumber(0, 1)).toBe("0");
    expect(formatNumber(-3.44, 1)).toBe("-3,4");
    expect(formatNumber(-0.04, 1)).toBe("0");
    expect(formatNumber(12, 1)).toBe("12");
    expect(formatNumber(12.34, 0)).toBe("12");
  });
  it("is null for null, undefined, NaN, Infinity and non-numbers", () => {
    for (const v of [null, undefined, Number.NaN, Number.POSITIVE_INFINITY, "5"]) {
      expect(formatNumber(v, 1)).toBeNull();
    }
  });
  it("joins units: space, but % and ° attach, empty unit adds nothing", () => {
    expect(withUnit("12", "km/h")).toBe("12 km/h");
    expect(withUnit("55", "%")).toBe("55%");
    expect(withUnit("1", "")).toBe("1");
    expect(withUnit("1", undefined)).toBe("1");
  });
});

describe("readingLine", () => {
  it("FRESH: normal, age only", () => {
    const l = readingLine("PM2.5", "PM2.5", param(11.5, 10), ok, NOW, AIR_AGE, fmt);
    expect(l).toMatchObject({ state: "ok", text: "11.5 µg/m³", note: "10 min temu" });
  });
  it("RECENT: flagged with label and age", () => {
    const l = readingLine("k", "k", param(11.5, 200, "RECENT"), ok, NOW, AIR_AGE, fmt);
    expect(l).toMatchObject({ state: "recent", note: "niedawne · 3 godz. temu" });
  });
  it("STALE by server label keeps the value but marks it old", () => {
    const l = readingLine("k", "k", param(11.5, 600, "STALE"), ok, NOW, AIR_AGE, fmt);
    expect(l).toMatchObject({ state: "stale", text: "11.5 µg/m³", note: "nieaktualne · 10 godz. temu" });
  });
  it("a label that was FRESH at fetch time ages on the device clock", () => {
    const l = readingLine("k", "k", param(11.5, 400, "FRESH"), ok, NOW, AIR_AGE, fmt);
    expect(l.state).toBe("stale");
  });
  it("source STALE/RECENT drags a FRESH reading down; healthy/unknown source does not", () => {
    const stale = { state: "STALE", lastSuccessAt: ago(900) } as const;
    expect(readingLine("k", "k", param(1, 5), stale, NOW, AIR_AGE, fmt).state).toBe("stale");
    const recent = { state: "RECENT", lastSuccessAt: ago(200) } as const;
    expect(readingLine("k", "k", param(1, 5), recent, NOW, AIR_AGE, fmt).state).toBe("recent");
    expect(readingLine("k", "k", param(1, 5), { state: "FRESH", lastSuccessAt: ago(5) }, NOW, AIR_AGE, fmt).state).toBe("ok");
  });
  it("0 is a value; null/missing/NaN/garbage timestamp are 'brak danych'", () => {
    expect(readingLine("k", "k", param(0, 5), ok, NOW, AIR_AGE, fmt).text).toBe("0 µg/m³");
    for (const r of [param(null, 5), undefined, null, param(Number.NaN, 5), { ...param(1, 5), observed_at: "x" }]) {
      expect(readingLine("k", "k", r, ok, NOW, AIR_AGE, fmt)).toMatchObject({ state: "missing", text: "brak danych" });
    }
  });
  it("negative values pass through", () => {
    expect(readingLine("k", "k", param(-5, 5, "FRESH", "°C"), ok, NOW, AIR_AGE, fmt).text).toBe("-5 °C");
  });
});

describe("sourceState", () => {
  it("absent source_status = no constraint (older backend)", () => {
    expect(sourceState({}, NOW, AIR_AGE)).toEqual({ state: null, lastSuccessAt: null });
  });
  it("UNAVAILABLE stays UNAVAILABLE; healthy label ages with the clock", () => {
    expect(sourceState({ source_status: { freshness: "UNAVAILABLE", last_success_at: null } }, NOW, AIR_AGE).state).toBe("UNAVAILABLE");
    expect(sourceState({ source_status: { freshness: "FRESH", last_success_at: ago(30) } }, NOW, AIR_AGE).state).toBe("FRESH");
    expect(sourceState({ source_status: { freshness: "FRESH", last_success_at: ago(500) } }, NOW, AIR_AGE).state).toBe("STALE");
  });
  it("FRESH label with no success time cannot be verified", () => {
    expect(sourceState({ source_status: { freshness: "FRESH", last_success_at: null } }, NOW, AIR_AGE).state).toBe("UNAVAILABLE");
  });
});

describe("airView with a null block (top-level source_status)", () => {
  it("source never succeeded -> unavailable instead of 'brak stacji'", () => {
    const v = airView(null, NOW, { freshness: "UNAVAILABLE", last_success_at: null });
    expect(v).toMatchObject({ unavailable: true, suppressDerived: true });
  });
  it("silent source -> note, no values", () => {
    const v = airView(null, NOW, { freshness: "STALE", last_success_at: ago(900) });
    expect(v).toMatchObject({ unavailable: false, lines: [], suppressDerived: true });
    expect(v?.sourceNote).toContain("15 godz. temu");
  });
});

describe("airView suppressDerived (AQI badge)", () => {
  const b = (freshness: string) => ({
    params: { "PM2.5": param(11.5, 10) },
    source_status: { freshness, last_success_at: freshness === "UNAVAILABLE" ? null : ago(10) },
  });
  it("hidden for UNAVAILABLE and STALE source, shown for healthy or unknown", () => {
    expect(airView(b("UNAVAILABLE"), NOW)?.suppressDerived).toBe(true);
    expect(airView(b("STALE"), NOW)?.suppressDerived).toBe(true);
    expect(airView(b("FRESH"), NOW)?.suppressDerived).toBe(false);
    expect(airView({ params: {} }, NOW)?.suppressDerived).toBe(false);
  });
});

describe("airView", () => {
  const block = (extra: object = {}) => ({
    attribution: "GIOŚ",
    params: { "PM2.5": param(11.5, 10), PM10: param(null, 10) },
    source_status: { freshness: "FRESH", last_success_at: ago(10) },
    ...extra,
  });
  it("lists every param; a null one is 'brak danych'", () => {
    const v = airView(block(), NOW);
    expect(v?.lines.map((l) => [l.key, l.state])).toEqual([["PM2.5", "ok"], ["PM10", "missing"]]);
    expect(v?.attribution).toBe("GIOŚ");
    expect(v?.sourceNote).toBeNull();
  });
  it("source never succeeded -> unavailable, no values shown", () => {
    const v = airView(block({ source_status: { freshness: "UNAVAILABLE", last_success_at: null } }), NOW);
    expect(v).toMatchObject({ unavailable: true, lines: [] });
  });
  it("stale source -> warning note and dimmed lines", () => {
    const v = airView(block({ source_status: { freshness: "STALE", last_success_at: ago(900) } }), NOW);
    expect(v?.sourceNote).toBe("Źródło nie odświeża się — ostatnia aktualizacja 15 godz. temu.");
    expect(v?.lines[0].state).toBe("stale");
  });
  it("null or garbage block -> null (screen shows 'brak stacji')", () => {
    expect(airView(null, NOW)).toBeNull();
    expect(airView("x", NOW)).toBeNull();
    expect(airView(null, NOW, { freshness: "FRESH", last_success_at: ago(10) })).toBeNull();
    expect(airView({ params: null }, NOW)?.lines).toEqual([]);
  });
});
