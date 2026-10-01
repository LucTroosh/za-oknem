// Types the screens share (moved out of the old single-screen index.tsx so route files stay
// routes). They come from the generated API contract (packages/api-contract, ADR-024);
// components still take `unknown` and parse defensively, so an older backend degrades,
// never crashes. Freshness labels are the server's own (ADR-004); the client never
// upgrades one, it only combines it with `source_status` (worst wins, ADR-012).
import type {
  DashboardArea as ContractArea,
  DashboardSourceStatus as ContractSourceStatus,
} from "../../../packages/api-contract/schema";

export type DashboardArea = ContractArea;

// TASK-7.3: top-level (not per area) because `air`/`weather` are null when there is no
// station/snapshot - the source status must survive that.
export type DashboardSourceStatus = ContractSourceStatus;

export type LoadState = "loading" | "ready" | "error";

// Date + time together, always: STALE only gives a broad age bucket, so "14:00" alone
// could be today or yesterday (Codex review, round 2).
export function formatObservedAt(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "brak daty" : d.toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
}
