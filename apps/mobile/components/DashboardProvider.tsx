import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { DashboardResponse } from "../../../packages/api-contract/schema";
import { apiGet } from "../app/api";
import type { AlertsBlock } from "../app/alerts";
import type { DashboardArea, DashboardSourceStatus, LoadState } from "../app/dashboardTypes";

// One fetch of /api/v1/dashboard/latest shared by the tabs (Home: areas, Alerts: national
// alerts, Settings: attributions). Reads only from our backend (rule #14). A failed refresh
// keeps the previous data and flips `state` to "error", so screens can show both.
export type DashboardContext = {
  state: LoadState;
  dashboard: DashboardResponse | null;
  areas: DashboardArea[];
  alerts: AlertsBlock | null;
  sourceStatus: DashboardSourceStatus | null;
  // Device time of the last successful response (ages the outdoor verdict and AQI).
  loadedAt: number;
  refreshing: boolean;
  // Bumped on every pull-to-refresh: the screens' own fetches (hydro, pollen calendar) follow it.
  refreshTick: number;
  refresh: () => void;
};

const Ctx = createContext<DashboardContext | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LoadState>("loading");
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loadedAt, setLoadedAt] = useState(() => Date.now());
  const [refreshTick, setRefreshTick] = useState(0);

  const load = useCallback(() => {
    return apiGet<DashboardResponse>("/api/v1/dashboard/latest")
      .then((body) => {
        setDashboard(body);
        setLoadedAt(Date.now());
        setState("ready");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const refresh = useCallback(() => {
    setRefreshTick((t) => t + 1);
    setRefreshing(true);
    load().finally(() => setRefreshing(false));
  }, [load]);

  const value = useMemo<DashboardContext>(
    () => ({
      state,
      dashboard,
      areas: dashboard?.areas ?? [],
      alerts: dashboard?.alerts ?? null,
      // `?? null`: an older backend may omit it (runtime only; the contract says required).
      sourceStatus: dashboard?.source_status ?? null,
      loadedAt,
      refreshing,
      refreshTick,
      refresh,
    }),
    [state, dashboard, loadedAt, refreshing, refreshTick, refresh],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export default function useDashboard(): DashboardContext {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDashboard outside DashboardProvider");
  return v;
}
