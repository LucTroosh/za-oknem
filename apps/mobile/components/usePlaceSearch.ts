import { useEffect, useState } from "react";

import type { PlaceOut, PlacesResponse } from "../../../packages/api-contract/schema";
import { apiGet } from "../lib/api";
import { DEBOUNCE_MS, debounce, placesPath, searchQuery } from "../lib/places";

export type PlaceSearch =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; query: string; places: PlaceOut[]; attribution: string | null };

// Search-as-you-type against our own GET /api/v1/places: >= 2 characters, 300 ms debounce, and
// latest wins - every new input (or retry) aborts the previous request, and an aborted one can
// never set state. `retry` is a counter the screen bumps for "Spróbuj ponownie".
export default function usePlaceSearch(raw: string, retry: number): PlaceSearch {
  const [state, setState] = useState<PlaceSearch>({ status: "idle" });

  useEffect(() => {
    const q = searchQuery(raw);
    if (q === null) {
      setState({ status: "idle" });
      return;
    }
    setState({ status: "loading" });
    const ctrl = new AbortController();
    const run = debounce(() => {
      apiGet<PlacesResponse>(placesPath(q), ctrl.signal)
        .then((r) => {
          if (!ctrl.signal.aborted) setState({ status: "ready", query: q, places: r.places, attribution: r.attribution || null });
        })
        .catch(() => {
          if (!ctrl.signal.aborted) setState({ status: "error" });
        });
    }, DEBOUNCE_MS);
    run.call();
    return () => {
      run.cancel();
      ctrl.abort();
    };
  }, [raw, retry]);

  return state;
}
