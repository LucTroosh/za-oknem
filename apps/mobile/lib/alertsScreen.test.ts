import { describe, expect, it } from "vitest";

import { type AlertItem, type AlertsBlock, alertKey } from "./alerts";
import { areaNames, buildAlertsScreen, findAlert } from "./alertsScreen";

const NOW = Date.parse("2026-10-02T12:00:00Z");
const alert = (id: string, geo: AlertItem["geo_match"] = null, areas: Record<string, unknown>[] = [{ wojewodztwo: "śląskie" }]): AlertItem => ({
  external_id: id,
  source: "imgw_warningshydro",
  published_at: "2026-10-02T08:00:00Z",
  event_type: "Wezbranie",
  severity_raw: "2",
  issuing_office: "IMGW",
  description: "Treść źródłowa",
  areas,
  valid_from: "2026-10-02T08:00:00Z",
  valid_until: "2026-10-03T08:00:00Z",
  fetched_at: "2026-10-02T11:00:00Z",
  freshness: "FRESH",
  comment: null,
  probability_pct: null,
  geo_match: geo,
});
type Status = { freshness: "FRESH" | "RECENT" | "STALE" | "UNAVAILABLE"; last_success_at: string | null };
const ok: Status = { freshness: "FRESH", last_success_at: "2026-10-02T11:30:00Z" };
const block = (items: AlertItem[], status: Status = ok): AlertsBlock => ({
  attribution: "IMGW",
  items,
  scope: "national",
  source: "imgw",
  source_status: { imgw_warningshydro: status },
});

describe("buildAlertsScreen", () => {
  it("splits local / unresolved / elsewhere; unresolved is never hidden", () => {
    const a = alert("1");
    const b = alert("2");
    const c = alert("3");
    const m = buildAlertsScreen(block([a, b, c]), [{ ...a, geo_match: "voivodeship" }, { ...b, geo_match: "unresolved" }], NOW, false);
    expect(m.local.map((x) => x.external_id)).toEqual(["1"]);
    expect(m.unresolved.map((x) => x.external_id)).toEqual(["2"]);
    expect(m.elsewhere.map((x) => x.external_id)).toEqual(["3"]);
    expect(m.localStatus).toBe("has-local");
  });
  it("confirmed zero only with a healthy source and nothing unresolved", () => {
    expect(buildAlertsScreen(block([alert("9")]), [], NOW, false).localStatus).toBe("none-confirmed");
    expect(buildAlertsScreen(block([]), [], NOW, false).localStatus).toBe("none-confirmed");
  });
  it("unresolved alerts or a silent source or a failed refresh never read as all-clear", () => {
    const u = { ...alert("2"), geo_match: "unresolved" as const };
    expect(buildAlertsScreen(block([u]), [u], NOW, false).localStatus).toBe("unknown");
    const old = { freshness: "STALE" as const, last_success_at: "2026-10-01T00:00:00Z" };
    expect(buildAlertsScreen(block([], old), [], NOW, false).localStatus).toBe("unknown");
    expect(buildAlertsScreen(block([]), [], NOW, true).localStatus).toBe("unknown");
    // a source that aged past the bound on the device clock
    const aged = { freshness: "FRESH" as const, last_success_at: "2026-10-02T01:00:00Z" };
    expect(buildAlertsScreen(block([], aged), [], NOW, false).localStatus).toBe("unknown");
  });
  it("without local_alerts (older backend) only the national list, flagged as not located", () => {
    const m = buildAlertsScreen(block([alert("1")]), undefined, NOW, false);
    expect(m.located).toBe(false);
    expect(m.elsewhere).toHaveLength(1);
    expect(m.localStatus).toBe("unknown");
  });
});

describe("findAlert", () => {
  it("prefers the local copy, null when gone", () => {
    const n = alert("1");
    const l = { ...n, geo_match: "voivodeship" as const };
    expect(findAlert(alertKey(n), [l], [n])?.geo_match).toBe("voivodeship");
    expect(findAlert(alertKey(n), null, [n])?.geo_match).toBeNull();
    expect(findAlert("nope", [l], [n])).toBeNull();
    expect(findAlert(undefined, [l], [n])).toBeNull();
  });
});

describe("areaNames", () => {
  it("unique non-empty source names only", () => {
    expect(areaNames([{ wojewodztwo: "śląskie" }, { wojewodztwo: "śląskie" }, { wojewodztwo: " " }, { x: 1 }, null])).toEqual(["śląskie"]);
    expect(areaNames("x")).toEqual([]);
  });
});
