import { useEffect, useState } from "react";

// Device clock, ticking every minute: a mounted screen only re-renders on state
// changes, so age labels would otherwise freeze while the screen stays open.
export default function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);
  return now;
}
