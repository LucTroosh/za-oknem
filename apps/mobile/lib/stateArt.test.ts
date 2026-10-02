import { describe, expect, it } from "vitest";

import { ApiError } from "./api";
import { alertsArt, isNetworkFailure, loadErrorArt, verdictArt } from "./stateArt";

describe("verdictArt", () => {
  it("maps verdict levels, UNKNOWN is no-data and never good", () => {
    expect(verdictArt("GOOD")).toBe("good");
    expect(verdictArt("CAUTION")).toBe("caution");
    expect(verdictArt("AVOID")).toBe("bad");
    expect(verdictArt("UNKNOWN")).toBe("noData");
  });
});

describe("alertsArt", () => {
  it("no-alerts only for a confirmed zero", () => {
    expect(alertsArt({ kind: "none-confirmed", sources: ["x"] })).toBe("noAlerts");
  });
  it("a zero from cached data after a failed refresh is not confirmed", () => {
    expect(alertsArt({ kind: "none-confirmed", sources: ["x"] }, true)).toBe("noData");
  });
  it("unknown, unavailable or missing block is no-data", () => {
    expect(alertsArt({ kind: "unavailable", lastSuccessAt: null })).toBe("noData");
    expect(alertsArt({ kind: "unavailable", lastSuccessAt: "2026-01-01T00:00:00Z" })).toBe("noData");
    expect(alertsArt(null)).toBe("noData");
  });
  it("a list has no illustration", () => {
    expect(alertsArt({ kind: "list" })).toBeNull();
    expect(alertsArt({ kind: "list-maybe-outdated", lastSuccessAt: null })).toBeNull();
  });
});

describe("network failure", () => {
  it("only a rejected fetch (TypeError) is offline", () => {
    expect(isNetworkFailure(new TypeError("Network request failed"))).toBe(true);
    expect(isNetworkFailure(new ApiError(503, "x"))).toBe(false);
    expect(isNetworkFailure(new DOMException("aborted", "AbortError"))).toBe(false);
    expect(isNetworkFailure("boom")).toBe(false);
  });
  it("picks offline vs no-data", () => {
    expect(loadErrorArt(true)).toBe("offline");
    expect(loadErrorArt(false)).toBe("noData");
  });
});
