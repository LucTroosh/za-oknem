import { describe, expect, it } from "vitest";

import {
  DEFAULT_SETTINGS,
  type Settings,
  dropLocationIf,
  entryRedirect,
  locationFromArea,
  locationFromPlace,
  parseSettings,
  readSettings,
  shouldReactivate,
  refreshLocation,
  serializeSettings,
} from "./location";

const loc = { geoAreaId: 7, placeId: 42, name: "Nowa Wieś", label: "Nowa Wieś, pow. gliwicki, woj. śląskie", latitude: 50.3, longitude: 18.7, attribution: "Nazwy miejscowości: GeoNames (CC BY 4.0)" };
const done: Settings = { onboardingDone: true, location: loc };

describe("settings storage", () => {
  it("round-trips", () => {
    expect(parseSettings(serializeSettings(done))).toEqual(done);
    expect(parseSettings(serializeSettings({ ...done, location: { ...loc, placeId: null } })).location?.placeId).toBeNull();
  });
  it("stores one location and no user coordinates, only the place centre", () => {
    const keys = Object.keys(JSON.parse(serializeSettings(done)));
    expect(keys.sort()).toEqual(["location", "onboardingDone", "v"]);
  });
  it("missing / corrupt / foreign-version records give the defaults", () => {
    for (const raw of [null, undefined, "", "{", "[]", "42", "null", JSON.stringify({ v: 2, onboardingDone: true, location: loc }), JSON.stringify({ onboardingDone: true })]) {
      expect(parseSettings(raw)).toEqual(DEFAULT_SETTINGS);
    }
  });
  it("a damaged location is dropped but the finished onboarding stays", () => {
    const bad = (l: unknown) => parseSettings(JSON.stringify({ v: 1, onboardingDone: true, location: l }));
    for (const l of [null, "x", { ...loc, geoAreaId: 0 }, { ...loc, geoAreaId: 1.5 }, { ...loc, name: "" }, { ...loc, label: 3 }, { ...loc, latitude: 91 }, { ...loc, longitude: "18" }, { ...loc, placeId: -1 }]) {
      expect(bad(l)).toEqual({ onboardingDone: true, location: null });
    }
  });
  it("onboardingDone must be literally true", () => {
    expect(parseSettings(JSON.stringify({ v: 1, onboardingDone: "yes", location: loc })).onboardingDone).toBe(false);
  });
});

describe("location builders", () => {
  const area = { geo_area_id: 3, latitude: 50, longitude: 19, name: "Gliwice", slug: "gliwice", teryt_code: null, weather_polling_active: true };
  it("from a seeded area", () => {
    expect(locationFromArea(area)).toEqual({ geoAreaId: 3, placeId: null, name: "Gliwice", label: "Gliwice", latitude: 50, longitude: 19, attribution: null });
  });
  it("from a place + its activated area", () => {
    const place = { admin1_code: "83", admin2_code: null, kind: "PPL", label: loc.label, latitude: 50.3, longitude: 18.7, name: loc.name, place_id: 42, population: null };
    expect(locationFromPlace(place, { ...area, geo_area_id: 7 }, loc.attribution)).toEqual(loc);
  });
});

describe("entryRedirect", () => {
  it("first run: everything goes to Welcome", () => {
    expect(entryRedirect(DEFAULT_SETTINGS, "tabs")).toBe("/welcome");
    expect(entryRedirect(DEFAULT_SETTINGS, "welcome")).toBeNull();
  });
  it("after onboarding: Welcome never comes back, tabs render", () => {
    expect(entryRedirect(done, "welcome")).toBe("/");
    expect(entryRedirect(done, "tabs")).toBeNull();
  });
  it("the picker needs the Welcome CTA on the first run (no deep-link bypass), never afterwards", () => {
    expect(entryRedirect(DEFAULT_SETTINGS, "location")).toBe("/welcome");
    expect(entryRedirect(DEFAULT_SETTINGS, "location", true)).toBeNull();
    expect(entryRedirect(done, "location")).toBeNull();
    expect(entryRedirect({ onboardingDone: true, location: null }, "location")).toBeNull();
  });
  it("finished onboarding but no usable location: the picker, not Welcome", () => {
    const s = { onboardingDone: true, location: null };
    expect(entryRedirect(s, "tabs")).toBe("/location");
    expect(entryRedirect(s, "welcome")).toBe("/location");
  });
});

describe("dropLocationIf", () => {
  it("forgets the location only when it is still the one that was reported gone", () => {
    expect(dropLocationIf(done, 7)).toEqual({ onboardingDone: true, location: null });
  });
  it("a late answer for an earlier place changes nothing (same object)", () => {
    expect(dropLocationIf(done, 3)).toBe(done);
    const none = { onboardingDone: true, location: null };
    expect(dropLocationIf(none, 7)).toBe(none);
  });
});

describe("attribution and refreshLocation", () => {
  it("a record saved before the attribution field parses with null", () => {
    const old: Record<string, unknown> = { ...loc };
    delete old.attribution;
    expect(parseSettings(JSON.stringify({ v: 1, onboardingDone: true, location: old })).location?.attribution).toBeNull();
  });
  it("the activation answer replaces a stale name / area id of the same place", () => {
    const next = { ...loc, geoAreaId: 99, label: "Nowa Wieś, pow. gliwicki, woj. śląskie (poprawka)" };
    expect(refreshLocation(done, 42, next)).toEqual({ onboardingDone: true, location: next });
  });
  it("same data or another place: the very same object back", () => {
    expect(refreshLocation(done, 42, { ...loc })).toBe(done);
    expect(refreshLocation(done, 5, { ...loc, geoAreaId: 99 })).toBe(done);
    const seeded = { onboardingDone: true, location: { ...loc, placeId: null } };
    expect(refreshLocation(seeded, 42, loc)).toBe(seeded);
  });
});

describe("readSettings", () => {
  it("reads a valid record", async () => {
    expect(await readSettings(() => Promise.resolve(serializeSettings(done)), 50)).toEqual({ settings: done, ok: true });
  });
  it("no record is a normal first run (ok)", async () => {
    expect(await readSettings(() => Promise.resolve(null), 50)).toEqual({ settings: DEFAULT_SETTINGS, ok: true });
  });
  it("a read error is flagged, with defaults to start on", async () => {
    const r = await readSettings(() => Promise.reject(new Error("io")), 50);
    expect(r).toEqual({ settings: DEFAULT_SETTINGS, ok: false });
    expect(r.settings).not.toBe(DEFAULT_SETTINGS); // never the shared singleton
  });
  it("a hanging read times out with the defaults, flagged", async () => {
    expect(await readSettings(() => new Promise<string | null>(() => undefined), 20)).toEqual({ settings: DEFAULT_SETTINGS, ok: false });
  });
});

describe("shouldReactivate", () => {
  it("first time, then at most hourly", () => {
    expect(shouldReactivate(null, 1000)).toBe(true);
    expect(shouldReactivate(0, 59 * 60_000)).toBe(false);
    expect(shouldReactivate(0, 60 * 60_000)).toBe(true);
  });
});
