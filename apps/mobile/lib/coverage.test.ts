import { describe, expect, it } from "vitest";

import { GRID_FALLBACK, NO_STATION_HEADLINE, airCoverage, gridDescription, showAirIndex } from "./coverage";

const air = { station_name: "Zabrze", distance_km: 12, coverage: "nearby" };

describe("airCoverage", () => {
  it("exact says nothing", () => {
    expect(airCoverage({ air: "exact" }, air)).toEqual({ band: "exact", note: null, unavailable: false });
  });
  it("nearby names the station and the distance", () => {
    expect(airCoverage({ air: "nearby" }, air).note).toBe("Dane ze stacji Zabrze, 12 km stąd.");
  });
  it("regional uses the backend radius and the same station", () => {
    expect(airCoverage({ air: "regional", air_radius_km: 100 }, { ...air, distance_km: 80.25 }).note).toBe(
      "Stan dla obszaru w promieniu ok. 100 km — stacja Zabrze, 80,3 km.",
    );
  });
  it("none is unavailable", () => {
    expect(airCoverage({ air: "none" }, null)).toEqual({ band: "none", note: NO_STATION_HEADLINE, unavailable: true });
  });
  it("falls back to the air block's band, then to no claim", () => {
    expect(airCoverage(undefined, air).band).toBe("nearby");
    expect(airCoverage(undefined, null)).toEqual({ band: null, note: null, unavailable: false });
  });
  it("a missing station name does not invent one", () => {
    expect(airCoverage({ air: "nearby" }, { coverage: "nearby" }).note).toBe("Dane ze stacji w okolicy.");
    expect(airCoverage({ air: "regional" }, {}).note).toBe("Stan dla obszaru w promieniu ok. 100 km — stacja w okolicy.");
  });
});

describe("gridDescription", () => {
  it("shows the backend text verbatim, else a safe fallback", () => {
    expect(gridDescription({ grid_description: "Model Open-Meteo, siatka ~11 km." })).toBe("Model Open-Meteo, siatka ~11 km.");
    expect(gridDescription({ grid_description: " " })).toBe(GRID_FALLBACK);
    expect(gridDescription(undefined)).toBe(GRID_FALLBACK);
  });
});

describe("showAirIndex (details badge)", () => {
  it("only for exact / nearby / unknown-band stations, never regional or none", () => {
    expect(showAirIndex({ air: "exact" }, air)).toBe(true);
    expect(showAirIndex({ air: "nearby" }, air)).toBe(true);
    expect(showAirIndex(undefined, null)).toBe(true);
    expect(showAirIndex({ air: "regional" }, air)).toBe(false);
    expect(showAirIndex({ air: "none" }, null)).toBe(false);
  });
});
