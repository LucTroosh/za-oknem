import { describe, expect, it, vi } from "vitest";

import { type NavRouter, applyNavStep, backFromLocation, finishLocation, locationMode, showLocationBack } from "./navigation";

const fakeRouter = (canDismiss = true) => {
  const calls: string[] = [];
  const router: NavRouter = {
    back: vi.fn(() => void calls.push("back")),
    replace: vi.fn((href) => void calls.push(`replace:${href}`)),
    dismissAll: vi.fn(() => void calls.push("dismissAll")),
    canDismiss: () => canDismiss,
  };
  return { router, calls };
};

describe("locationMode", () => {
  it("is first-run until onboarding is done", () => {
    expect(locationMode({ onboardingDone: false })).toBe("first-run");
    expect(locationMode({ onboardingDone: true })).toBe("change");
  });
});

describe("first run: Welcome -> Location -> Start", () => {
  it("Back from Location returns to Welcome (header and Android back both pop the pushed screen)", () => {
    const step = backFromLocation("first-run", true);
    expect(step).toEqual({ kind: "back" });
    const { router, calls } = fakeRouter();
    applyNavStep(router, step);
    expect(calls).toEqual(["back"]);
  });
  it("without history (restored process) Back still lands on Welcome, never on Start", () => {
    expect(backFromLocation("first-run", false)).toEqual({ kind: "replace", href: "/welcome" });
  });
  it("the Back affordance is always offered on the first run", () => {
    expect(showLocationBack("first-run", false)).toBe(true);
    expect(showLocationBack("first-run", true)).toBe(true);
  });
  it("choosing a location clears the onboarding history, then opens Start: Back from Start has nothing to return to", () => {
    const step = finishLocation("first-run", true);
    expect(step).toEqual({ kind: "reset-to-start" });
    const { router, calls } = fakeRouter();
    applyNavStep(router, step);
    expect(calls).toEqual(["dismissAll", "replace:/"]); // order matters: pop first, then replace the root
  });
  it("reset works when there is nothing to dismiss", () => {
    const { router, calls } = fakeRouter(false);
    applyNavStep(router, finishLocation("first-run", false));
    expect(calls).toEqual(["replace:/"]);
  });
});

describe("change location (from Start or Settings)", () => {
  it("Back and 'done' return to the screen the user came from", () => {
    expect(backFromLocation("change", true)).toEqual({ kind: "back" });
    expect(finishLocation("change", true)).toEqual({ kind: "back" });
    const { router, calls } = fakeRouter();
    applyNavStep(router, finishLocation("change", true));
    expect(calls).toEqual(["back"]); // no history reset: Start / Settings stay underneath
  });
  it("opened without history (deep link) it falls back to Start", () => {
    expect(backFromLocation("change", false)).toEqual({ kind: "replace", href: "/" });
    expect(finishLocation("change", false)).toEqual({ kind: "replace", href: "/" });
  });
  it("a forced picker with nowhere to go shows no Back", () => {
    expect(showLocationBack("change", false)).toBe(false);
    expect(showLocationBack("change", true)).toBe(true);
  });
});
