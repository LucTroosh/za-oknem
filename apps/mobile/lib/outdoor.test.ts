import { describe, expect, it } from "vitest";

import {
  OUTDOOR_LEVEL_LABEL,
  OUTDOOR_FALLBACK_MAX_AGE_MS,
  type OutdoorBlock,
  type OutdoorReason,
  missingList,
  outdoorView,
  reasonLine,
} from "./outdoor";

const NOW = Date.parse("2026-09-30T12:00:00Z");

const reason = (over: Partial<OutdoorReason> = {}): OutdoorReason => ({
  code: "PRECIPITATION",
  param: "precipitation",
  value: 3,
  threshold: 2.5,
  comparison: "gte",
  unit: "mm",
  level: "POOR",
  ...over,
});

const block = (over: Partial<OutdoorBlock> = {}): OutdoorBlock => ({
  level: "GOOD",
  reasons: [],
  missing: [],
  ...over,
});

describe("reasonLine", () => {
  it("formats value, comparison and threshold straight from the data", () => {
    expect(reasonLine(reason())).toBe("opady: 3 mm (próg ≥ 2,5 mm)");
    expect(
      reasonLine(reason({ param: "visibility", value: 800, threshold: 1000, comparison: "lt", unit: "m" })),
    ).toBe("widzialność: 800 m (próg < 1000 m)");
    expect(
      reasonLine(reason({ param: "pm25", value: 15.3, threshold: 15, comparison: "gt", unit: "µg/m³" })),
    ).toBe("PM2.5: 15,3 µg/m³ (próg > 15 µg/m³)");
    expect(
      reasonLine(reason({ param: "apparent_temperature", value: -2, threshold: 0, comparison: "lte", unit: "°C" })),
    ).toBe("temperatura odczuwalna: -2 °C (próg ≤ 0 °C)");
  });

  it("omits an empty unit (UV index) and keeps an unknown param code", () => {
    expect(reasonLine(reason({ param: "uv_index", value: 6.5, threshold: 6, unit: "" }))).toBe(
      "indeks UV: 6,5 (próg ≥ 6)",
    );
    expect(reasonLine(reason({ param: "snow_depth" }))).toContain("snow_depth:");
  });

  it("shows ? for a non-numeric value instead of throwing", () => {
    expect(reasonLine(reason({ value: null as unknown as number }))).toContain("?");
  });
});

describe("missingList", () => {
  it("names the factor for a blocking gap and only the absent param for a non-blocking one", () => {
    expect(
      missingList([
        { group: "wind", params: ["wind_speed_10m"], status: "STALE", core: true, blocking: true },
        { group: "air", params: ["pm10"], status: "MISSING", core: true, blocking: false },
      ]),
    ).toBe("wiatr (nieaktualne), PM10 (brak)");
  });

  it("labels the optional NO2/O3/storm groups", () => {
    expect(
      missingList([
        { group: "no2", params: ["no2"], status: "MISSING", core: false, blocking: true },
        { group: "storm", params: ["weather_code"], status: "STALE", core: false, blocking: true },
      ]),
    ).toBe("NO₂ (brak), burza (nieaktualne)");
  });

  it("tolerates garbage", () => {
    expect(missingList(undefined)).toBe("");
    expect(missingList([null, 3])).toBe("");
  });
});

describe("outdoorView", () => {
  it("returns null when the backend has no outdoor field (older backend)", () => {
    expect(outdoorView(undefined, NOW, NOW)).toBeNull();
    expect(outdoorView(null, NOW, NOW)).toBeNull();
    expect(outdoorView("GOOD", NOW, NOW)).toBeNull();
  });

  it("GOOD: label, icon, nothing else when nothing is missing", () => {
    expect(outdoorView(block(), NOW, NOW)).toEqual({
      level: "GOOD",
      icon: "✓",
      headline: OUTDOOR_LEVEL_LABEL.GOOD,
      reasonLines: [],
      missingLine: null,
    });
  });

  it("MODERATE/POOR list reasons in the backend's order with a text label and icon", () => {
    const v = outdoorView(
      block({
        level: "POOR",
        reasons: [reason(), reason({ code: "WIND_STRONG", param: "wind_speed_10m", value: 30, threshold: 29, unit: "km/h", level: "MODERATE" })],
      }),
      NOW,
      NOW,
    );
    expect(v?.headline).toBe("Złe warunki");
    expect(v?.icon).toBe("✕");
    expect(v?.reasonLines).toEqual(["opady: 3 mm (próg ≥ 2,5 mm)", "wiatr: 30 km/h (próg ≥ 29 km/h)"]);
    expect(outdoorView(block({ level: "MODERATE" }), NOW, NOW)?.icon).toBe("!");
  });

  it("a bad verdict with gaps still says what was not taken into account", () => {
    const v = outdoorView(
      block({
        level: "MODERATE",
        reasons: [reason({ level: "MODERATE" })],
        missing: [{ group: "uv", params: ["uv_index"], status: "MISSING", core: false, blocking: true }],
      }),
      NOW,
      NOW,
    );
    expect(v?.missingLine).toBe("Nie uwzględniono — brak danych: indeks UV (brak)");
  });

  it("UNKNOWN is shown honestly with the missing inputs, never as a verdict", () => {
    const v = outdoorView(
      block({
        level: "UNKNOWN",
        missing: [
          { group: "wind", params: ["wind_speed_10m"], status: "STALE", core: true, blocking: true },
          { group: "air", params: ["pm10", "pm25"], status: "MISSING", core: true, blocking: true },
        ],
      }),
      NOW,
      NOW,
    );
    expect(v?.level).toBe("UNKNOWN");
    expect(v?.icon).toBe("?");
    expect(v?.headline).toBe("Brak oceny — brak danych: wiatr (nieaktualne), jakość powietrza (brak)");
  });

  it("UNKNOWN without a missing list still does not pretend", () => {
    expect(outdoorView(block({ level: "UNKNOWN" }), NOW, NOW)?.headline).toBe("Brak oceny — brak danych");
  });

  it("an unrecognised level degrades to UNKNOWN, not to a good verdict", () => {
    expect(outdoorView({ level: "EXCELLENT", reasons: [], missing: [] }, NOW, NOW)?.level).toBe("UNKNOWN");
    expect(outdoorView({}, NOW, NOW)?.level).toBe("UNKNOWN");
  });

  it("survives malformed reasons/missing", () => {
    const v = outdoorView({ level: "MODERATE", reasons: "x", missing: 5 }, NOW, NOW);
    expect(v?.reasonLines).toEqual([]);
    expect(v?.missingLine).toBeNull();
  });

  it("stops asserting a verdict once its earliest input expired (valid_until), not a fixed hour after receipt", () => {
    const validUntil = new Date(NOW + 10 * 60_000).toISOString(); // input turns STALE in 10 min
    const b = block({ level: "POOR", reasons: [reason()], valid_until: validUntil });
    expect(outdoorView(b, NOW + 10 * 60_000, NOW)?.level).toBe("POOR");
    const old = outdoorView(b, NOW + 10 * 60_000 + 1, NOW);
    expect(old?.level).toBe("UNKNOWN");
    expect(old?.reasonLines).toEqual([]);
    expect(old?.headline).toContain("Brak oceny");
  });

  it("a long valid_until is not cut short by the fallback age", () => {
    const b = block({ valid_until: new Date(NOW + 5 * 3600_000).toISOString() });
    expect(outdoorView(b, NOW + 2 * 3600_000, NOW)?.level).toBe("GOOD");
  });

  it("without a usable valid_until falls back to the response age", () => {
    for (const valid_until of [undefined, null, "not-a-date"]) {
      const b = { ...block(), valid_until } as OutdoorBlock;
      expect(outdoorView(b, NOW + OUTDOOR_FALLBACK_MAX_AGE_MS, NOW)?.level).toBe("GOOD");
      expect(outdoorView(b, NOW + OUTDOOR_FALLBACK_MAX_AGE_MS + 1, NOW)?.level).toBe("UNKNOWN");
    }
  });
});
