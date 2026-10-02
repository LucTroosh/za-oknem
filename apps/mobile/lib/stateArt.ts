// Which state illustration (asset pack v2, docs/ui/asset-implementation-v2.md §6) a screen may show.
// Pure logic, no react-native import. An illustration only ever ACCOMPANIES native text; it never
// carries information and never turns a missing answer into a calm one (rule #8, ADR-012/028).
import type { AlertsSummary } from "./alerts";
import type { GlyphLevel } from "./home";

export type StateArt = "good" | "caution" | "bad" | "noAlerts" | "noData" | "offline" | "locationRequired";

// UNKNOWN verdict -> no-data, never condition-good.
export function verdictArt(level: GlyphLevel): StateArt {
  switch (level) {
    case "GOOD":
      return "good";
    case "CAUTION":
      return "caution";
    case "AVOID":
      return "bad";
    default:
      return "noData";
  }
}

// no-alerts only for a CONFIRMED zero (every source FRESH/RECENT). Unknown / stale / unavailable
// / a missing block -> no-data. A non-empty list has no illustration (the list is the content).
// `refreshFailed`: the last refresh failed and the block is cached data - never re-confirm a zero.
export function alertsArt(summary: AlertsSummary | null, refreshFailed = false): StateArt | null {
  if (summary === null) return "noData";
  switch (summary.kind) {
    case "none-confirmed":
      return refreshFailed ? "noData" : "noAlerts";
    case "unavailable":
      return "noData";
    default:
      return null;
  }
}

// Shown with "could not load": offline only for a genuine connectivity failure. An HTTP answer
// (any status) proves the network works, and a timeout is ambiguous, so both are no-data.
export function loadErrorArt(networkFailure: boolean): StateArt {
  return networkFailure ? "offline" : "noData";
}

// fetch() rejects with a TypeError ("Network request failed") when the request never reached a
// server. ApiError (HTTP status) and AbortError (our timeout / cancellation) are not that.
export function isNetworkFailure(err: unknown): boolean {
  return err instanceof TypeError;
}

// Shown only when no location is chosen (the picker, first run).
export const LOCATION_REQUIRED_ART: StateArt = "locationRequired";
