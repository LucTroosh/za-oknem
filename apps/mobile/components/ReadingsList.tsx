import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { NO_DATA, type ReadingLine, type ReadingsView } from "../lib/readings";
import { type Theme, space, typo } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// TASK-7.3: shared layout for air and weather lines. A stale line is dimmed and
// carries its age; a missing one says "brak danych". Wording comes from app/readings.ts.
function Line({ line }: { line: ReadingLine }) {
  const styles = useThemedStyles(createStyles);
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
  lead,
}: {
  title: string;
  view: ReadingsView | null;
  emptyText: string;
  unavailableText: string;
  // Summary shown right under the title (e.g. the AQI badge), above the detail lines.
  lead?: ReactNode;
}) {
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.box}>
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      {lead}
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

const createStyles = (t: Theme) =>
  StyleSheet.create({
    box: { gap: space.xs },
    title: { ...typo.heading, color: t.colors.text, marginBottom: space.xs },
    line: { ...typo.body, color: t.colors.text },
    dim: { color: t.colors.dim },
    note: { ...typo.caption, color: t.colors.textSecondary },
    warn: { ...typo.caption, color: t.colors.warning, fontWeight: "600" },
    attribution: { ...typo.micro, color: t.colors.textSecondary, marginTop: space.xs },
  });
