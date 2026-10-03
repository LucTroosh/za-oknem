// TASK-8.10 (UI) / ADR-023: presentation of `GET /api/v1/pollen/calendar`.
// This is a TYPICAL SEASON from a static reference table - NOT a measurement and NOT a
// forecast (rule #7). Every view says so, always carries the server's coverage warning
// and disclaimer, and an empty `active` list is never rendered as "nothing pollinates"
// ("brak wpisu" != "nie pyli"). Parsing is defensive: missing/odd fields degrade, never throw.

import type { PollenCalendarOut } from "../../../packages/api-contract/schema";

// The contract of the endpoint (generated); the view below accepts `unknown`.
export type PollenCalendarBlock = PollenCalendarOut;

export const CALENDAR_TITLE = "Kalendarz sezonów"; // the detail screen; the dashboard card sits under "Typowy sezon"
export const CALENDAR_KIND_NOTE = "Typowy sezon, nie pomiar i nie prognoza.";
// Local fallbacks only for an API that omitted the server text; same wording as the backend.
export const CALENDAR_COVERAGE_FALLBACK =
  "Lista nie obejmuje wszystkich alergenów; brak wpisu NIE oznacza braku pylenia.";
export const CALENDAR_EMPTY_FALLBACK =
  "Żaden z ujętych alergenów nie jest teraz w typowym sezonie. To nie znaczy, że nic nie pyli: kalendarz nie obejmuje wszystkich alergenów, a rzeczywiste pylenie zależy od pogody.";
export const CALENDAR_DISCLAIMER_FALLBACK =
  "Typowy przebieg sezonu, NIE pomiar i NIE prognoza. Rzeczywisty termin zależy od pogody, roku i regionu.";
export const CALENDAR_ATTRIBUTION_FALLBACK = "Źródło: kalendarz własny Za Oknem (dane referencyjne).";

export const PHASE_LABEL: Record<string, string> = {
  start: "początek sezonu",
  peak: "szczyt sezonu",
  end: "koniec sezonu",
};

export type CalendarActiveLine = {
  key: string;
  name: string;
  phase: "start" | "peak" | "end" | null;
  phaseText: string;
  range: string | null; // "typowy sezon 1 lut – 1 kwi"
  peakRange: string | null; // only before the peak: "szczyt 1–31 mar"
};

export type CalendarUpcomingLine = { key: string; name: string; text: string };

export type CalendarView = {
  title: string;
  kindNote: string;
  date: string | null; // ISO day the calendar was computed for, "na dzień ..." in the UI
  active: CalendarActiveLine[];
  // Shown whenever `active` is empty (server's `active_message`, else our fallback).
  emptyMessage: string | null;
  upcoming: CalendarUpcomingLine[];
  notCovered: string | null; // "nie obejmuje: ambrozja, pokrzywowate"
  coverageWarning: string;
  disclaimer: string;
  attribution: string;
};

const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

const nonEmpty = (x: unknown): x is string => typeof x === "string" && x.trim() !== "";

const MONTHS = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"];

// "2026-03-01" -> {d:1, m:3}; null for anything else (no Date: no timezone shifts, no "Invalid Date").
function parseDay(iso: unknown): { d: number; m: number } | null {
  if (typeof iso !== "string") return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!match) return null;
  const m = Number(match[2]);
  const d = Number(match[3]);
  return m >= 1 && m <= 12 && d >= 1 && d <= 31 ? { d, m } : null;
}

export function formatDay(iso: unknown): string | null {
  const p = parseDay(iso);
  return p ? `${p.d} ${MONTHS[p.m - 1]}` : null;
}

// "1 lut – 1 kwi"; "1–31 mar" inside one month; null if either end is unusable.
export function formatRange(from: unknown, to: unknown): string | null {
  const a = parseDay(from);
  const b = parseDay(to);
  if (!a || !b) return null;
  if (a.m === b.m) {
    return a.d === b.d ? `${a.d} ${MONTHS[a.m - 1]}` : `${a.d}–${b.d} ${MONTHS[a.m - 1]}`;
  }
  return `${a.d} ${MONTHS[a.m - 1]} – ${b.d} ${MONTHS[b.m - 1]}`;
}

export function daysUntilText(n: unknown): string | null {
  if (typeof n !== "number" || !Number.isInteger(n) || n < 0) return null;
  return n === 0 ? "dziś" : n === 1 ? "jutro" : `za ${n} dni`;
}

function activeLine(raw: unknown): CalendarActiveLine | null {
  if (!isObject(raw) || !nonEmpty(raw.name_pl)) return null;
  const phase = raw.phase === "start" || raw.phase === "peak" || raw.phase === "end" ? raw.phase : null;
  const range = formatRange(raw.season_start, raw.season_end);
  const peakRange = phase === "start" ? formatRange(raw.peak_start, raw.peak_end) : null;
  return {
    key: nonEmpty(raw.key) ? raw.key : raw.name_pl,
    name: raw.name_pl,
    phase,
    phaseText: phase ? PHASE_LABEL[phase] : "w typowym sezonie",
    range: range && `typowy sezon ${range}`,
    peakRange: peakRange && `szczyt ${peakRange}`,
  };
}

function upcomingLine(raw: unknown): CalendarUpcomingLine | null {
  if (!isObject(raw) || !nonEmpty(raw.name_pl)) return null;
  const when = daysUntilText(raw.days_until);
  const start = formatDay(raw.starts_on);
  const text = when
    ? `typowy start sezonu ${when}${start ? ` (${start})` : ""}`
    : start
      ? `typowy start sezonu ${start}`
      : "typowy start sezonu wkrótce";
  return { key: nonEmpty(raw.key) ? raw.key : raw.name_pl, name: raw.name_pl, text };
}

function mapList<T>(raw: unknown, f: (x: unknown) => T | null): T[] {
  return Array.isArray(raw) ? raw.map(f).filter((x): x is T => x !== null) : [];
}

// null = not a seasonal-calendar payload at all (unknown `kind` must never be labelled as
// a calendar); the card then renders nothing.
export function pollenCalendarView(block: unknown): CalendarView | null {
  if (!isObject(block) || block.kind !== "seasonal_calendar") return null;
  const active = mapList(block.active, activeLine);
  const names = mapList(block.not_covered, (x) =>
    isObject(x) && nonEmpty(x.name_pl) ? x.name_pl : null,
  );
  return {
    title: CALENDAR_TITLE,
    kindNote: CALENDAR_KIND_NOTE,
    date: parseDay(block.date) ? (block.date as string) : null,
    active,
    emptyMessage:
      active.length > 0
        ? null
        : nonEmpty(block.active_message)
          ? block.active_message
          : CALENDAR_EMPTY_FALLBACK,
    upcoming: mapList(block.upcoming, upcomingLine),
    notCovered: names.length > 0 ? `nie obejmuje: ${names.join(", ")}` : null,
    coverageWarning: nonEmpty(block.coverage_warning)
      ? block.coverage_warning
      : CALENDAR_COVERAGE_FALLBACK,
    disclaimer: nonEmpty(block.disclaimer) ? block.disclaimer : CALENDAR_DISCLAIMER_FALLBACK,
    attribution: nonEmpty(block.attribution) ? block.attribution : CALENDAR_ATTRIBUTION_FALLBACK,
  };
}

// ---- the dashboard card: one status, one sentence of context ----------------------------------
// The calendar is background for the CURRENT FORECAST, never a replacement for it (rule #7): an
// empty `active` list is "outside the typical season" - the wording never says nothing pollinates,
// and when today's forecast shows pollen the card says so (`ForecastLevel`) instead of the calendar.
// Everything technical (ranges, coverage, method, sources) lives on the detail screen.

export type SeasonState = "out" | "start" | "active" | "peak" | "end";
// What today's CAMS forecast says, from the pollen status model (lib/home.ts); "unknown" = no
// usable forecast (unavailable / stale / no data): then the calendar makes no claim about it.
export type ForecastLevel = "low" | "elevated" | "unknown";
// Ionicons glyph names (a status is never carried by colour alone: icon + the title text).
export type SeasonIcon = "leaf-outline" | "flower-outline" | "flower" | "trending-up" | "trending-down";

export type SeasonSummary = {
  state: SeasonState;
  icon: SeasonIcon;
  title: string;
  text: string;
  context: string;
};

const SEASON_TITLE: Record<SeasonState, string> = {
  out: "Poza sezonem pylenia",
  start: "Początek sezonu",
  active: "Trwa sezon pylenia",
  peak: "Szczyt sezonu",
  end: "Sezon dobiega końca",
};
const SEASON_ICON: Record<SeasonState, SeasonIcon> = {
  out: "leaf-outline",
  start: "flower-outline",
  active: "flower",
  peak: "trending-up",
  end: "trending-down",
};

// "brzoza", "brzoza i olsza", "brzoza, olsza i trawy", "brzoza, olsza, trawy i 2 inne".
export function formatAllergens(names: string[]): string {
  const list = names.filter((n) => n.trim() !== "");
  if (list.length <= 1) return list.join("");
  if (list.length <= 3) return `${list.slice(0, -1).join(", ")} i ${list[list.length - 1]}`;
  const rest = list.length - 3;
  const other = rest === 1 ? "inny" : rest <= 4 ? "inne" : "innych";
  return `${list.slice(0, 3).join(", ")} i ${rest} ${other}`;
}

// The phase that headlines the card: any peak wins; otherwise one shared phase is named (all at
// their start / all past their peak), and a mix of phases is simply "a season is under way" - never
// "start of the season" while another allergen is already ending. A taxon without a phase (odd
// payload) counts as "in its typical season".
export function seasonState(active: CalendarActiveLine[]): SeasonState {
  if (active.length === 0) return "out";
  if (active.some((t) => t.phase === "peak")) return "peak";
  const phases = new Set(active.map((t) => t.phase));
  if (phases.size === 1) {
    if (phases.has("start")) return "start";
    if (phases.has("end")) return "end";
  }
  return "active";
}

function seasonText(state: SeasonState, active: CalendarActiveLine[]): string {
  const named = (phase: CalendarActiveLine["phase"]) => formatAllergens(active.filter((t) => t.phase === phase).map((t) => t.name));
  switch (state) {
    case "out":
      return "Żaden z monitorowanych alergenów nie jest teraz w typowym okresie pylenia.";
    case "start":
      return `Rozpoczyna się typowy okres pylenia: ${named("start")}.`;
    case "active":
      return `W typowym sezonie są teraz: ${formatAllergens(active.map((t) => t.name))}.`;
    case "peak":
      return `To typowo jeden z najbardziej intensywnych okresów pylenia: ${named("peak")}.`;
    case "end":
      return `Typowy okres pylenia ${formatAllergens(active.map((t) => t.name))} zbliża się do końca.`;
  }
}

function seasonContext(state: SeasonState, forecast: ForecastLevel): string {
  if (state === "out") {
    return forecast === "elevated"
      ? "Prognoza pokazuje jednak wyższe stężenia pyłków — sprawdź ją powyżej."
      : "Aktualna prognoza może nadal wskazywać obecność pyłków.";
  }
  if (forecast === "low") return "Prognoza na dziś jest jednak niska — pogoda mocno zmienia rzeczywiste pylenie.";
  switch (state) {
    case "start":
      return "Warto częściej sprawdzać aktualną prognozę.";
    case "active":
      return "Sprawdź aktualne stężenia powyżej — pogoda może mocno zmieniać rzeczywiste pylenie.";
    case "peak":
      return forecast === "elevated"
        ? "Prognoza potwierdza wyższe stężenia również dziś."
        : "Aktualna prognoza pokaże, czy wysokie stężenia występują również dziś.";
    case "end":
      return "Stężenia mogą nadal występować lokalnie.";
  }
}

export function seasonSummary(view: CalendarView, forecast: ForecastLevel): SeasonSummary {
  const state = seasonState(view.active);
  return {
    state,
    icon: SEASON_ICON[state],
    title: SEASON_TITLE[state],
    text: seasonText(state, view.active),
    context: seasonContext(state, forecast),
  };
}

export const CALENDAR_CTA = "Zobacz kalendarz sezonów";
export const CALENDAR_HOW_TITLE = "Jak działa kalendarz?";
export const CALENDAR_HOW_INTRO =
  "Kalendarz pokazuje, kiedy dany alergen zwykle pyli w Polsce. To typowy przebieg sezonu, nie pomiar i nie prognoza — aktualne stężenia pokazuje prognoza pyłków.";
