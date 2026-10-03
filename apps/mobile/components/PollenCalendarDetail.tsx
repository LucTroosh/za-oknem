import { StyleSheet, Text, View } from "react-native";

import { CALENDAR_HOW_INTRO, CALENDAR_HOW_TITLE, formatDay, pollenCalendarView } from "../lib/pollenCalendar";
import { type Theme, space, typo } from "../lib/theme";
import Card from "./Card";
import SectionHeader from "./SectionHeader";
import { useThemedStyles } from "./useTheme";

// The details behind the dashboard card (TASK-8.10 / ADR-023): periods per allergen, what is
// coming, how the calendar works, what it does not cover, and the source. All of it comes from the
// same view model as before (lib/pollenCalendar.ts) - the redesign only moved it off the dashboard.
export default function PollenCalendarDetail({ calendar, error }: { calendar: unknown; error: boolean }) {
  const styles = useThemedStyles(createStyles);
  const view = pollenCalendarView(calendar);
  if (!view) {
    return error ? (
      <Card>
        <Text style={styles.error} accessibilityRole="alert">
          Kalendarz sezonów chwilowo niedostępny. Odśwież widok, aby spróbować ponownie.
        </Text>
      </Card>
    ) : null;
  }
  return (
    <>
      {error && (
        <Text style={styles.error} accessibilityRole="alert">
          Nie udało się odświeżyć — pokazany kalendarz może być nieaktualny.
        </Text>
      )}
      <View style={styles.block}>
        <SectionHeader title="Teraz w typowym sezonie" />
        <Card>
          {formatDay(view.date) && <Text style={styles.caption}>Stan na {formatDay(view.date)}.</Text>}
          {view.active.length === 0 ? (
            <Text style={styles.body}>Żaden z ujętych alergenów nie jest teraz w typowym sezonie.</Text>
          ) : (
            view.active.map((t) => (
              <View key={t.key} style={styles.item}>
                <Text style={styles.body}>
                  <Text style={styles.name}>{t.name}</Text> — <Text style={t.phase === "peak" ? styles.peak : null}>{t.phaseText}</Text>
                </Text>
                {[t.range, t.peakRange].filter(Boolean).map((line) => (
                  <Text key={line} style={styles.caption}>
                    {line}
                  </Text>
                ))}
              </View>
            ))
          )}
        </Card>
      </View>

      {view.upcoming.length > 0 && (
        <View style={styles.block}>
          <SectionHeader title="Nadchodzące" />
          <Card>
            {view.upcoming.map((t) => (
              <Text key={t.key} style={styles.body}>
                <Text style={styles.name}>{t.name}</Text> — {t.text}
              </Text>
            ))}
          </Card>
        </View>
      )}

      <View style={styles.block}>
        <SectionHeader title={CALENDAR_HOW_TITLE} />
        <Card>
          <Text style={styles.body}>{CALENDAR_HOW_INTRO}</Text>
          {view.emptyMessage && <Text style={styles.caption}>{view.emptyMessage}</Text>}
          {view.notCovered && <Text style={styles.caption}>{view.notCovered}</Text>}
          <Text style={styles.caption}>{view.coverageWarning}</Text>
          <Text style={styles.caption}>{view.disclaimer}</Text>
        </Card>
      </View>

      <Text style={styles.source}>{view.attribution}</Text>
    </>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    block: { gap: space.md },
    item: { gap: 2 },
    body: { ...typo.body, color: t.colors.text },
    name: { fontWeight: "700" },
    peak: { fontWeight: "700" },
    caption: { ...typo.caption, color: t.colors.textSecondary },
    error: { ...typo.caption, color: t.colors.danger },
    source: { ...typo.meta, color: t.colors.textSecondary },
  });
