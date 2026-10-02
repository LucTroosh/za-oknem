// TASK-12.16 (S8): the full list of IMGW water-level stations. Statuses come from the backend
// (IMGW's own thresholds); nothing here classifies a level (rule #10). This module decides how
// the list is grouped and what a row may CLAIM: a NORMAL reading that is old does not say
// "below thresholds" (rule #8), a station without thresholds is "not assessed", never "OK".
import { type HydroBlock, type HydroItem, type HydroStation, ageFreshness, stationFreshness } from "./hydro";
import { asFreshness, worstFreshness } from "./freshness";

export type RiverGroupKey = "alarm" | "warning" | "normal" | "outdated" | "unassessed";

export type RiverGroup = { key: RiverGroupKey; title: string; note: string | null; items: HydroItem[] };

export type RiversModel = {
  // Source healthy = FRESH/RECENT by its own status and by age on the device clock.
  sourceOk: boolean;
  lastSuccessAt: string | null;
  groups: RiverGroup[];
  total: number; // stations matching the query
};

const TITLE: Record<RiverGroupKey, string> = {
  alarm: "Stan alarmowy",
  warning: "Stan ostrzegawczy",
  normal: "Poniżej progów",
  outdated: "Odczyt nieaktualny",
  unassessed: "Bez progów IMGW",
};

const NOTE: Record<RiverGroupKey, string | null> = {
  alarm: null,
  warning: null,
  normal: "Odczyt poniżej progów ostrzegawczego i alarmowego IMGW.",
  outdated: "Ostatni odczyt jest stary — nie wiemy, jaki jest stan teraz.",
  unassessed: "Dla tych stacji IMGW nie publikuje progów, więc ich nie oceniamy.",
};

const ORDER: RiverGroupKey[] = ["alarm", "warning", "normal", "outdated", "unassessed"];

// Lowercase, no diacritics (incl. ł), single spaces: "Kłodzko" matches "klodzko".
export function normalizeName(s: string): string {
  return s
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/ł/gi, "l")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

const cmp = (a: HydroStation, b: HydroStation) =>
  a.station_name < b.station_name ? -1 : a.station_name > b.station_name ? 1 : a.station_id < b.station_id ? -1 : a.station_id > b.station_id ? 1 : 0;

// A real warning/alarm stays in its group even when the reading is old (it is shown with its
// age badge): hiding it would be worse. Only NORMAL readings lose their claim when stale.
function groupOf(s: HydroStation, now: number): RiverGroupKey {
  if (s.status === "ALARM") return "alarm";
  if (s.status === "WARNING") return "warning";
  if (s.status === "NORMAL") {
    const f = stationFreshness(s, now);
    return f === "FRESH" || f === "RECENT" ? "normal" : "outdated";
  }
  return "unassessed";
}

export function buildRivers(block: HydroBlock, now: number, query = ""): RiversModel {
  const stations = Array.isArray(block.stations) ? block.stations : [];
  const q = normalizeName(query);
  const matching = q === "" ? stations : stations.filter((s) => normalizeName(s.station_name).includes(q));
  const lastSuccessAt = typeof block.source_status?.last_success_at === "string" ? block.source_status.last_success_at : null;
  const srcState = worstFreshness(asFreshness(block.source_status?.freshness), ageFreshness(lastSuccessAt, now));
  const buckets = new Map<RiverGroupKey, HydroStation[]>();
  for (const s of matching) {
    const k = groupOf(s, now);
    buckets.set(k, [...(buckets.get(k) ?? []), s]);
  }
  const groups = ORDER.flatMap((key) => {
    const list = (buckets.get(key) ?? []).sort(cmp);
    return list.length === 0
      ? []
      : [{ key, title: TITLE[key], note: NOTE[key], items: list.map((station) => ({ station, freshness: stationFreshness(station, now) })) }];
  });
  return { sourceOk: srcState === "FRESH" || srcState === "RECENT", lastSuccessAt, groups, total: matching.length };
}

// Paging: keep the first `limit` rows across groups in order; empty groups disappear.
export function limitGroups(groups: RiverGroup[], limit: number): RiverGroup[] {
  let left = limit;
  return groups.flatMap((g) => {
    if (left <= 0) return [];
    const items = g.items.slice(0, left);
    left -= items.length;
    return [{ ...g, items }];
  });
}

export const RIVERS_PAGE = 30;
