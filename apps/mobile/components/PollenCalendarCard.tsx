import { StyleSheet, Text } from "react-native";

import { pollenCalendarView } from "../lib/pollenCalendar";
import { type Theme, space, typo } from "../lib/theme";
import Card from "./Card";
import { useThemedStyles } from "./useTheme";

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
  const styles = useThemedStyles(createStyles);
  const view = pollenCalendarView(calendar);
  if (!view) {
    return error ? (
      <Card>
        <Text style={styles.title} accessibilityRole="header">
          Kalendarz pylenia
        </Text>
        <Text style={styles.error} accessibilityRole="alert">
          Kalendarz pylenia chwilowo niedostępny. Odśwież widok, aby spróbować ponownie.
        </Text>
      </Card>
    ) : null;
  }
  return (
    <Card>
      <Text style={styles.title} accessibilityRole="header">
        {view.title}
      </Text>
      <Text style={styles.kind}>
        {view.kindNote}
        {view.date ? ` Stan na ${view.date}.` : ""}
      </Text>
      {error && (
        <Text style={styles.error} accessibilityRole="alert">
          Nie udało się odświeżyć — pokazany kalendarz może być nieaktualny.
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
    </Card>
  );
}

// Colours come from the palettes, whose text pairs are contrast-tested (theme.test.ts).
const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.cardTitle, color: t.colors.text, marginBottom: space.xs },
    kind: { ...typo.caption, color: t.colors.textSecondary },
    sub: { ...typo.caption, fontWeight: "600", color: t.colors.textSecondary, paddingTop: 2 },
    line: { ...typo.body, color: t.colors.text },
    phase: { color: t.colors.warning },
    peak: { color: t.colors.danger, fontWeight: "700" },
    empty: { ...typo.body, color: t.colors.warning },
    error: { ...typo.caption, color: t.colors.danger },
    note: { ...typo.micro, color: t.colors.textSecondary },
  });
