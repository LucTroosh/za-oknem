// Pure freshness logic, split out from index.tsx so it can be unit-tested
// without pulling in react-native (which needs a full RN test runner to import
// at all). No react/react-native imports here — keep it that way.

// Matches app/api/v1/air.py's response shape (see apps/api).
export type Freshness = "FRESH" | "RECENT" | "STALE";

export const FRESHNESS_LABEL: Record<Freshness, string> = {
  FRESH: "świeże",
  RECENT: "niedawne",
  STALE: "nieaktualne",
};

// Mirrors the thresholds in apps/api/app/api/v1/air.py — recomputed client-side
// (Codex review) so the label doesn't freeze at whatever it was on load while the
// screen stays mounted for hours. Keep both in sync if the backend thresholds change.
export const FRESH_MAX_AGE_MS = 2 * 60 * 60 * 1000;
export const RECENT_MAX_AGE_MS = 6 * 60 * 60 * 1000;

export function freshnessOf(observedAt: string, now: number): Freshness {
  const age = now - new Date(observedAt).getTime();
  if (age <= FRESH_MAX_AGE_MS) return "FRESH";
  if (age <= RECENT_MAX_AGE_MS) return "RECENT";
  return "STALE";
}
