import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { type ActiveLocation, DEFAULT_SETTINGS, type Settings } from "../lib/location";
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
  // Choosing a place finishes the onboarding as well.
  choose: (location: ActiveLocation) => void;
  // The remembered area is gone/unavailable: forget it (Welcome stays done), explain in the picker.
  // Ignored unless `geoAreaId` is still the chosen one (a late answer for a place the user has
  // already left must not wipe the new choice).
  invalidate: (geoAreaId: number, message: string) => void;
};

const Ctx = createContext<LocationContext | null>(null);

export function LocationProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadSettings().then((s) => {
      if (cancelled) return;
      setSettings(s);
      setReady(true);
      // Opening the app with a chosen place refreshes its activation TTL (ADR-029). Best effort:
      // the dashboard reads our database either way, a failure here changes nothing.
      if (s.location?.placeId != null) activatePlace(s.location.placeId).catch(() => undefined);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Persist every change after the first read (not before: that would overwrite the record).
  useEffect(() => {
    if (ready) void saveSettings(settings);
  }, [ready, settings]);

  // Latest settings for `invalidate`, whose callers (an older provider instance answering late)
  // may hold a stale closure.
  const current = useRef(settings);
  useEffect(() => {
    current.current = settings;
  }, [settings]);

  const choose = useCallback((location: ActiveLocation) => {
    setNotice(null);
    setSettings({ onboardingDone: true, location });
  }, []);

  const invalidate = useCallback((geoAreaId: number, message: string) => {
    if (current.current.location?.geoAreaId !== geoAreaId) return;
    setNotice(message);
    setSettings({ ...current.current, location: null });
  }, []);

  const value = useMemo(() => ({ ready, settings, notice, choose, invalidate }), [ready, settings, notice, choose, invalidate]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export default function useLocation(): LocationContext {
  const v = useContext(Ctx);
  if (!v) throw new Error("useLocation outside LocationProvider");
  return v;
}
