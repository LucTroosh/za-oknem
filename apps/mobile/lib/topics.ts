// TASK-12.13 (S10): "Co chcesz śledzić?" - a LOCAL preference of which modules Start shows.
// It is not a profile (spec §3): no species, no age, no health. It never changes a source value
// and never hides a real warning: an active alert banner is shown whatever is selected; the
// "Alerty" topic only governs the quiet "no alerts / could not check" line.
// An empty selection means "all available" (the default). No water / bathing tiles exist.
import type { AlertsStatus, ModuleKey, StatusCardModel } from "./home";

export type TopicKey = "air" | "weather" | "pollen" | "alerts";

// Order = tile order. "Aktywność" is deliberately absent: the module does not exist yet (TASK-7.9).
export const TOPICS: readonly { key: TopicKey; label: string; hint: string }[] = [
  { key: "air", label: "Powietrze", hint: "Jakość powietrza z najbliższej stacji" },
  { key: "weather", label: "Pogoda", hint: "Pogoda i prognoza" },
  { key: "pollen", label: "Pyłki", hint: "Prognoza pylenia" },
  { key: "alerts", label: "Alerty", hint: "Ostrzeżenia i stany wody" },
];

const KEYS: readonly string[] = TOPICS.map((t) => t.key);

// From storage: unknown entries dropped, duplicates removed, anything else -> [] (= all).
export function parseTopics(x: unknown): TopicKey[] {
  if (!Array.isArray(x)) return [];
  return [...new Set(x.filter((k): k is TopicKey => typeof k === "string" && KEYS.includes(k)))];
}

// Empty = everything. Otherwise only the selected ones.
export function isTopicOn(selected: readonly TopicKey[], key: TopicKey): boolean {
  return selected.length === 0 || selected.includes(key);
}

// Tapping works on the EFFECTIVE selection (empty = all tiles look on, so the first tap turns that
// tile off). Nothing left selected, or everything selected, is stored as [] ("show all").
export function toggleTopic(selected: readonly TopicKey[], key: TopicKey): TopicKey[] {
  const effective = TOPICS.map((t) => t.key).filter((k) => isTopicOn(selected, k));
  const next = effective.includes(key) ? effective.filter((k) => k !== key) : [...effective, key];
  return next.length === 0 || next.length === TOPICS.length ? [] : next;
}

const CARD_TOPIC: Record<ModuleKey, TopicKey> = { air: "air", weather: "weather", pollen: "pollen" };

// Status cards the selection shows. A hidden topic is a missing card, never "0" or "brak".
export function visibleCards(cards: StatusCardModel[], selected: readonly TopicKey[]): StatusCardModel[] {
  return cards.filter((c) => isTopicOn(selected, CARD_TOPIC[c.key]));
}

export function showPollenCalendar(selected: readonly TopicKey[]): boolean {
  return isTopicOn(selected, "pollen");
}

// Safety rule: a real warning (active banners) is NEVER hidden by the selection. Only the quiet
// states (confirmed none / could not check / loading) follow the "Alerty" topic.
export function showAlertsStatus(status: AlertsStatus, selected: readonly TopicKey[]): boolean {
  return status.kind === "active" || isTopicOn(selected, "alerts");
}
