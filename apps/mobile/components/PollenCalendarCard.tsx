import { StyleSheet, Text, View } from "react-native";

import { pollenCalendarView } from "../app/pollenCalendar";

// TASK-8.10 (UI) / ADR-023: typical pollen season. Visibly separate from the CAMS forecast
// card (PollenCard). All wording comes from app/pollenCalendar.ts + the backend block.
// `calendar` null = not loaded yet (renders nothing); `error` = this section only failed.
export default function PollenCalendarCard({
  calendar,
  error,
}: {
  calendar: unknown;
  error: boolean;
}) {
  const view = pollenCalendarView(calendar);
  if (!view) {
    return error ? (
      <View style={styles.card}>
        <Text style={styles.title} accessibilityRole="header">
          Kalendarz pylenia
        </Text>
        <Text style={styles.error} accessibilityRole="alert">
          Kalendarz pylenia chwilowo niedostępny — pociągnij w dół, aby spróbować ponownie.
        </Text>
      </View>
    ) : null;
  }
  return (
    <View style={styles.card}>
      <Text style={styles.title} accessibilityRole="header">
        {view.title}
      </Text>
      <Text style={styles.kind}>
        {view.kindNote}
        {view.date ? ` Stan na ${view.date}.` : ""}
      </Text>
      {error && (
        <Text style={styles.error} accessibilityRole="alert">
          Błąd odświeżania — pokazany kalendarz może być nieaktualny.
        </Text>
      )}
      {view.emptyMessage && <Text style={styles.empty}>{view.emptyMessage}</Text>}
      {view.active.map((t) => (
        <Text key={t.key} style={styles.line}>
          {t.name}: <Text style={t.phase === "peak" ? styles.peak : styles.phase}>{t.phaseText}</Text>
          {[t.range, t.peakRange].filter(Boolean).map((s) => ` · ${s}`)}
        </Text>
      ))}
      {view.upcoming.length > 0 && <Text style={styles.sub}>Nadchodzące</Text>}
      {view.upcoming.map((t) => (
        <Text key={t.key} style={styles.line}>
          {t.name}: {t.text}
        </Text>
      ))}
      {view.notCovered && <Text style={styles.note}>{view.notCovered}</Text>}
      <Text style={styles.note}>{view.coverageWarning}</Text>
      <Text style={styles.note}>{view.disclaimer}</Text>
      <Text style={styles.note}>{view.attribution}</Text>
    </View>
  );
}

// Text colours >= 4.5:1 on white (#595959 7.0, #8a5300 6.6, #b00020 7.1).
const styles = StyleSheet.create({
  card: { gap: 2, paddingTop: 4 },
  title: { fontSize: 16, fontWeight: "600" },
  kind: { fontSize: 12, color: "#595959" },
  sub: { fontSize: 13, fontWeight: "600", color: "#595959", paddingTop: 2 },
  line: { fontSize: 14 },
  phase: { color: "#8a5300" },
  peak: { color: "#b00020", fontWeight: "700" },
  empty: { fontSize: 14, color: "#8a5300" },
  error: { fontSize: 13, color: "#b00020" },
  note: { fontSize: 11, color: "#595959" },
});
