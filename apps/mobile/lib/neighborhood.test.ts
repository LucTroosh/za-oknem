import { describe, expect, it } from "vitest";

import { DEGRADED_NOTICE, type NeighborhoodBlock, distanceText, entryVisible, formatDay, neighborhoodView, periodText, sectionView } from "./neighborhood";

type S = NeighborhoodBlock["sections"][number];
const section = (over: Partial<S> = {}): S => ({
  id: "noise",
  data_kind: "historical_measurement",
  title: "Hałas",
  availability: "available",
  retrieval_status: "ok",
  message: null,
  source_period: { from: "2024-05-10", to: "2024-11-10", precision: "date" },
  fetched_at: "2026-10-03T08:00:00Z",
  attribution: "Źródło danych: GIOŚ · CC BY 4.0. Dane zostały uporządkowane i przetworzone przez Za Oknem.",
  source_url: "https://dane.gios.gov.pl",
  license_url: "https://creativecommons.org/licenses/by/4.0/",
  limitations: ["Dane historyczne z pomiarów w wybranych punktach — nie opisują hałasu teraz."],
  search_radius_km: 10,
  items: [
    {
      category: "Droga",
      point_code: "D_1",
      locality: "Żyglin",
      gmina: "Miasteczko Śląskie",
      voivodeship: "ŚLĄSKIE",
      distance_km: 2.34,
      period_from: "2024-05-10",
      period_to: "2024-11-10",
      purpose: "Państwowy monitoring środowiska",
      measurements: [
        { period_of_day: "Dzień 16h", value_db: 64.5, exceedance_db: 0 },
        { period_of_day: "Noc 8h", value_db: 55, exceedance_db: 2.5 },
      ],
    },
  ],
  ...over,
});
const block = (sections: S[], enabled = true): NeighborhoodBlock => ({ geo_area_id: 1, area_name: "Gliwice", enabled, sections });

describe("entry", () => {
  it("is shown only when the server reports a switched-on section", () => {
    expect(entryVisible(block([section()]))).toBe(true);
    expect(entryVisible(block([], false))).toBe(false);
    expect(entryVisible(block([], true))).toBe(false);
    expect(entryVisible(null)).toBe(false);
  });
  it("tolerates a backend without the module or with a broken body", () => {
    expect(neighborhoodView(null)).toBeNull();
    expect(neighborhoodView({ detail: "Not Found" })).toBeNull();
    expect(neighborhoodView({ enabled: "yes", sections: [] })).toBeNull();
    expect(neighborhoodView(block([section()]))).not.toBeNull();
  });
});

describe("period and distance wording", () => {
  it("formats plain calendar days without a timezone shift", () => {
    expect(formatDay("2024-05-10")).toBe("10.05.2024");
    expect(periodText({ from: "2024-05-10", to: "2024-11-10", precision: "date" })).toBe("10.05.2024 – 10.11.2024");
    expect(periodText({ from: "2024-05-10", to: "2024-05-10", precision: "date" })).toBe("10.05.2024");
    expect(periodText({ from: "2023-01-01", to: "2024-12-31", precision: "year" })).toBe("2023–2024");
    expect(periodText({ from: "2024-01-01", to: "2024-12-31", precision: "year" })).toBe("2024");
  });
  it("says nothing when the source gives no period", () => {
    expect(periodText({ from: "2024-01-01", to: "2024-01-01", precision: "unknown" })).toBeNull();
    expect(periodText(null)).toBeNull();
  });
  it("uses a decimal comma and never claims a precise place", () => {
    expect(distanceText(2.34)).toBe("ok. 2,3 km od wybranej lokalizacji");
    expect(distanceText(0.02)).toBe("w tym samym miejscu");
  });
});

describe("sectionView", () => {
  it("shows measurements with the source's period labels and a comma", () => {
    const v = sectionView(section());
    expect(v.kind).toBe("data");
    expect(v.period).toBe("10.05.2024 – 10.11.2024");
    const [item] = v.items;
    expect(item.title).toBe("Hałas drogowy");
    expect(item.place).toBe("Żyglin, Miasteczko Śląskie");
    expect(item.rows.map((r) => [r.label, r.value])).toEqual([["Dzień 16h", "64,5 dB"], ["Noc 8h", "55,0 dB"]]);
    expect(v.attribution).toContain("CC BY 4.0");
  });
  it("mentions the exceedance only when the source reports a positive one, never as 'within the norm'", () => {
    const rows = sectionView(section()).items[0].rows;
    expect(rows[0].note).toBeNull(); // 0 -> no claim either way
    expect(rows[1].note).toBe("przekroczenie wg źródła: 2,5 dB");
    const none = sectionView(section({ items: [{ ...section().items[0], measurements: [{ period_of_day: "Dzień 16h", value_db: 50, exceedance_db: null }] }] }));
    expect(none.items[0].rows[0].note).toBeNull();
  });
  it("tells 'no point nearby' (empty) from 'could not read' (failed) and never mixes them", () => {
    const empty = sectionView(section({ availability: "no_coverage", items: [], source_period: null, message: "Brak punktów pomiaru hałasu w promieniu 10 km od wybranej lokalizacji." }));
    expect(empty.kind).toBe("empty");
    expect(empty.headline).toBe("W pobliżu nie ma punktu pomiarowego");
    expect(empty.body).toContain("10 km");
    const failed = sectionView(section({ availability: "unavailable", items: [], source_period: null, retrieval_status: "none", message: "Nie udało się odczytać danych o hałasie." }));
    expect(failed.kind).toBe("failed");
    expect(failed.headline).toBe("Dane chwilowo niedostępne");
    expect(failed.headline).not.toMatch(/brak|nie ma/i);
  });
  it("keeps showing old data but says the latest fetch failed; the period stays the source's", () => {
    const v = sectionView(section({ retrieval_status: "degraded" }));
    expect(v.kind).toBe("data");
    expect(v.retrievalNotice).toBe(DEGRADED_NOTICE);
    expect(v.period).toBe("10.05.2024 – 10.11.2024"); // never "now"
    expect(sectionView(section()).retrievalNotice).toBeNull();
  });
  it("treats 'available' without items as empty rather than rendering a blank card", () => {
    expect(sectionView(section({ items: [] })).kind).toBe("empty");
  });
  it("has no live-data or advice wording", () => {
    const text = JSON.stringify(sectionView(section()));
    expect(text).not.toMatch(/aktualn|na żywo|świeże|zostań|unikaj|bezpiecz|norma/i);
  });
});
