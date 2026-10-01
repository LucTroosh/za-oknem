import { StyleSheet, Text, View } from "react-native";

import { pollenView } from "../app/pollen";

// TASK-8.8: one card per location. All wording/levels come from app/pollen.ts + the
// backend block; this only lays it out. Renders nothing when the backend sent no
// `pollen` (older backend). Always shows the attribution (ADR-020: CAMS + Open-Meteo).
const COLOR = { BELOW_SEASON: "#2e7d32", SEASON: "#8a5300", PEAK: "#b00020" } as const;

// null for an unparsable timestamp: never render "Invalid Date".
function format(iso: string | null, opts: Intl.DateTimeFormatOptions): string | null {
  if (iso === null || Number.isNaN(new Date(iso).getTime())) return null;
  return new Date(iso).toLocaleString("pl-PL", opts);
}

export default function PollenCard({ pollen }: { pollen: unknown }) {
  const view = pollenView(pollen);
  if (!view) return null;
  const fetched = format(view.fetchedAt, { dateStyle: "short", timeStyle: "short" });
  const validHour = format(view.validAt, { hour: "2-digit", minute: "2-digit" });
  return (
    <View style={styles.card}>
      <Text style={styles.title} accessibilityRole="header">
        {view.title}
      </Text>
      {view.status && (
        <Text style={view.state === "recent" ? styles.note : styles.status}>{view.status}</Text>
      )}
      {view.lines.map((line) => (
        <Text key={line.species} style={styles.line}>
          {line.name}:{" "}
          <Text style={line.level ? { color: COLOR[line.level] } : styles.note}>{line.text}</Text>
        </Text>
      ))}
      {view.lines.length > 0 && validHour && (
        <Text style={styles.note}>wartości na godz. {validHour}</Text>
      )}
      {fetched && <Text style={styles.note}>pobrano {fetched}</Text>}
      <Text style={styles.disclaimer}>{view.note}</Text>
      <Text style={styles.disclaimer}>{view.attribution}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { gap: 2, paddingTop: 4 },
  title: { fontSize: 16, fontWeight: "600" },
  line: { fontSize: 14 },
  status: { fontSize: 14, color: "#8a5300" },
  note: { fontSize: 12, color: "#666" },
  disclaimer: { fontSize: 11, color: "#595959" },
});
