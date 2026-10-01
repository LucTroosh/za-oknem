import { describe, expect, it } from "vitest";

import { homeAlertsBanner, homeHydroBanner } from "./alertsBanner";
import type { HydroSummary } from "./hydro";

describe("homeAlertsBanner", () => {
  it("is silent only for a confirmed all-clear", () => {
    expect(homeAlertsBanner({ kind: "none-confirmed", sources: ["x"] }, 0)).toBeNull();
  });
  it("a missing block is a neutral 'niedostępne', never silence", () => {
    const b = homeAlertsBanner(null, 0);
    expect(b?.tone).toBe("neutral");
    expect(b?.text).toContain("sprawdzić");
  });
  it("never claims an all-clear when the source is silent", () => {
    const b = homeAlertsBanner({ kind: "unavailable", lastSuccessAt: null }, 0);
    expect(b?.tone).toBe("neutral");
    expect(b?.text).toContain("sprawdzić");
  });
  it("counts a healthy list and caveats an old one", () => {
    expect(homeAlertsBanner({ kind: "list" }, 3)?.text).toContain("3");
    expect(homeAlertsBanner({ kind: "list-maybe-outdated", lastSuccessAt: null }, 3)?.text).toContain("nieaktualna");
  });
});

const st = (status: "ALARM" | "WARNING", freshness: "FRESH" | "RECENT" | "STALE" | "UNAVAILABLE") =>
  ({ station: { status }, freshness }) as unknown as Extract<HydroSummary, { kind: "list" }>["items"][number];
const list = (items: ReturnType<typeof st>[], outdated = false): HydroSummary => ({
  kind: "list",
  items,
  more: 0,
  outdated,
  lastSuccessAt: null,
});

describe("homeHydroBanner", () => {
  it("alarm wins over warning and counts current stations only", () => {
    const b = homeHydroBanner(list([st("ALARM", "FRESH"), st("ALARM", "STALE"), st("WARNING", "RECENT")]));
    expect(b?.tone).toBe("danger");
    expect(b?.text).toContain("1");
  });
  it("warning only", () => {
    expect(homeHydroBanner(list([st("WARNING", "FRESH"), st("WARNING", "RECENT")]))?.tone).toBe("warning");
  });
  it("calm only when confirmed none", () => {
    expect(homeHydroBanner({ kind: "none-confirmed", unassessed: 0 })).toBeNull();
  });
  it("unavailable or missing data is neutral, not calm", () => {
    expect(homeHydroBanner({ kind: "unavailable", lastSuccessAt: null })?.tone).toBe("neutral");
    expect(homeHydroBanner(null)?.tone).toBe("neutral");
  });
  it("a list with only STALE/UNAVAILABLE stations or an outdated source is neutral", () => {
    expect(homeHydroBanner(list([st("ALARM", "STALE"), st("WARNING", "UNAVAILABLE")]))?.tone).toBe("neutral");
    expect(homeHydroBanner(list([st("ALARM", "FRESH")], true))?.tone).toBe("neutral");
  });
});
