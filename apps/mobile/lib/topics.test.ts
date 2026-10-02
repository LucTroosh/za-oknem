import { describe, expect, it } from "vitest";

import type { AlertsStatus, StatusCardModel } from "./home";
import { TOPICS, isTopicOn, parseTopics, showAlertsStatus, showPollenCalendar, toggleTopic, visibleCards } from "./topics";

const card = (key: StatusCardModel["key"]): StatusCardModel => ({
  key,
  title: key,
  state: "ready",
  level: "GOOD",
  headline: "x",
  supporting: null,
  freshnessNote: null,
  coverageNote: null,
});
const all = [card("air"), card("weather"), card("pollen")];

describe("tiles", () => {
  it("has no water / bathing / activity tile", () => {
    expect(TOPICS.map((t) => t.key)).toEqual(["air", "weather", "pollen", "alerts"]);
    expect(JSON.stringify(TOPICS)).not.toMatch(/kąpiel|woda|aktywno/i);
  });
});

describe("parseTopics", () => {
  it("keeps known keys once, drops the rest, garbage -> [] (all)", () => {
    expect(parseTopics(["air", "pollen", "air", "water", 3])).toEqual(["air", "pollen"]);
    expect(parseTopics("air")).toEqual([]);
    expect(parseTopics(undefined)).toEqual([]);
  });
});

describe("selection", () => {
  it("empty means everything is on", () => {
    for (const t of TOPICS) expect(isTopicOn([], t.key)).toBe(true);
    expect(visibleCards(all, [])).toHaveLength(3);
  });
  it("only selected topics show their card; a hidden topic is a missing card", () => {
    expect(visibleCards(all, ["air", "weather"]).map((c) => c.key)).toEqual(["air", "weather"]);
    expect(showPollenCalendar(["air"])).toBe(false);
    expect(showPollenCalendar(["pollen"])).toBe(true);
    expect(showPollenCalendar([])).toBe(true);
  });
  it("first tap on the implicit 'all' turns that tile off", () => {
    expect(toggleTopic([], "pollen")).toEqual(["air", "weather", "alerts"]);
  });
  it("turning everything back on, or everything off, returns to 'all' (empty)", () => {
    expect(toggleTopic(["air", "weather", "alerts"], "pollen")).toEqual([]);
    expect(toggleTopic(["air"], "air")).toEqual([]);
  });
  it("adds a tile to an explicit selection", () => {
    expect(toggleTopic(["air"], "weather")).toEqual(["air", "weather"]);
  });
});

describe("safety: a real warning is never hidden", () => {
  const active: AlertsStatus = { kind: "active", banners: [{ tone: "danger", text: "x" }] };
  const none: AlertsStatus = { kind: "none" };
  const unknown: AlertsStatus = { kind: "unavailable", banners: [{ tone: "neutral", text: "x" }] };
  it("active banners show even with the Alerty topic off", () => {
    expect(showAlertsStatus(active, ["air"])).toBe(true);
  });
  it("quiet states follow the topic", () => {
    expect(showAlertsStatus(none, ["air"])).toBe(false);
    expect(showAlertsStatus(unknown, ["air"])).toBe(false);
    expect(showAlertsStatus(none, ["alerts"])).toBe(true);
    expect(showAlertsStatus(none, [])).toBe(true);
  });
});
