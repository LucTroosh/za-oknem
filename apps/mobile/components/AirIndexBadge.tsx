import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { airIndexView } from "../app/aqi";

// TASK-4.2: one badge per air block. All wording comes from app/aqi.ts + the backend
// block; this only lays it out. Renders nothing when the backend sent no `index`.
const COLOR = { GOOD: "#2e7d32", FAIR: "#2e7d32", MODERATE: "#b26a00" } as const;

export default function AirIndexBadge({
  index,
  receivedAt,
}: {
  index: unknown;
  // Device time of the response, owned by the screen (see OutdoorCard).
  receivedAt: number;
}) {
  // A mounted screen only re-renders on state changes, so tick to let the badge expire.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const view = airIndexView(index, now, receivedAt);
  if (!view) return null;
  const color = view.level === null ? "#666" : (COLOR[view.level as keyof typeof COLOR] ?? "#b00020");
  return (
    <View style={styles.box}>
      <Text style={[styles.headline, { color }]}>
        {view.icon} {view.headline}
        {view.step !== null ? ` (${view.step}/6)` : ""}
      </Text>
      {view.detail && <Text style={styles.detail}>{view.detail}</Text>}
      {view.note && <Text style={styles.note}>{view.note}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  box: { gap: 2, paddingTop: 4 },
  headline: { fontSize: 16, fontWeight: "600" },
  detail: { fontSize: 14 },
  note: { fontSize: 10, color: "#999" },
});
