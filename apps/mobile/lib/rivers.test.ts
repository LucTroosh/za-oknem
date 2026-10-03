import { describe, expect, it } from "vitest";

import type { HydroBlock, HydroStation } from "./hydro";
import { RIVERS_PAGE, buildRivers, limitGroups, normalizeName } from "./rivers";

const NOW = Date.parse("2026-10-02T12:00:00Z");
const st = (id: string, name: string, status: HydroStation["status"], over: Partial<HydroStation> = {}): HydroStation => ({
  station_id: id,
  station_name: name,
  status,
  source: "imgw_hydro",
  latitude: 50,
  longitude: 18,
  unit: "cm",
  water_level_cm: 100,
  warning_level_cm: status === "UNKNOWN" ? null : 200,
  alarm_level_cm: status === "UNKNOWN" ? null : 300,
  observed_at: "2026-10-02T11:30:00Z",
  freshness: "FRESH",
  ...over,
});
const block = (stations: HydroStation[], status: HydroBlock["source_status"] = { freshness: "FRESH", last_success_at: "2026-10-02T11:30:00Z" }): HydroBlock => ({
  attribution: "IMGW",
  source_status: status,
  stations,
});

describe("normalizeName", () => {
  it("folds case, diacritics and ł", () => {
    expect(normalizeName("  Kłodzko   NYSA ")).toBe("klodzko nysa");
    expect(normalizeName("Świnoujście")).toBe("swinoujscie");
  });
});

describe("buildRivers", () => {
  it("groups in a fixed order and sorts by name", () => {
    const m = buildRivers(block([st("3", "B", "NORMAL"), st("1", "Z", "ALARM"), st("2", "A", "WARNING"), st("4", "C", "UNKNOWN")]), NOW);
    expect(m.groups.map((g) => g.key)).toEqual(["alarm", "warning", "normal", "unassessed"]);
    expect(m.total).toBe(4);
  });
  it("an old NORMAL reading does not claim 'below thresholds'", () => {
    const m = buildRivers(block([st("1", "A", "NORMAL", { observed_at: "2026-10-01T00:00:00Z", freshness: "FRESH" })]), NOW);
    expect(m.groups.map((g) => g.key)).toEqual(["outdated"]);
  });
  it("an old ALARM stays an alarm (never hidden)", () => {
    const m = buildRivers(block([st("1", "A", "ALARM", { observed_at: "2026-10-01T00:00:00Z", freshness: "STALE" })]), NOW);
    expect(m.groups[0].key).toBe("alarm");
    expect(m.groups[0].items[0].freshness).toBe("STALE");
  });
  it("stations without thresholds are 'not assessed', never normal", () => {
    const m = buildRivers(block([st("1", "A", "UNKNOWN")]), NOW);
    expect(m.groups[0].key).toBe("unassessed");
  });
  it("filters by name without diacritics", () => {
    const m = buildRivers(block([st("1", "Kłodzko", "NORMAL"), st("2", "Opole", "NORMAL")]), NOW, "klodz");
    expect(m.groups[0].items.map((i) => i.station.station_id)).toEqual(["1"]);
    expect(m.total).toBe(1);
  });
  it("source health uses the device clock", () => {
    expect(buildRivers(block([]), NOW).sourceOk).toBe(true);
    expect(buildRivers(block([], { freshness: "FRESH", last_success_at: "2026-10-02T01:00:00Z" }), NOW).sourceOk).toBe(false);
    expect(buildRivers(block([], { freshness: "UNAVAILABLE", last_success_at: null }), NOW).sourceOk).toBe(false);
  });
  it("tolerates a missing stations array", () => {
    expect(buildRivers({ attribution: "x", source_status: { freshness: "FRESH", last_success_at: null }, stations: undefined as never }, NOW).total).toBe(0);
  });
});

describe("limitGroups", () => {
  it("keeps the first rows across groups and drops empty groups", () => {
    const m = buildRivers(block(Array.from({ length: 5 }, (_, i) => st(String(i), `S${i}`, i < 2 ? "ALARM" : "NORMAL"))), NOW);
    const l = limitGroups(m.groups, 3);
    expect(l.map((g) => g.items.length)).toEqual([2, 1]);
    expect(limitGroups(m.groups, 2).map((g) => g.key)).toEqual(["alarm"]);
    expect(RIVERS_PAGE).toBeGreaterThan(0);
  });
});

it("sorts nearby stations by distance before their names, regardless of input order", () => {
 const far = st("far", "A", "NORMAL", { distance_km: 10 });
 const near = st("near", "Z", "NORMAL", { distance_km: 1 });
 for (const stations of [[far, near], [near, far]]) {
   expect(buildRivers(block(stations), NOW).groups[0].items.map(i => i.station.station_id)).toEqual(["near", "far"]);
 }
});
