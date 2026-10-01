import { StyleSheet, Text, View } from "react-native";

import { NO_DATA, type ReadingLine, type ReadingsView } from "../app/readings";

// TASK-7.3: shared layout for air and weather lines. A stale line is dimmed and
// carries its age; a missing one says "brak danych". Wording comes from app/readings.ts.
function Line({ line }: { line: ReadingLine }) {
  const dim = line.state === "stale" || line.state === "missing";
  return (
    <Text style={[styles.line, dim && styles.dim]}>
      {line.label}: {line.state === "stale" ? "ostatnio " : ""}
      {line.text}
      {line.note && <Text style={styles.note}> ({line.note})</Text>}
    </Text>
  );
}

export default function ReadingsList({
  title,
  view,
  emptyText,
  unavailableText,
}: {
  title: string;
  view: ReadingsView | null;
  emptyText: string;
  unavailableText: string;
}) {
  return (
    <View style={styles.box}>
      <Text style={styles.title}>{title}</Text>
      {view === null && <Text style={[styles.line, styles.dim]}>{emptyText}</Text>}
      {view?.unavailable && <Text style={[styles.line, styles.dim]}>{unavailableText}</Text>}
      {view?.sourceNote && <Text style={styles.warn}>{view.sourceNote}</Text>}
      {view && !view.unavailable && view.lines.length === 0 && (
        <Text style={[styles.line, styles.dim]}>{NO_DATA}</Text>
      )}
      {view?.lines.map((line) => (
        <Line key={line.key} line={line} />
      ))}
      {view?.attribution && <Text style={styles.attribution}>{view.attribution}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  box: { gap: 2 },
  title: { fontSize: 14, fontWeight: "600" },
  line: { fontSize: 14 },
  dim: { color: "#8a8a8a" },
  note: { fontSize: 12, color: "#666" },
  warn: { fontSize: 12, color: "#8a5300" },
  attribution: { fontSize: 10, color: "#999" },
});
