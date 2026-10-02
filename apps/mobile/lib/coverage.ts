// How honestly the air card describes WHERE the measurement comes from (ADR-029 §5, rule #8/#9).
// The backend decides the band (`coverage`); this only words it. Weather and pollen are model
// values on a grid, never a measurement in the town - the backend's own description is shown.
import type { DashboardCoverage } from "../../../packages/api-contract/schema";

export const NO_STATION_HEADLINE = "Brak stacji pomiarowej w okolicy";
export const GRID_FALLBACK = "Pogoda i pyłki to wartości z modelu dla tego obszaru, nie pomiar w miejscowości.";

export const MODEL_NOTE = "Wartość z modelu dla obszaru, nie pomiar w miejscowości.";

// `headline`: regional only - a distant station is an orientation, never a verdict about "here".
export type AirCoverage = { band: DashboardCoverage["air"] | null; note: string | null; unavailable: boolean; headline?: string };

const isObject = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);

// 3,0 -> "3", 12,34 -> "12,3": distance as the backend rounded it (0.1 km).
function km(v: unknown): string | null {
  if (typeof v !== "number" || !Number.isFinite(v)) return null;
  return String(Math.round(v * 10) / 10).replace(".", ",");
}

// exact -> no note; nearby -> station + distance; regional -> explicit "area state"; none ->
// UNAVAILABLE (never "good"). Unknown band (older backend) -> no claim, no note.
export function airCoverage(coverage: unknown, air: unknown): AirCoverage {
  const fromArea = isObject(coverage) ? coverage.air : undefined;
  const band = fromArea ?? (isObject(air) ? air.coverage : undefined);
  const station = isObject(air) && typeof air.station_name === "string" && air.station_name !== "" ? air.station_name : null;
  const dist = isObject(air) ? km(air.distance_km) : null;
  const where = station ? `stacja ${station}${dist ? `, ${dist} km` : ""}` : "stacja w okolicy";
  switch (band) {
    case "exact":
      return { band, note: null, unavailable: false };
    case "nearby":
      return {
        band,
        note: station ? `Dane ze stacji ${station}${dist ? `, ${dist} km stąd` : ""}.` : "Dane ze stacji w okolicy.",
        unavailable: false,
      };
    case "regional": {
      const r = isObject(coverage) && typeof coverage.air_radius_km === "number" ? coverage.air_radius_km : 100;
      return {
        band,
        note: `Stan dla obszaru w promieniu ok. ${r} km — ${where}.`,
        unavailable: false,
        headline: station ? `Stacja ${station}${dist ? `, ${dist} km` : ""}` : "Stacja w okolicy",
      };
    }
    case "none":
      return { band, note: NO_STATION_HEADLINE, unavailable: true };
    default:
      return { band: null, note: null, unavailable: false };
  }
}

export function gridDescription(coverage: unknown): string {
  const d = isObject(coverage) ? coverage.grid_description : undefined;
  return typeof d === "string" && d.trim() !== "" ? d : GRID_FALLBACK;
}
