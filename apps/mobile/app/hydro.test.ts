import { describe, expect, it } from "vitest";

import { type HydroBlock, type HydroStation, ageFreshness, hydroLevelLine, summarizeHydro } from "./hydro";

const NOW = Date.parse("2026-09-30T12:00:00Z");
const ago = (h: number) => new Date(NOW - h * 3600_000).toISOString();

const station = (over: Partial<HydroStation> = {}): HydroStation => ({
  station_id: "1",
  station_name: "A (Rzeka)",
  latitude: 50,
  longitude: 20,
  water_level_cm: 300,
  warning_level_cm: 250,
  alarm_level_cm: 350,
  status: "WARNING",
  unit: "cm",
  observed_at: ago(0.5),
  freshness: "FRESH",
  source: "imgw_hydro",
  ...over,
});

const block = (
  stations: Partial<HydroStation>[],
  source: { freshness?: string; last?: string | null } = {},
): HydroBlock =>
  ({
    stations: stations.map(station),
    attribution: "x",
    source_status: {
      freshness: source.freshness ?? "FRESH",
      last_success_at: source.last === undefined ? ago(0.5) : source.last,
    },
  }) as unknown as HydroBlock;

describe("summarizeHydro", () => {
  it("lists ALARM before WARNING and caps with a 'more' counter", () => {
    const s = summarizeHydro(
      block([
        { station_id: "1", station_name: "B", status: "WARNING" },
        { station_id: "2", station_name: "C", status: "ALARM" },
        { station_id: "3", station_name: "A", status: "WARNING" },
        { station_id: "4", station_name: "D", status: "NORMAL" },
      ]),
      NOW,
      2,
    );
    expect(s.kind).toBe("list");
    if (s.kind !== "list") return;
    expect(s.items.map((i) => i.station.station_id)).toEqual(["2", "3"]);
    expect(s.more).toBe(1);
    expect(s.outdated).toBe(false);
  });

  it("confirms 'none' only with healthy source and a current reading, counting unassessed", () => {
    expect(
      summarizeHydro(block([{ status: "NORMAL" }, { station_id: "2", status: "UNKNOWN" }]), NOW),
    ).toEqual({ kind: "none-confirmed", unassessed: 1 });
  });

  it("never confirms 'none' when the source is stale", () => {
    expect(
      summarizeHydro(block([{ status: "NORMAL" }], { freshness: "STALE", last: ago(10) }), NOW),
    ).toEqual({ kind: "unavailable", lastSuccessAt: ago(10) });
  });

  it("never confirms 'none' when the source was never fetched", () => {
    expect(
      summarizeHydro(block([{ status: "NORMAL" }], { freshness: "UNAVAILABLE", last: null }), NOW),
    ).toEqual({ kind: "unavailable", lastSuccessAt: null });
  });

  it("never confirms 'none' with an empty station list", () => {
    expect(summarizeHydro(block([]), NOW).kind).toBe("unavailable");
  });

  it("never confirms 'none' when every reading is old, even if the server said FRESH", () => {
    const old = { status: "NORMAL" as const, observed_at: ago(7), freshness: "FRESH" as const };
    expect(summarizeHydro(block([old]), NOW).kind).toBe("unavailable");
  });

  it("ages the source on the device: server FRESH, last success 7h ago -> not confirmed", () => {
    expect(summarizeHydro(block([{ status: "NORMAL" }], { last: ago(7) }), NOW).kind).toBe(
      "unavailable",
    );
  });

  it("UNKNOWN stations alone are not an all-clear", () => {
    expect(summarizeHydro(block([{ status: "UNKNOWN" }]), NOW)).toEqual({
      kind: "none-confirmed",
      unassessed: 1,
    });
  });

  it("flags a list as outdated and ages each station at `now`", () => {
    const s = summarizeHydro(
      block([{ status: "ALARM", observed_at: ago(8) }], { freshness: "STALE", last: ago(8) }),
      NOW,
    );
    expect(s.kind === "list" && s.outdated).toBe(true);
    expect(s.kind === "list" && s.items[0]?.freshness).toBe("STALE");
  });

  it("degrades without throwing on missing fields", () => {
    const broken = { stations: undefined, attribution: "x" } as unknown as HydroBlock;
    expect(summarizeHydro(broken, NOW)).toEqual({ kind: "unavailable", lastSuccessAt: null });
  });

  it("ignores statuses it does not know", () => {
    expect(summarizeHydro(block([{ status: "SEVERE" as never }]), NOW)).toEqual({
      kind: "none-confirmed",
      unassessed: 1,
    });
  });
});

describe("ageFreshness", () => {
  it("uses 2h/6h thresholds and degrades on garbage", () => {
    expect(ageFreshness(ago(1), NOW)).toBe("FRESH");
    expect(ageFreshness(ago(3), NOW)).toBe("RECENT");
    expect(ageFreshness(ago(7), NOW)).toBe("STALE");
    expect(ageFreshness("nope", NOW)).toBe("UNAVAILABLE");
    expect(ageFreshness(undefined, NOW)).toBe("UNAVAILABLE");
  });
});

describe("hydroLevelLine", () => {
  it("shows level and only the thresholds that exist", () => {
    expect(hydroLevelLine(station({ alarm_level_cm: null }))).toBe("300 cm · próg ostrzegawczy 250 cm");
  });
});
