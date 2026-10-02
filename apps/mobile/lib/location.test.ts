import { describe, expect, it } from "vitest";

import {
  DEFAULT_SETTINGS,
  type Settings,
  entryRedirect,
  locationFromArea,
  locationFromPlace,
  parseSettings,
  serializeSettings,
} from "./location";

const loc = { geoAreaId: 7, placeId: 42, name: "Nowa Wieś", label: "Nowa Wieś, pow. gliwicki, woj. śląskie", latitude: 50.3, longitude: 18.7 };
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
    expect(locationFromArea(area)).toEqual({ geoAreaId: 3, placeId: null, name: "Gliwice", label: "Gliwice", latitude: 50, longitude: 19 });
  });
  it("from a place + its activated area", () => {
    const place = { admin1_code: "83", admin2_code: null, kind: "PPL", label: loc.label, latitude: 50.3, longitude: 18.7, name: loc.name, place_id: 42, population: null };
    expect(locationFromPlace(place, { ...area, geo_area_id: 7 })).toEqual(loc);
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
  it("finished onboarding but no usable location: the picker, not Welcome", () => {
    const s = { onboardingDone: true, location: null };
    expect(entryRedirect(s, "tabs")).toBe("/location");
    expect(entryRedirect(s, "welcome")).toBe("/location");
  });
});
