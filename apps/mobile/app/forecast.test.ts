import { describe, expect, it } from "vitest";

import { forecastDayLabel, forecastLine } from "./forecast";

const day = (params: Record<string, { value: number; unit: string }>) => ({
  valid_from: "2026-09-30T00:00:00+00:00", // a Wednesday
  valid_until: "2026-10-01T00:00:00+00:00",
  params,
});

describe("forecastDayLabel", () => {
  it("formats weekday with rounded max/min", () => {
    const label = forecastDayLabel(
      day({
        temperature_2m_max: { value: 18.5, unit: "°C" },
        temperature_2m_min: { value: 9.2, unit: "°C" },
      }),
    );
    expect(label).toMatch(/^śr\.? 19°\/9°$/);
  });

  it("returns null when max or min is missing instead of inventing a value", () => {
    expect(forecastDayLabel(day({ temperature_2m_max: { value: 18, unit: "°C" } }))).toBeNull();
  });
});

describe("forecastLine", () => {
  it("is null when no day has both max and min", () => {
    expect(forecastLine([day({ temperature_2m_max: { value: 18, unit: "°C" } })])).toBeNull();
  });

  it("limits to the first 3 days", () => {
    const d = day({
      temperature_2m_max: { value: 18, unit: "°C" },
      temperature_2m_min: { value: 9, unit: "°C" },
    });
    expect(forecastLine([d, d, d, d])?.split("   ")).toHaveLength(3);
  });
});
