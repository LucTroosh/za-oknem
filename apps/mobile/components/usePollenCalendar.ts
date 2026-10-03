import { useEffect, useState } from "react";

import { apiGet } from "../lib/api";
import type { PollenCalendarBlock } from "../lib/pollenCalendar";

// Own fetch, own state: the calendar failing (or being offline) must never touch the rest
// of the screen (rule #1). Goes through our backend only (rule #14). `refreshTick` = pull-to-refresh;
// `day` = the device's current day: the calendar is per day, so a new day fetches it again.
// A failed refresh keeps the previous data; the card shows its date and the error.
export default function usePollenCalendar(refreshTick: number, day: string) {
  const [data, setData] = useState<PollenCalendarBlock | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let cancelled = false;
    apiGet<PollenCalendarBlock>("/api/v1/pollen/calendar")
      .then((body) => {
        if (cancelled) return;
        setData(body);
        setError(false);
      })
      .catch(() => !cancelled && setError(true));
    return () => {
      cancelled = true;
    };
  }, [refreshTick, day]);
  return { data, error };
}
