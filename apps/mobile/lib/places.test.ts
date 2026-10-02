import { afterEach, describe, expect, it, vi } from "vitest";

import {
  POLLING_OFF_NOTICE,
  activatePlace,
  activationFailureMessage,
  debounce,
  emptyResultMessage,
  interpretActivation,
  placesPath,
  searchQuery,
} from "./places";
import { ApiError } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

const area = { geo_area_id: 9, latitude: 50, longitude: 19, name: "Wieś", slug: "place-1", teryt_code: null, weather_polling_active: true };
const place = { admin1_code: null, admin2_code: null, kind: "PPL", label: "Wieś", latitude: 50, longitude: 19, name: "Wieś", place_id: 1, population: null };
const response = (polling: string, a: unknown = area) => ({ area: a, attribution: "GeoNames", place, polling });
const ok = (body: unknown) => ({ ok: true, status: 200, json: () => Promise.resolve(body) });
const fail = (status: number) => ({ ok: false, status });

describe("searchQuery / placesPath", () => {
  it("needs two characters after trimming and collapses spaces", () => {
    expect(searchQuery("a")).toBeNull();
    expect(searchQuery("  a ")).toBeNull();
    expect(searchQuery(" Nowa   Wieś ")).toBe("Nowa Wieś");
  });
  it("encodes the query", () => {
    expect(placesPath("Łódź & co")).toBe("/api/v1/places?q=%C5%81%C3%B3d%C5%BA%20%26%20co&limit=10");
  });
  it("empty result copy names the query", () => {
    expect(emptyResultMessage("Xyz")).toContain("„Xyz”");
  });
});

describe("debounce", () => {
  it("fires once with the last arguments", async () => {
    const calls: string[] = [];
    const d = debounce((q: string) => calls.push(q), 20);
    d.call("a");
    d.call("ab");
    d.call("abc");
    await new Promise((r) => setTimeout(r, 60));
    expect(calls).toEqual(["abc"]);
  });
  it("cancel drops the pending call", async () => {
    const calls: string[] = [];
    const d = debounce((q: string) => calls.push(q), 20);
    d.call("a");
    d.cancel();
    await new Promise((r) => setTimeout(r, 60));
    expect(calls).toEqual([]);
  });
});

describe("interpretActivation", () => {
  it("active -> proceed, not limited", () => {
    expect(interpretActivation(response("active") as never)).toEqual({ kind: "proceed", area, limited: false });
  });
  it("capacity_reached / budget_exhausted / inactive -> proceed, limited (not an error)", () => {
    for (const p of ["capacity_reached", "budget_exhausted", "inactive"]) {
      expect(interpretActivation(response(p) as never)).toMatchObject({ kind: "proceed", limited: true });
    }
  });
  it("no area -> failed with a plain message", () => {
    const r = interpretActivation(response("active", null) as never);
    expect(r.kind).toBe("failed");
  });
  it("the Start notice says weather is unavailable and air may come from nearby", () => {
    expect(POLLING_OFF_NOTICE).toContain("Pogoda i pyłki");
    expect(POLLING_OFF_NOTICE).toContain("Powietrze może pochodzić ze stacji w okolicy");
  });
});

describe("activatePlace", () => {
  it("POSTs and proceeds", async () => {
    const f = vi.fn().mockResolvedValue(ok(response("active")));
    vi.stubGlobal("fetch", f);
    await expect(activatePlace(1)).resolves.toEqual({ kind: "proceed", area, limited: false });
    expect(f.mock.calls[0][0]).toContain("/api/v1/places/1/activate");
    expect(f.mock.calls[0][1].method).toBe("POST");
  });
  it("429/503: falls back to the read-only lookup and proceeds limited when the area exists", async () => {
    for (const status of [429, 503]) {
      const f = vi.fn().mockResolvedValueOnce(fail(status)).mockResolvedValueOnce(ok(response("inactive")));
      vi.stubGlobal("fetch", f);
      await expect(activatePlace(1)).resolves.toEqual({ kind: "proceed", area, limited: true });
      expect(f.mock.calls[1][0]).toMatch(/\/api\/v1\/places\/1$/);
    }
  });
  it("429/503 and no area yet -> honest failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(fail(429)).mockResolvedValueOnce(ok(response("inactive", null))));
    const r = await activatePlace(1);
    expect(r).toEqual({ kind: "failed", message: activationFailureMessage(new ApiError(429, "")) });
  });
  it("network error -> connection message, no lookup", async () => {
    const f = vi.fn().mockRejectedValue(new TypeError("Network request failed"));
    vi.stubGlobal("fetch", f);
    const r = await activatePlace(1);
    expect(r).toMatchObject({ kind: "failed" });
    expect(f).toHaveBeenCalledTimes(1);
  });
  it("other HTTP errors fail without a lookup and without technicalities", async () => {
    const f = vi.fn().mockResolvedValue(fail(404));
    vi.stubGlobal("fetch", f);
    const r = await activatePlace(1);
    expect(r.kind).toBe("failed");
    if (r.kind === "failed") expect(r.message).not.toMatch(/404|GET|POST|api/i);
    expect(f).toHaveBeenCalledTimes(1);
  });
});
