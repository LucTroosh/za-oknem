import type { Settings } from "./location";

// Navigation plan of the location picker (production UI v1: Welcome -> Location -> Start).
// Pure decisions here, executed by `applyNavStep`, so both cases are testable without a router:
//  - first run: Welcome is PUSHED under Location, so Back (header or Android) returns to Welcome;
//    finishing wipes the onboarding history, so Back from Start never leads to Location/Welcome.
//  - change (opened from Start / Settings): Back and "done" return to where the user came from.
export type LocationMode = "first-run" | "change";

export const locationMode = (s: Pick<Settings, "onboardingDone">): LocationMode => (s.onboardingDone ? "change" : "first-run");

export type NavStep =
  | { kind: "back" }
  | { kind: "replace"; href: "/" | "/welcome" }
  // Pop the whole stack (Welcome, Location), then make Start the only screen.
  | { kind: "reset-to-start" };

// Header "Wstecz" / system back from the picker.
export function backFromLocation(mode: LocationMode, canGoBack: boolean): NavStep {
  if (canGoBack) return { kind: "back" };
  return { kind: "replace", href: mode === "first-run" ? "/welcome" : "/" };
}

// A location was chosen.
export function finishLocation(mode: LocationMode, canGoBack: boolean): NavStep {
  if (mode === "first-run") return { kind: "reset-to-start" };
  return canGoBack ? { kind: "back" } : { kind: "replace", href: "/" };
}

// Whether the picker offers Back: always on the first run (Welcome is behind it), later only when
// there is somewhere to return to (a forced picker without a stored location has nowhere to go).
export const showLocationBack = (mode: LocationMode, canGoBack: boolean): boolean => mode === "first-run" || canGoBack;

// The slice of expo-router's `router` the executor needs (kept narrow so tests can fake it).
export type NavRouter = {
  back: () => void;
  replace: (href: "/" | "/welcome") => void;
  dismissAll: () => void;
  canDismiss: () => boolean;
};

export function applyNavStep(router: NavRouter, step: NavStep): void {
  switch (step.kind) {
    case "back":
      router.back();
      return;
    case "replace":
      router.replace(step.href);
      return;
    case "reset-to-start":
      if (router.canDismiss()) router.dismissAll();
      router.replace("/");
      return;
  }
}
