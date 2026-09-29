// Freshness label lookup, shared across screens. The FRESH/RECENT/STALE
// classification itself is always computed server-side (different thresholds
// per data domain - air 2h/6h, weather 4h/8h, ADR-004) and returned in API
// responses, never recomputed on the client.
export type Freshness = "FRESH" | "RECENT" | "STALE";

export const FRESHNESS_LABEL: Record<Freshness, string> = {
  FRESH: "świeże",
  RECENT: "niedawne",
  STALE: "nieaktualne",
};
