import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { type ActiveLocation, DEFAULT_SETTINGS, type Settings, dropLocationIf, locationFromPlace, refreshLocation } from "../lib/location";
import { activatePlace } from "../lib/places";
import { loadSettings, saveSettings } from "../lib/storage";

// The remembered location + onboarding flag for the whole app (spec §3: ONE location, local to
// the device, no account). `ready` = the stored record has been read (the root shows nothing
// until then, so a returning user never flashes Welcome).
export type LocationContext = {
  ready: boolean;
  settings: Settings;
  // Message for the picker after the remembered place stopped being available.
  notice: string | null;
  // Count of successful activations of the remembered place at app start (see below).
  activations: number;
  // The Welcome CTA was pressed in this run (memory only): the first run may enter the picker.
  welcomeSeen: boolean;
  startOnboarding: () => void;
  // Choosing a place finishes the onboarding as well.
  choose: (location: ActiveLocation) => void;
  // The remembered area is gone/unavailable: forget it (Welcome stays done), explain in the picker.
  // Ignored unless `geoAreaId` is still the chosen one (a late answer for a place the user has
  // already left must not wipe the new choice).
  invalidate: (geoAreaId: number, message: string) => void;
};

const Ctx = createContext<LocationContext | null>(null);

type State = { ready: boolean; settings: Settings; notice: string | null };

export function LocationProvider({ children }: { children: ReactNode }) {
  const [{ ready, settings, notice }, setState] = useState<State>({ ready: false, settings: DEFAULT_SETTINGS, notice: null });
  // Bumped when the activation of the remembered place succeeded: the dashboard read that raced
  // with it may have seen the not-yet-reactivated area, so it reloads (DashboardProvider).
  const [activations, setActivations] = useState(0);
  const [welcomeSeen, setWelcomeSeen] = useState(false);
  const startOnboarding = useCallback(() => setWelcomeSeen(true), []);

  useEffect(() => {
    let cancelled = false;
    loadSettings().then((s) => {
      if (cancelled) return;
      setState((cur) => ({ ...cur, ready: true, settings: s }));
      // Opening the app with a chosen place refreshes its activation TTL (ADR-029). Best effort:
      // the dashboard reads our database either way, a failure here changes nothing.
      const placeId = s.location?.placeId;
      if (placeId != null) {
        activatePlace(placeId)
          .then((r) => {
            if (cancelled || r.kind !== "proceed") return;
            // The answer is the authority: refresh name / label / area id before the reload.
            const next = locationFromPlace(r.place, r.area, r.attribution);
            setState((cur) => {
              const settings = refreshLocation(cur.settings, placeId, next);
              return settings === cur.settings ? cur : { ...cur, settings };
            });
            setActivations((n) => n + 1);
          })
          .catch(() => undefined);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Persist every change after the first read (not before: that would overwrite the record).
  useEffect(() => {
    if (ready) void saveSettings(settings);
  }, [ready, settings]);

  const choose = useCallback((location: ActiveLocation) => {
    setState((cur) => ({ ...cur, settings: { onboardingDone: true, location }, notice: null }));
  }, []);

  // The check runs inside the updater, against React's latest state: a late answer for a place
  // the user has already left finds another location and changes nothing.
  const invalidate = useCallback((geoAreaId: number, message: string) => {
    setState((cur) => {
      const next = dropLocationIf(cur.settings, geoAreaId);
      return next === cur.settings ? cur : { ...cur, settings: next, notice: message };
    });
  }, []);

  const value = useMemo(
    () => ({ ready, settings, notice, activations, welcomeSeen, startOnboarding, choose, invalidate }),
    [ready, settings, notice, activations, welcomeSeen, startOnboarding, choose, invalidate],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export default function useLocation(): LocationContext {
  const v = useContext(Ctx);
  if (!v) throw new Error("useLocation outside LocationProvider");
  return v;
}
