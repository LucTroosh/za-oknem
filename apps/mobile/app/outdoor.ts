// TASK-7.8: presentation of the backend's `outdoor` block (TASK-7.7 / ADR-016).
// The verdict, its reasons and its gaps are computed server-side by deterministic rules
// (app/outdoor.py) - nothing here classifies anything (rule #10): this module only
// formats what the block says and decides what the card may CLAIM, so missing/old data
// never reads as a confident GOOD (rule #8).

export type OutdoorLevel = "GOOD" | "MODERATE" | "POOR" | "UNKNOWN";

export type OutdoorReason = {
  code: string;
  param: string;
  value: number;
  threshold: number;
  comparison: "gt" | "gte" | "lt" | "lte";
  unit: string;
  level: "MODERATE" | "POOR";
};

export type OutdoorMissing = {
  group: string;
  params: string[];
  status: "MISSING" | "STALE" | "INVALID";
  core: boolean;
  // false = an alternative in the group still worked (e.g. PM2.5 present, PM10 absent).
  blocking: boolean;
};

export type OutdoorBlock = {
  level: OutdoorLevel;
  reasons: OutdoorReason[];
  missing: OutdoorMissing[];
  // ISO time after which the earliest usable input turns STALE (backend, from the
  // same freshness bounds as the rest of the dashboard); null when no input fed it.
  valid_until?: string | null;
};

export type OutdoorView = {
  level: OutdoorLevel;
  icon: string; // level is never conveyed by colour alone
  headline: string;
  reasonLines: string[];
  missingLine: string | null;
};

// The screen does not refetch by itself and the backend judged freshness at response
// time, so the verdict is good only until `valid_until` (earliest input expiry, PR #68
// review) - past it the card stops asserting it (same lesson as alerts/hydro, PR #59/#61).
// Without a usable `valid_until` fall back to this age of the response.
export const OUTDOOR_FALLBACK_MAX_AGE_MS = 60 * 60 * 1000;

export const OUTDOOR_DISCLAIMER = "Ocena orientacyjna — nie zastępuje ostrzeżeń IMGW.";

export const OUTDOOR_LEVEL_LABEL: Record<OutdoorLevel, string> = {
  GOOD: "Dobre warunki",
  MODERATE: "Umiarkowane warunki",
  POOR: "Złe warunki",
  UNKNOWN: "Brak oceny",
};

const LEVEL_ICON: Record<OutdoorLevel, string> = { GOOD: "✓", MODERATE: "!", POOR: "✕", UNKNOWN: "?" };

// Keys = OutdoorInputs fields (app/outdoor.py). Unknown codes fall back to the raw code.
const PARAM_LABEL: Record<string, string> = {
  temperature_2m: "temperatura",
  apparent_temperature: "temperatura odczuwalna",
  precipitation: "opady",
  wind_speed_10m: "wiatr",
  wind_gusts_10m: "porywy wiatru",
  uv_index: "indeks UV",
  visibility: "widzialność",
  pm25: "PM2.5",
  pm10: "PM10",
};

// Keys = Rule.group in app/outdoor.py.
const GROUP_LABEL: Record<string, string> = {
  air: "jakość powietrza",
  thermal: "temperatura",
  wind: "wiatr",
  precipitation: "opady",
  gusts: "porywy wiatru",
  uv: "indeks UV",
  visibility: "widzialność",
};

const STATUS_LABEL: Record<string, string> = {
  MISSING: "brak",
  STALE: "nieaktualne",
  INVALID: "błędne",
};

const COMPARISON_SYMBOL: Record<string, string> = { gt: ">", gte: "≥", lt: "<", lte: "≤" };

const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

// Formatting only: the number as sent (no rounding that could make value and threshold
// look equal), Polish decimal comma, space before a non-empty unit.
function num(value: unknown, unit: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "?";
  const u = typeof unit === "string" && unit !== "" ? ` ${unit}` : "";
  return `${String(value).replace(".", ",")}${u}`;
}

export function reasonLine(r: OutdoorReason): string {
  const label = PARAM_LABEL[r.param] ?? r.param;
  const symbol = COMPARISON_SYMBOL[r.comparison] ?? "";
  return `${label}: ${num(r.value, r.unit)} (próg ${symbol} ${num(r.threshold, r.unit)})`;
}

function missingItem(m: OutdoorMissing): string {
  const params = Array.isArray(m.params) ? m.params : [];
  // A blocking gap is the whole factor; a non-blocking one only the absent alternative.
  const name = m.blocking
    ? (GROUP_LABEL[m.group] ?? m.group)
    : params.map((p) => PARAM_LABEL[p] ?? p).join(", ") || (GROUP_LABEL[m.group] ?? m.group);
  return `${name} (${STATUS_LABEL[m.status] ?? "brak"})`;
}

export function missingList(missing: unknown): string {
  if (!Array.isArray(missing)) return "";
  return missing.filter(isObject).map((m) => missingItem(m as unknown as OutdoorMissing)).join(", ");
}

function validLevel(l: unknown): OutdoorLevel {
  return l === "GOOD" || l === "MODERATE" || l === "POOR" ? l : "UNKNOWN";
}

function unknownView(headline: string): OutdoorView {
  return { level: "UNKNOWN", icon: LEVEL_ICON.UNKNOWN, headline, reasonLines: [], missingLine: null };
}

function isExpired(validUntil: unknown, now: number, receivedAt: number): boolean {
  const t = typeof validUntil === "string" ? Date.parse(validUntil) : Number.NaN;
  return Number.isNaN(t) ? now - receivedAt > OUTDOOR_FALLBACK_MAX_AGE_MS : now > t;
}

// null = nothing to show (older backend without the field, or not an object): the card
// disappears instead of inventing a verdict. `receivedAt` = device time of the response.
export function outdoorView(block: unknown, now: number, receivedAt: number): OutdoorView | null {
  if (!isObject(block)) return null;
  const level = validLevel(block.level);
  if (level !== "UNKNOWN" && isExpired(block.valid_until, now, receivedAt)) {
    return unknownView("Brak oceny — dane mogły się zestarzeć, odśwież widok");
  }
  const gaps = missingList(block.missing);
  if (level === "UNKNOWN") {
    return unknownView(gaps === "" ? "Brak oceny — brak danych" : `Brak oceny — brak danych: ${gaps}`);
  }
  const reasons = Array.isArray(block.reasons) ? block.reasons.filter(isObject) : [];
  return {
    level,
    icon: LEVEL_ICON[level],
    headline: OUTDOOR_LEVEL_LABEL[level],
    reasonLines: reasons.map((r) => reasonLine(r as unknown as OutdoorReason)),
    missingLine: gaps === "" ? null : `Nie uwzględniono — brak danych: ${gaps}`,
  };
}
