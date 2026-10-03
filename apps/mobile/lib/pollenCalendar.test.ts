import { describe, expect, it } from "vitest";

import {
  CALENDAR_COVERAGE_FALLBACK,
  CALENDAR_EMPTY_FALLBACK,
  type PollenCalendarBlock,
  type CalendarActiveLine,
  daysUntilText,
  formatAllergens,
  formatDay,
  formatRange,
  pollenCalendarView,
  seasonState,
  seasonSummary,
} from "./pollenCalendar";

const block = (over: Partial<PollenCalendarBlock> = {}): PollenCalendarBlock => ({
  date: "2026-03-10",
  kind: "seasonal_calendar",
  region: "PL",
  active: [
    {
      key: "hazel",
      name_pl: "leszczyna",
      category: "tree",
      phase: "start",
      peak: false,
      season_start: "2026-02-01",
      season_end: "2026-04-10",
      peak_start: "2026-03-01",
      peak_end: "2026-03-31",
      note: "n",
      source_ids: ["a"],
    },
  ],
  active_message: null,
  upcoming: [
    {
      key: "birch",
      name_pl: "brzoza",
      category: "tree",
      starts_on: "2026-04-01",
      days_until: 22,
      season_end: "2026-05-10",
      note: "n",
      source_ids: ["a"],
    },
  ],
  upcoming_within_days: 30,
  coverage_complete: false,
  coverage_warning: "Lista nie obejmuje wszystkich alergenów.",
  not_covered: [{ key: "ragweed", name_pl: "ambrozja", reason: "UNVERIFIED" }],
  sources: {},
  attribution: "Kalendarz: własne zestawienie",
  disclaimer: "Typowy przebieg sezonu, NIE pomiar i NIE prognoza.",
  reviewed_at: "2026-10-01",
  ...over,
});

describe("formatters", () => {
  it("formats days and ranges without Date (no timezone shift)", () => {
    expect(formatDay("2026-03-01")).toBe("1 mar");
    expect(formatDay("2026-12-31T00:00:00Z")).toBe("31 gru");
    expect(formatRange("2026-03-01", "2026-03-31")).toBe("1–31 mar");
    expect(formatRange("2026-02-01", "2026-04-10")).toBe("1 lut – 10 kwi");
    expect(formatRange("2026-03-05", "2026-03-05")).toBe("5 mar");
  });
  it("rejects garbage dates", () => {
    expect(formatDay("2026-13-01")).toBeNull();
    expect(formatDay("jutro")).toBeNull();
    expect(formatDay(undefined)).toBeNull();
    expect(formatRange("2026-03-01", null)).toBeNull();
  });
  it("says 'dziś' / 'jutro' / 'za N dni'", () => {
    expect(daysUntilText(0)).toBe("dziś");
    expect(daysUntilText(1)).toBe("jutro");
    expect(daysUntilText(2)).toBe("za 2 dni");
    expect(daysUntilText(30)).toBe("za 30 dni");
    expect(daysUntilText(-1)).toBeNull();
    expect(daysUntilText(1.5)).toBeNull();
    expect(daysUntilText("3")).toBeNull();
  });
});

describe("pollenCalendarView", () => {
  it("shows phase, season range, peak window before the peak and 'za N dni'", () => {
    const v = pollenCalendarView(block());
    expect(v?.active[0]).toMatchObject({
      name: "leszczyna",
      phase: "start",
      phaseText: "początek sezonu",
      range: "typowy sezon 1 lut – 10 kwi",
      peakRange: "szczyt 1–31 mar",
    });
    expect(v?.upcoming[0]).toEqual({
      key: "birch",
      name: "brzoza",
      text: "typowy start sezonu za 22 dni (1 kwi)",
    });
    expect(v?.notCovered).toBe("nie obejmuje: ambrozja");
    expect(v?.emptyMessage).toBeNull();
    expect(v?.kindNote).toContain("nie pomiar i nie prognoza");
    expect(v?.attribution).toBe("Kalendarz: własne zestawienie");
  });

  it("labels peak and end phases; no peak window after the start phase", () => {
    const a = block().active[0];
    const peak = pollenCalendarView(block({ active: [{ ...a, phase: "peak", peak: true }] }));
    const end = pollenCalendarView(block({ active: [{ ...a, phase: "end" }] }));
    expect(peak?.active[0]).toMatchObject({ phaseText: "szczyt sezonu", peakRange: null });
    expect(end?.active[0]).toMatchObject({ phaseText: "koniec sezonu", peakRange: null });
  });

  it("empty active is never 'nothing pollinates': server message, else the fallback", () => {
    const withMsg = pollenCalendarView(block({ active: [], active_message: "Brak ujętych, ale NIE znaczy..." }));
    expect(withMsg?.emptyMessage).toBe("Brak ujętych, ale NIE znaczy...");
    const without = pollenCalendarView(block({ active: [], active_message: null }));
    expect(without?.emptyMessage).toBe(CALENDAR_EMPTY_FALLBACK);
    expect(without?.coverageWarning).not.toBe("");
    expect(without?.disclaimer).not.toBe("");
  });

  it("a list with only unusable entries counts as empty (message shown)", () => {
    const v = pollenCalendarView({ ...block(), active: [{}, null, { name_pl: "" }] });
    expect(v?.active).toEqual([]);
    expect(v?.emptyMessage).toBe(CALENDAR_EMPTY_FALLBACK);
  });

  it("always carries coverage warning, disclaimer and attribution, even if the API omitted them", () => {
    const v = pollenCalendarView({ kind: "seasonal_calendar" });
    expect(v?.coverageWarning).toBe(CALENDAR_COVERAGE_FALLBACK);
    expect(v?.disclaimer).not.toBe("");
    expect(v?.attribution).not.toBe("");
    expect(v?.emptyMessage).toBe(CALENDAR_EMPTY_FALLBACK);
    expect(v?.upcoming).toEqual([]);
    expect(v?.notCovered).toBeNull();
  });

  it("is not a calendar for anything else (null, wrong kind, non-objects)", () => {
    for (const x of [null, undefined, 3, "x", [], {}, { kind: "model_forecast" }]) {
      expect(pollenCalendarView(x)).toBeNull();
    }
  });

  it("survives missing/unknown/odd fields", () => {
    const v = pollenCalendarView({
      kind: "seasonal_calendar",
      date: "nie-data",
      surprise: { x: 1 },
      active: [{ name_pl: "olsza", phase: "dziwna", season_start: 5 }],
      upcoming: [{ name_pl: "dąb", days_until: "x", starts_on: "?" }, "zly"],
      not_covered: [{ key: "k" }, { name_pl: "pokrzywowate" }],
    });
    expect(v?.date).toBeNull();
    expect(v?.active[0]).toMatchObject({
      name: "olsza",
      key: "olsza",
      phase: null,
      phaseText: "w typowym sezonie",
      range: null,
      peakRange: null,
    });
    expect(v?.upcoming).toEqual([{ key: "dąb", name: "dąb", text: "typowy start sezonu wkrótce" }]);
    expect(v?.notCovered).toBe("nie obejmuje: pokrzywowate");
  });

  it("boundary dates: season start day, end day, year-wrap upcoming", () => {
    const a = block().active[0];
    const first = pollenCalendarView(block({ date: "2026-02-01", active: [{ ...a, phase: "start" }] }));
    expect(first?.date).toBe("2026-02-01");
    expect(first?.active[0].range).toBe("typowy sezon 1 lut – 10 kwi");
    const wrap = pollenCalendarView(
      block({
        date: "2026-12-31",
        active: [],
        upcoming: [{ ...block().upcoming[0], starts_on: "2027-01-05", days_until: 5 }],
      }),
    );
    expect(wrap?.upcoming[0].text).toBe("typowy start sezonu za 5 dni (5 sty)");
  });
});

describe("season card (dashboard)", () => {
  const taxon = (name: string, phase: "start" | "peak" | "end" | null): PollenCalendarBlock["active"][number] => ({
    key: name,
    name_pl: name,
    category: "tree",
    phase: phase as "start" | "peak" | "end", // null = a payload without a phase (parsed defensively)
    peak: phase === "peak",
    season_start: "2026-02-01",
    season_end: "2026-04-10",
    peak_start: "2026-03-01",
    peak_end: "2026-03-31",
    note: "n",
    source_ids: ["a"],
  });
  const summary = (active: PollenCalendarBlock["active"], forecast: "low" | "elevated" | "unknown" = "unknown") => {
    const v = pollenCalendarView(block({ active }));
    if (!v) throw new Error("not a calendar");
    return seasonSummary(v, forecast);
  };
  const line = (phase: CalendarActiveLine["phase"]) => ({ phase }) as CalendarActiveLine;

  it("formats allergen lists", () => {
    expect(formatAllergens([])).toBe("");
    expect(formatAllergens(["brzoza"])).toBe("brzoza");
    expect(formatAllergens(["brzoza", "olsza"])).toBe("brzoza i olsza");
    expect(formatAllergens(["brzoza", "olsza", "trawy"])).toBe("brzoza, olsza i trawy");
    expect(formatAllergens(["a", "b", "c", "d"])).toBe("a, b, c i 1 inny");
    expect(formatAllergens(["a", "b", "c", "d", "e"])).toBe("a, b, c i 2 inne");
    expect(formatAllergens(["a", "b", "c", "d", "e", "f", "g", "h"])).toBe("a, b, c i 5 innych");
  });

  it("picks the headline: peak wins, one shared phase is named, a mix is 'season under way'", () => {
    expect(seasonState([])).toBe("out");
    expect(seasonState([line("end"), line("peak"), line("start")])).toBe("peak");
    expect(seasonState([line("start"), line("start")])).toBe("start");
    expect(seasonState([line("end"), line("end")])).toBe("end");
    expect(seasonState([line("end"), line("start")])).toBe("active"); // not "start of the season"
    expect(seasonState([line("end"), line(null), line("start")])).toBe("active");
    expect(seasonState([line(null)])).toBe("active");
  });

  it("A. outside the season: calm status, never 'nothing pollinates'", () => {
    const s = summary([]);
    expect(s).toMatchObject({ state: "out", title: "Poza sezonem pylenia", icon: "leaf-outline" });
    expect(s.text).toBe("Żaden z monitorowanych alergenów nie jest teraz w typowym okresie pylenia.");
    expect(s.context).toBe("Aktualna prognoza może nadal wskazywać obecność pyłków.");
  });

  it("A. outside the season but the forecast shows pollen: the card says so, not 'quiet'", () => {
    const s = summary([], "elevated");
    expect(s.context).toBe("Prognoza pokazuje jednak wyższe stężenia pyłków — sprawdź ją powyżej.");
    expect(s.text).not.toMatch(/nie pyli|nic nie/i);
  });

  it("B. start of the season names the starting allergens", () => {
    const s = summary([taxon("brzoza", "start"), taxon("olsza", "start")]);
    expect(s).toMatchObject({ state: "start", title: "Początek sezonu" });
    expect(s.text).toBe("Rozpoczyna się typowy okres pylenia: brzoza i olsza.");
    expect(s.context).toBe("Warto częściej sprawdzać aktualną prognozę.");
  });

  it("C. active season lists everything that is in season", () => {
    const s = summary([taxon("trawy", "end"), taxon("bylica", "start")]);
    expect(s).toMatchObject({ state: "active", title: "Trwa sezon pylenia" });
    expect(s.text).toBe("W typowym sezonie są teraz: trawy i bylica.");
    expect(s.context).toContain("pogoda może mocno zmieniać rzeczywiste pylenie");
  });

  it("D. peak names only the allergens at their peak", () => {
    const s = summary([taxon("leszczyna", "peak"), taxon("olsza", "start")]);
    expect(s).toMatchObject({ state: "peak", title: "Szczyt sezonu", icon: "trending-up" });
    expect(s.text).toBe("To typowo jeden z najbardziej intensywnych okresów pylenia: leszczyna.");
    expect(s.context).toBe("Aktualna prognoza pokaże, czy wysokie stężenia występują również dziś.");
    expect(summary([taxon("leszczyna", "peak")], "elevated").context).toBe("Prognoza potwierdza wyższe stężenia również dziś.");
  });

  it("E. end of the season", () => {
    const s = summary([taxon("brzoza", "end")]);
    expect(s).toMatchObject({ state: "end", title: "Sezon dobiega końca", icon: "trending-down" });
    expect(s.text).toBe("Typowy okres pylenia brzoza zbliża się do końca.");
    expect(s.context).toBe("Stężenia mogą nadal występować lokalnie.");
  });

  it("in season but the forecast is low: the context says the forecast is what counts today", () => {
    expect(summary([taxon("trawy", "end"), taxon("bylica", "start")], "low").context).toBe(
      "Prognoza na dziś jest jednak niska — pogoda mocno zmienia rzeczywiste pylenie.",
    );
  });

  it("the card copy has no shouting and no methodology", () => {
    for (const active of [[], [taxon("a", "start")], [taxon("a", null)], [taxon("a", "peak")], [taxon("a", "end")]]) {
      for (const forecast of ["low", "elevated", "unknown"] as const) {
        const s = summary(active, forecast);
        const all = `${s.title} ${s.text} ${s.context}`;
        expect(all).not.toMatch(/\bNIE\b|dekad|takson|nie obejmuje|ambrozj|pokrzywowat/);
      }
    }
  });

  it("the details keep everything the card dropped (coverage, disclaimer, 'not covered', source)", () => {
    const v = pollenCalendarView(block({ active: [] }));
    expect(v?.notCovered).toBe("nie obejmuje: ambrozja");
    expect(v?.coverageWarning).not.toBe("");
    expect(v?.disclaimer).not.toBe("");
    expect(v?.attribution).not.toBe("");
    expect(v?.emptyMessage).not.toBeNull();
  });
});
