import { useEffect, useState } from "react";

import { apiGet } from "../lib/api";
import { type NeighborhoodBlock, neighborhoodView } from "../lib/neighborhood";

export type NeighborhoodState = { block: NeighborhoodBlock | null; status: "loading" | "ok" | "error" };

// Own fetch, own state (rule #1): "Twoja okolica" failing must never touch the rest of Start. Goes
// through our backend only (rule #14). A failed refresh keeps the previous block; a backend without
// the module (404 / odd body) simply yields no block, so the entry stays hidden.
export default function useNeighborhood(geoAreaId: number, refreshTick: number): NeighborhoodState {
  const [state, setState] = useState<NeighborhoodState>({ block: null, status: "loading" });
  useEffect(() => {
    let cancelled = false;
    apiGet<unknown>(`/api/v1/neighborhood?geo_area_id=${geoAreaId}`)
      .then((body) => !cancelled && setState({ block: neighborhoodView(body), status: "ok" }))
      .catch(() => !cancelled && setState((s) => ({ block: s.block, status: "error" })));
    return () => {
      cancelled = true;
    };
  }, [geoAreaId, refreshTick]);
  return state;
}
