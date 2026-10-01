import { useEffect, useState } from "react";

import { apiGet } from "../app/api";
import type { HydroBlock } from "../app/hydro";
import type { LoadState } from "../app/dashboardTypes";

// TASK-7.2 (hydro): separate fetch (hydrology isn't part of the dashboard aggregate, §55),
// so its failure never touches the rest of the app and vice versa (rule #1). `refreshTick`
// = pull-to-refresh. A failed refresh keeps the previous data; the section shows both.
export default function useHydro(refreshTick: number) {
  const [state, setState] = useState<LoadState>("loading");
  const [hydro, setHydro] = useState<HydroBlock | null>(null);
  useEffect(() => {
    let cancelled = false;
    apiGet<HydroBlock>("/api/v1/hydro/latest")
      .then((body) => {
        if (cancelled) return;
        setHydro(body);
        setState("ready");
      })
      .catch(() => !cancelled && setState("error"));
    return () => {
      cancelled = true;
    };
  }, [refreshTick]);
  return { state, hydro };
}
