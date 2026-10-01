import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import type { DashboardResponse } from "../../../packages/api-contract/schema";
import type { AlertsBlock } from "../lib/alerts";
import { apiGet } from "../lib/api";
import type { DashboardArea, DashboardSourceStatus, LoadState } from "../lib/dashboardTypes";
import type { HydroBlock } from "../lib/hydro";
import { createLatestGuard } from "../lib/latest";
import type { PollenCalendarBlock } from "../lib/pollenCalendar";
import usePollenCalendar from "./usePollenCalendar";

// The shared data of the tabs, each from its own request (rule #1: one failing never blanks
// another) and only from our backend (rule #14):
//   /api/v1/dashboard/latest -> areas (Home), alerts (Alerts + Home banner), attributions
//   /api/v1/hydro/latest     -> water levels (Alerts + Home banner)
//   /api/v1/pollen/calendar  -> typical pollen season (Home, attribution in Settings)
// A failed refresh keeps the previous data and flips the state to "error", so screens can
// show both. Responses of superseded requests are ignored (latest wins).
export type DashboardContext = {
  state: LoadState;
  dashboard: DashboardResponse | null;
  areas: DashboardArea[];
  alerts: AlertsBlock | null;
  sourceStatus: DashboardSourceStatus | null;
  hydroState: LoadState;
  hydro: HydroBlock | null;
  calendar: PollenCalendarBlock | null;
  calendarError: boolean;
  // Device time of the last successful dashboard response (ages the outdoor verdict and AQI).
  loadedAt: number;
  refreshing: boolean;
  refresh: () => void;
};

const Ctx = createContext<DashboardContext | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LoadState>("loading");
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [hydroState, setHydroState] = useState<LoadState>("loading");
  const [hydro, setHydro] = useState<HydroBlock | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loadedAt, setLoadedAt] = useState(() => Date.now());
  const [refreshTick, setRefreshTick] = useState(0);
  const calendar = usePollenCalendar(refreshTick);
  const guards = useRef({ dashboard: createLatestGuard(), hydro: createLatestGuard(), refresh: createLatestGuard() });

  const loadDashboard = useCallback(() => {
    const isLatest = guards.current.dashboard();
    return apiGet<DashboardResponse>("/api/v1/dashboard/latest")
      .then((body) => {
        if (!isLatest()) return;
        setDashboard(body);
        setLoadedAt(Date.now());
        setState("ready");
      })
      .catch(() => isLatest() && setState("error"));
  }, []);

  const loadHydro = useCallback(() => {
    const isLatest = guards.current.hydro();
    return apiGet<HydroBlock>("/api/v1/hydro/latest")
      .then((body) => {
        if (!isLatest()) return;
        setHydro(body);
        setHydroState("ready");
      })
      .catch(() => isLatest() && setHydroState("error"));
  }, []);

  useEffect(() => {
    loadDashboard();
    loadHydro();
  }, [loadDashboard, loadHydro]);

  const refresh = useCallback(() => {
    const isLatest = guards.current.refresh();
    setRefreshTick((t) => t + 1);
    setRefreshing(true);
    // Both loaders swallow their errors, so this always settles; only the newest pull
    // switches the spinner off.
    Promise.all([loadDashboard(), loadHydro()]).finally(() => isLatest() && setRefreshing(false));
  }, [loadDashboard, loadHydro]);

  const value = useMemo<DashboardContext>(
    () => ({
      state,
      dashboard,
      areas: dashboard?.areas ?? [],
      alerts: dashboard?.alerts ?? null,
      // `?? null`: an older backend may omit it (runtime only; the contract says required).
      sourceStatus: dashboard?.source_status ?? null,
      hydroState,
      hydro,
      calendar: calendar.data,
      calendarError: calendar.error,
      loadedAt,
      refreshing,
      refresh,
    }),
    [state, dashboard, hydroState, hydro, calendar.data, calendar.error, loadedAt, refreshing, refresh],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export default function useDashboard(): DashboardContext {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDashboard outside DashboardProvider");
  return v;
}
