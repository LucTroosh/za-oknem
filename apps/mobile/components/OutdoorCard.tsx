import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { OUTDOOR_DISCLAIMER, outdoorView } from "../app/outdoor";

// TASK-7.8: one card per location. All wording/classification comes from
// app/outdoor.ts + the backend block; this only lays it out. Renders nothing when
// the backend sent no `outdoor` (older backend).
export default function OutdoorCard({
  outdoor,
  receivedAt,
}: {
  outdoor: unknown;
  // Device time of the response, owned by the screen (a list row remounting on
  // scroll must not reset the age of an old verdict).
  receivedAt: number;
}) {
  // The response is aged on the device clock: a mounted screen only re-renders on
  // state changes, so tick.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const view = outdoorView(outdoor, now, receivedAt);
  if (!view) return null;
  return (
    <View style={styles.card}>
      <Text style={view.level === "POOR" ? styles.poor : view.level === "MODERATE" ? styles.moderate : styles.headline}>
        {view.icon} {view.headline}
      </Text>
      {view.reasonLines.map((line) => (
        <Text key={line} style={styles.line}>
          {line}
        </Text>
      ))}
      {view.missingLine && <Text style={styles.note}>{view.missingLine}</Text>}
      <Text style={styles.disclaimer}>{OUTDOOR_DISCLAIMER}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { gap: 2, paddingTop: 4 },
  headline: { fontSize: 16, fontWeight: "600" },
  moderate: { fontSize: 16, fontWeight: "600", color: "#b26a00" },
  poor: { fontSize: 16, fontWeight: "700", color: "#b00020" },
  line: { fontSize: 14 },
  note: { fontSize: 12, color: "#666" },
  disclaimer: { fontSize: 10, color: "#999" },
});
