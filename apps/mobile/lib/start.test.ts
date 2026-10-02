import { describe, expect, it } from "vitest";

import type { AlertItem, AlertsBlock } from "./alerts";
import { alertPreview, currentWeatherIcon, longestTileWords, quickGridColumns, quickTiles, uvTile, weatherHero, weatherMetrics } from "./start";

const NOW = Date.parse("2026-10-02T12:00:00Z");
const ago = (min: number) => new Date(NOW - min * 60_000).toISOString();
const p = (value: number, unit: string, min = 10) => ({ value, unit, observed_at: ago(min), freshness: "FRESH" });
const src = { freshness: "FRESH", last_success_at: ago(10) };
const air = () => ({
  station_name: "Wrocław, ul. Test",
  distance_km: 2.5,
  coverage: "exact",
  params: { "PM2.5": p(12.4, "µg/m³") },
  index: { level: "GOOD", complete: true, params: { "PM2.5": "GOOD" }, missing: {}, dominant: ["PM2.5"], valid_until: ago(-60) },
  source_status: src,
});
const weather = (extra: Record<string, unknown> = {}) => ({
  observed_at: ago(10),
  params: { temperature_2m: p(16, "°C"), weather_code: p(0, ""), ...extra },
  source_status: src,
});
const cov = { air: "exact", air_radius_km: 10 };

describe("quickTiles", () => {
  it("builds air / weather tiles with real values and no fake pollen or UV", () => {
    const t = quickTiles({ air: air(), weather: weather(), coverage: cov }, { air: src, weather: src }, NOW, NOW);
    expect(t.map((x) => x.key)).toEqual(["air", "weather"]);
    expect(t[0]).toMatchObject({ label: "Powietrze", value: "Dobra", unavailable: false });
    expect(t[0].supporting).toContain("PM2.5");
    expect(t[1]).toMatchObject({ label: "Pogoda", value: "16°C", supporting: "Bezchmurnie" });
  });
  it("UV tile only with a usable uv_index reading", () => {
    expect(uvTile(weather(), src, NOW)).toBeNull();
    const t = uvTile(weather({ uv_index: p(3.24, "") }), src, NOW);
    expect(t).toMatchObject({ key: "uv", value: "3,2", supporting: "Indeks UV", route: "/weather" });
    expect(uvTile(weather({ uv_index: p(3, "", 900) }), src, NOW)).toBeNull(); // stale
  });
  it("an unavailable domain is a neutral, worded tile - never a good-looking value", () => {
    const t = quickTiles({ air: null, weather: null, coverage: { air: "none" } }, { air: { freshness: "UNAVAILABLE", last_success_at: null }, weather: null }, NOW, NOW);
    expect(t[0]).toMatchObject({ key: "air", unavailable: true, value: "Niedostępne" });
    expect(t[0].supporting).toMatch(/stacji|niedostępne/i);
    for (const x of t) if (x.unavailable) expect(x.value).not.toMatch(/Dobr|Niski/);
  });
  it("no technical leftovers in tile text", () => {
    const t = quickTiles({ air: air(), weather: weather(), coverage: cov }, { air: src, weather: src }, NOW, NOW);
    for (const x of t) expect(`${x.value} ${x.supporting}`).not.toMatch(/brak danych|\(brak\)/i);
  });
});

describe("quickGridColumns", () => {
  const short = { value: 6, supporting: 7 }; // "Niskie", "Indeks"
  it("one row of 4 only when the width allows AND no word would be cut", () => {
    expect(quickGridColumns(358, 1, 4, short)).toBe(4);
    expect(quickGridColumns(328, 1, 4, short)).toBe(4);
    expect(quickGridColumns(300, 1, 4, short)).toBe(2);
    expect(quickGridColumns(358, 1, 4, { value: 11, supporting: 12 })).toBe(2); // "Umiarkowana", "zachmurzenie"
  });
  it("big system font always goes to 2 columns", () => {
    expect(quickGridColumns(358, 1.3, 4, short)).toBe(2);
    expect(quickGridColumns(358, 2, 4, short)).toBe(2);
  });
  it("3 tiles stay in a row only if readable, 2 tiles are 2 columns, none is safe", () => {
    expect(quickGridColumns(358, 1, 3, short)).toBe(3);
    expect(quickGridColumns(358, 1, 3, { value: 14, supporting: 12 })).toBe(2);
    expect(quickGridColumns(358, 1, 2)).toBe(2);
    expect(quickGridColumns(358, 1, 0)).toBe(1);
  });
  it("measures the longest word of the real tiles", () => {
    const t = quickTiles({ air: air(), weather: weather(), coverage: cov }, { air: src, weather: src }, NOW, NOW);
    const w = longestTileWords(t);
    expect(w.value).toBeGreaterThanOrEqual(5);
    expect(w.supporting).toBeGreaterThanOrEqual(8);
  });
});

const alert = (id: string, geo: AlertItem["geo_match"]): AlertItem => ({
  external_id: id, source: "imgw_warningshydro", published_at: ago(60), event_type: "Wezbranie", severity_raw: "2", issuing_office: "IMGW",
  description: "x", areas: [{ wojewodztwo: "dolnośląskie" }], valid_from: ago(60), valid_until: ago(-600), fetched_at: ago(5), freshness: "FRESH",
  comment: null, probability_pct: null, geo_match: geo,
});
const block = (items: AlertItem[], fresh = true): AlertsBlock => ({
  attribution: "IMGW", items, scope: "national", source: "imgw",
  source_status: { imgw_warningshydro: fresh ? { freshness: "FRESH", last_success_at: ago(30) } : { freshness: "STALE", last_success_at: ago(3000) } },
});

describe("alertPreview", () => {
  it("a relevant local warning is shown with its own title", () => {
    const a = alert("1", "voivodeship");
    const r = alertPreview(block([a]), [a], NOW, false, false);
    expect(r).toMatchObject({ kind: "local", count: 1 });
    expect(r && "title" in r && r.title).toContain("Wezbranie");
  });
  it("nationwide warnings elsewhere do NOT appear on Start; the confirmed all-clear does", () => {
    const elsewhere = alert("9", null);
    expect(alertPreview(block([elsewhere]), [], NOW, false, false)).toEqual({ kind: "clear", title: "Brak aktywnych ostrzeżeń" });
  });
  it("unresolved warnings are surfaced as 'needs checking', never hidden", () => {
    const u = alert("2", "unresolved");
    expect(alertPreview(block([u]), [u], NOW, false, false)).toMatchObject({ kind: "unresolved", count: 1 });
  });
  it("cannot check (old source, failed refresh, no block) never reads as all-clear", () => {
    expect(alertPreview(block([], false), [], NOW, false, false)?.kind).toBe("unknown");
    expect(alertPreview(block([]), [], NOW, true, false)?.kind).toBe("unknown");
    expect(alertPreview(null, null, NOW, false, false)?.kind).toBe("unknown");
    expect(alertPreview(null, null, NOW, false, true)).toBeNull(); // still loading
  });
});

describe("currentWeatherIcon", () => {
  it("icon from a usable weather_code; none when stale or missing", () => {
    expect(currentWeatherIcon(weather(), src, NOW)).toBe("sunny");
    expect(currentWeatherIcon({ observed_at: ago(900), params: { weather_code: p(61, "", 900) }, source_status: src }, src, NOW)).toBeNull();
    expect(currentWeatherIcon(null, src, NOW)).toBeNull();
  });
});

describe("weatherHero / weatherMetrics", () => {
  const w = weather({ apparent_temperature: p(14.4, "°C"), wind_speed_10m: p(11, "km/h"), precipitation: p(0, "mm", 900) });
  it("hero is a factual one-liner from usable readings", () => {
    const h = weatherHero(w, src, NOW);
    expect(h).toMatchObject({ temp: "16°C", condition: "Bezchmurnie", icon: "sunny" });
    expect(h.summary).toBe("Bezchmurnie, 16°C. Odczuwalna 14,4 °C.");
  });
  it("no data -> no hero values and no summary (never invented)", () => {
    expect(weatherHero(null, null, NOW)).toEqual({ temp: null, condition: null, icon: null, summary: null });
  });
  it("metrics omit missing fields, dim an old one, never include the hero fields", () => {
    const m = weatherMetrics(w, src, NOW);
    const keys = m.map((x) => x.key);
    expect(keys).toContain("wind_speed_10m");
    expect(keys).not.toContain("temperature_2m");
    expect(keys).not.toContain("weather_code");
    expect(keys).not.toContain("relative_humidity_2m"); // not in the block: omitted, not 0
    expect(m.find((x) => x.key === "precipitation")).toMatchObject({ dim: true, note: "nieaktualne" });
  });
});
