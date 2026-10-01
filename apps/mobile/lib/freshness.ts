// Freshness helpers, shared across screens. The FRESH/RECENT/STALE classification of
// a row is computed server-side (different thresholds per data domain - air 2h/6h,
// weather 4h/8h, ADR-004) and returned in API responses. The client only (1) combines
// labels (worst wins, ADR-012) and (2) ages them against the device clock, because a
// mounted screen is not refetched while it stays open - it never UPGRADES a label.
export type Freshness = "FRESH" | "RECENT" | "STALE";

export const FRESHNESS_LABEL: Record<Freshness, string> = {
  FRESH: "świeże",
  RECENT: "niedawne",
  STALE: "nieaktualne",
};

// ADR-012: UNAVAILABLE = no data / the source never succeeded.
export type FreshnessState = Freshness | "UNAVAILABLE";

const ORDER: FreshnessState[] = ["FRESH", "RECENT", "STALE", "UNAVAILABLE"];

// Unknown/garbage -> UNAVAILABLE (fail safe: never a falsely fresh label).
export function asFreshness(f: unknown): FreshnessState {
  return ORDER.includes(f as FreshnessState) ? (f as FreshnessState) : "UNAVAILABLE";
}

// The worst of the given labels wins (data AND source can each be stale, ADR-012).
export function worstFreshness(...labels: unknown[]): FreshnessState {
  return ORDER[Math.max(0, ...labels.map((f) => ORDER.indexOf(asFreshness(f))))];
}

const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

// Block's own `freshness` vs its `source_status.freshness`: the worse one wins.
export function effectiveFreshness(block: Record<string, unknown>): FreshnessState {
  return worstFreshness(
    block.freshness,
    isObject(block.source_status) ? block.source_status.freshness : undefined,
  );
}

// Same bounds as the server's FRESH_MAX_AGE/RECENT_MAX_AGE of the domain
// (api/v1/air.py, weather.py) - duplicated on purpose, see above.
export type AgeBounds = { freshMs: number; recentMs: number };

// Label for an ISO timestamp at device time `now`. Missing/unparsable -> UNAVAILABLE
// (age cannot be verified); a timestamp ahead of `now` counts as age 0 (the server's
// own label still applies through worstFreshness).
export function ageFreshness(iso: unknown, now: number, bounds: AgeBounds): FreshnessState {
  const t = typeof iso === "string" ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(t)) return "UNAVAILABLE";
  const age = now - t;
  if (age <= bounds.freshMs) return "FRESH";
  if (age <= bounds.recentMs) return "RECENT";
  return "STALE";
}

// "12 min temu" / "3 godz. temu" / "2 dni temu"; null when the timestamp is unusable.
export function ageLabel(iso: unknown, now: number): string | null {
  const t = typeof iso === "string" ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(t)) return null;
  const min = Math.floor(Math.max(0, now - t) / 60_000);
  if (min < 1) return "przed chwilą";
  if (min < 60) return `${min} min temu`;
  const h = Math.floor(min / 60);
  if (h < 48) return `${h} godz. temu`;
  return `${Math.floor(h / 24)} dni temu`;
}
