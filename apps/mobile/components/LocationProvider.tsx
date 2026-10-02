import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AppState } from "react-native";

import {
  type ActiveLocation,
  DEFAULT_SETTINGS,
  type Settings,
  dropLocationIf,
  locationFromPlace,
  refreshLocation,
  shouldReactivate,
} from "../lib/location";
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
  // Resolves when the activation started at app launch has finished (or failed / timed out).
  // A dashboard 404 for a place may only mean "not re-created yet": wait for this first.
  startupActivation: () => Promise<void>;
  // Choosing a place finishes the onboarding as well.
  choose: (location: ActiveLocation) => void;
  // The remembered area is gone/unavailable: forget it (Welcome stays done), explain in the picker.
  // Ignored unless `geoAreaId` is still the chosen one (a late answer for a place the user has
  // already left must not wipe the new choice).
  invalidate: (geoAreaId: number, message: string) => void;
};

const Ctx = createContext<LocationContext | null>(null);

type State = { ready: boolean; settings: Settings; notice: string | null };

const ACTIVATION_TIMEOUT_MS = 10_000;

export function LocationProvider({ children }: { children: ReactNode }) {
  const [{ ready, settings, notice }, setState] = useState<State>({ ready: false, settings: DEFAULT_SETTINGS, notice: null });
  // Bumped when an activation of the remembered place succeeded: the dashboard read that raced
  // with it may have seen the not-yet-reactivated area (DashboardProvider decides to reload).
  const [activations, setActivations] = useState(0);
  const [welcomeSeen, setWelcomeSeen] = useState(false);
  const startOnboarding = useCallback(() => setWelcomeSeen(true), []);
  // The settings object that came from storage: never written back as is (a failed or foreign
  // read returns defaults that must not overwrite a record that may still be there).
  const loaded = useRef<Settings | null>(null);
  const lastActivation = useRef<number | null>(null);
  const startup = useRef<Promise<void>>(Promise.resolve());

  // Activates the remembered place (TTL, ADR-029) and takes the answer as the authority on its
  // name / label / area id. Best effort with a timeout: a failure changes nothing.
  const reactivate = useCallback(async (placeId: number) => {
    lastActivation.current = Date.now();
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), ACTIVATION_TIMEOUT_MS);
    try {
      const r = await activatePlace(placeId, ctrl.signal);
      if (r.kind !== "proceed") return;
      const next = locationFromPlace(r.place, r.area, r.attribution);
      setState((cur) => {
        const settings = refreshLocation(cur.settings, placeId, next);
        return settings === cur.settings ? cur : { ...cur, settings };
      });
      setActivations((n) => n + 1);
    } catch {
      // aborted / offline: the dashboard reads our database either way
    } finally {
      clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadSettings().then(({ settings: s }) => {
      if (cancelled) return;
      loaded.current = s;
      const placeId = s.location?.placeId;
      // Set BEFORE `ready`: the dashboard provider mounts right after and may need it.
      if (placeId != null) startup.current = reactivate(placeId);
      setState((cur) => ({ ...cur, ready: true, settings: s }));
    });
    return () => {
      cancelled = true;
    };
  }, [reactivate]);

  // A long-open app: re-activate when it returns to the foreground, at most once per hour.
  const placeId = settings.location?.placeId ?? null;
  useEffect(() => {
    if (placeId === null) return;
    const sub = AppState.addEventListener("change", (st) => {
      if (st === "active" && shouldReactivate(lastActivation.current, Date.now())) void reactivate(placeId);
    });
    return () => sub.remove();
  }, [placeId, reactivate]);

  // Persist every deliberate change (not the object read from storage, see `loaded`).
  useEffect(() => {
    if (ready && settings !== loaded.current) void saveSettings(settings);
  }, [ready, settings]);

  const choose = useCallback((location: ActiveLocation) => {
    lastActivation.current = Date.now(); // the picker has just activated it
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

  const startupActivation = useCallback(() => startup.current, []);

  const value = useMemo(
    () => ({ ready, settings, notice, activations, welcomeSeen, startOnboarding, startupActivation, choose, invalidate }),
    [ready, settings, notice, activations, welcomeSeen, startOnboarding, startupActivation, choose, invalidate],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export default function useLocation(): LocationContext {
  const v = useContext(Ctx);
  if (!v) throw new Error("useLocation outside LocationProvider");
  return v;
}
