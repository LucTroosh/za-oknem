import { describe, expect, it } from "vitest";

import { collectAttributions, withPlaceSource } from "./sources";

describe("collectAttributions", () => {
  it("collects unique attributions in first-seen order, verbatim", () => {
    const dash = {
      alerts: { attribution: "IMGW" },
      areas: [
        { air: { attribution: "GIOŚ" }, weather: { attribution: "Open-Meteo" }, forecast: { attribution: "Open-Meteo" }, pollen: { attribution: "CAMS" } },
        { air: null, weather: { attribution: "Open-Meteo" }, forecast: null, pollen: { attribution: "CAMS" } },
      ],
    };
    expect(collectAttributions(dash)).toEqual(["IMGW", "GIOŚ", "Open-Meteo", "CAMS"]);
  });

  it("adds extra blocks (hydro, pollen calendar) and works without a dashboard", () => {
    expect(collectAttributions(null, { attribution: "IMGW hydro" }, null, { attribution: "Kalendarz" })).toEqual([
      "IMGW hydro",
      "Kalendarz",
    ]);
    expect(collectAttributions({ alerts: { attribution: "IMGW" } }, { attribution: "IMGW" })).toEqual(["IMGW"]);
  });

  it("ignores garbage and empty strings instead of throwing", () => {
    expect(collectAttributions(null)).toEqual([]);
    expect(collectAttributions({ alerts: { attribution: "  " }, areas: [null, 3, { air: { attribution: 5 } }] })).toEqual([]);
    expect(collectAttributions({ areas: "x" })).toEqual([]);
  });
});

describe("withPlaceSource", () => {
  it("appends the GeoNames attribution verbatim, once", () => {
    expect(withPlaceSource(["IMGW"], "GeoNames (CC BY 4.0)")).toEqual(["IMGW", "GeoNames (CC BY 4.0)"]);
    expect(withPlaceSource(["GeoNames (CC BY 4.0)"], "GeoNames (CC BY 4.0)")).toEqual(["GeoNames (CC BY 4.0)"]);
  });
  it("nothing to add for seeded cities / old records", () => {
    const list = ["IMGW"];
    expect(withPlaceSource(list, null)).toBe(list);
    expect(withPlaceSource(list, undefined)).toBe(list);
    expect(withPlaceSource(list, " ")).toBe(list);
  });
});
