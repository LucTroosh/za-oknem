import { describe, expect, it, vi } from "vitest";

import { distanceText, findNearestPlace, nearestMessage } from "./nearest";

const place = { place_id: 7, name: "Oleśnica", label: "Oleśnica, woj. dolnośląskie", kind: "PPL", admin1_code: "72", admin2_code: null, latitude: 51.2, longitude: 17.4, population: 1 };
const pos = { latitude: 51.21, longitude: 17.38 };
const deps = (over: Partial<Parameters<typeof findNearestPlace>[0]> = {}) => ({
  requestPermission: async () => ({ granted: true, canAskAgain: true }),
  getPosition: async () => pos,
  lookup: async () => ({ status: "found" as const, place, distance_km: 2.4, attribution: "GeoNames" }),
  ...over,
});

describe("findNearestPlace", () => {
  it("returns the nearest place the backend found", async () => {
    expect(await findNearestPlace(deps())).toEqual({ kind: "found", place, distanceKm: 2.4, attribution: "GeoNames" });
  });
  it("sends the position only after permission is granted", async () => {
    const getPosition = vi.fn(async () => pos);
    const lookup = vi.fn();
    expect(await findNearestPlace(deps({ requestPermission: async () => ({ granted: false, canAskAgain: false }), getPosition, lookup }))).toEqual({ kind: "denied", canAskAgain: false });
    expect(getPosition).not.toHaveBeenCalled();
    expect(lookup).not.toHaveBeenCalled();
  });
  it("a failing position read is 'unavailable', a failing backend is 'error', nothing in range is its own state", async () => {
    expect((await findNearestPlace(deps({ getPosition: async () => Promise.reject(new Error("off")) }))).kind).toBe("unavailable");
    expect((await findNearestPlace(deps({ requestPermission: async () => Promise.reject(new Error("x")) }))).kind).toBe("unavailable");
    expect((await findNearestPlace(deps({ lookup: async () => Promise.reject(new Error("503")) }))).kind).toBe("error");
    expect((await findNearestPlace(deps({ lookup: async () => ({ status: "out_of_range" as const, place: null, distance_km: null, attribution: "x" }) }))).kind).toBe("out_of_range");
  });
});

describe("copy", () => {
  it("distance is rounded and honest about sub-kilometre", () => {
    expect(distanceText(0.4)).toBe("mniej niż 1 km od Ciebie");
    expect(distanceText(2.6)).toBe("ok. 3 km od Ciebie");
  });
  it("every failure state has a message; success/idle have none", () => {
    for (const kind of ["unavailable", "out_of_range", "error"] as const) expect(nearestMessage({ kind })).toBeTruthy();
    expect(nearestMessage({ kind: "denied", canAskAgain: true })).not.toBe(nearestMessage({ kind: "denied", canAskAgain: false }));
    expect(nearestMessage({ kind: "idle" })).toBeNull();
  });
});
