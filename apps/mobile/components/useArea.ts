import { useMemo } from "react";

import type { DashboardArea } from "../lib/dashboardTypes";
import { selectArea } from "../lib/home";
import useDashboard from "./DashboardProvider";
import useLocation from "./LocationProvider";

// The chosen area of the shared dashboard response (null while loading / when it has none).
export default function useArea(): DashboardArea | null {
  const d = useDashboard();
  const { settings } = useLocation();
  const id = settings.location?.geoAreaId;
  return useMemo(() => (id === undefined ? null : selectArea(d.areas, id)), [d.areas, id]);
}
