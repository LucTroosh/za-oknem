import { Pressable, StyleSheet, Text, View } from "react-native";

import Ionicons from "@expo/vector-icons/Ionicons";

import { CALENDAR_CTA, type ForecastLevel, calendarDateNote, pollenCalendarView, seasonSummary } from "../lib/pollenCalendar";
import { MIN_TOUCH, type Theme, space, typo } from "../lib/theme";
import Card from "./Card";
import IconBox from "./IconBox";
import useNow from "./useNow";
import useTheme, { useThemedStyles } from "./useTheme";

// TASK-8.10 (UI) / ADR-023, redesigned: the dashboard shows ONE status of the typical pollen season,
// one sentence of context and a link to the details (period, method, limits, sources:
// PollenCalendarDetail). The calendar is background for the current forecast (PollenCard above),
// never a replacement for it (rule #7), so it only ever says "typical season" and, outside it,
// never that nothing pollinates. Wording: lib/pollenCalendar.ts (seasonSummary).
// `calendar` null = not loaded yet (renders nothing); `error` = this section only failed.
export default function PollenCalendarCard({
  calendar,
  error,
  forecast,
  onOpenCalendar,
}: {
  calendar: unknown;
  error: boolean;
  forecast: ForecastLevel;
  onOpenCalendar: () => void;
}) {
  const styles = useThemedStyles(createStyles);
  const { colors } = useTheme();
  const now = useNow();
  const view = pollenCalendarView(calendar);
  if (!view) {
    return error ? (
      <Card>
        <Text style={styles.error} accessibilityRole="alert">
          Typowy sezon pylenia chwilowo niedostępny. Odśwież widok, aby spróbować ponownie.
        </Text>
      </Card>
    ) : null;
  }
  const s = seasonSummary(view, forecast);
  const dateNote = calendarDateNote(view, now);
  const inSeason = s.state !== "out";
  return (
    <Card>
      {/* One announcement: status, what it means, how it relates to the forecast. */}
      <View style={styles.row} accessible accessibilityLabel={`${s.title}. ${s.text} ${s.context}`}>
        <IconBox
          name={s.icon}
          fg={inSeason ? colors.pollenFg : colors.textSecondary}
          bg={inSeason ? colors.pollenBg : colors.neutralBg}
          size={44}
          iconSize={24}
          rounded={14}
        />
        <View style={styles.texts}>
          <Text style={styles.title}>{s.title}</Text>
          <Text style={styles.text}>{s.text}</Text>
        </View>
      </View>
      <Text style={styles.context} accessible={false} importantForAccessibility="no">
        {s.context}
      </Text>
      {dateNote && <Text style={styles.context}>{dateNote}</Text>}
      {error && (
        <Text style={styles.error} accessibilityRole="alert">
          Nie udało się odświeżyć — pokazany sezon może być nieaktualny.
        </Text>
      )}
      <Pressable accessibilityRole="button" accessibilityLabel={CALENDAR_CTA} onPress={onOpenCalendar} hitSlop={8} style={styles.cta}>
        <Text style={styles.ctaText}>{CALENDAR_CTA}</Text>
        <Ionicons name="chevron-forward" size={16} color={colors.accent} importantForAccessibility="no" />
      </Pressable>
    </Card>
  );
}

// Colours come from the palettes, whose text pairs are contrast-tested (theme.test.ts).
const createStyles = (t: Theme) =>
  StyleSheet.create({
    row: { flexDirection: "row", alignItems: "center", gap: space.md },
    texts: { flex: 1, gap: 2 },
    title: { ...typo.heading, color: t.colors.text },
    text: { ...typo.supporting, color: t.colors.text },
    context: { ...typo.caption, color: t.colors.textSecondary },
    error: { ...typo.caption, color: t.colors.danger },
    cta: { minHeight: MIN_TOUCH, flexDirection: "row", alignItems: "center", gap: 2, alignSelf: "flex-start" },
    ctaText: { ...typo.meta, fontSize: 13, color: t.colors.accent, fontWeight: "600" },
  });
