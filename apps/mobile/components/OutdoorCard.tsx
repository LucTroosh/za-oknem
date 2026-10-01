import { StyleSheet, Text, View } from "react-native";

import { OUTDOOR_DISCLAIMER, type OutdoorLevel, outdoorView } from "../app/outdoor";
import { type Theme, type Tone, radius, space, toneColors, typo } from "../app/theme";
import useNow from "./useNow";
import useTheme, { useThemedStyles } from "./useTheme";

// TASK-7.8: the verdict "na dwór" - the first and largest thing on Home. All wording and
// classification comes from app/outdoor.ts + the backend block; this only lays it out.
// Renders nothing when the backend sent no `outdoor` (older backend). Level = glyph + word
// + tint + side band; colour is never the only carrier.
const TONE: Record<OutdoorLevel, Tone> = { GOOD: "good", MODERATE: "warning", POOR: "danger", UNKNOWN: "neutral" };

export default function OutdoorCard({
  outdoor,
  receivedAt,
}: {
  outdoor: unknown;
  // Device time of the response, owned by the screen (a list row remounting on
  // scroll must not reset the age of an old verdict).
  receivedAt: number;
}) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  // The response is aged on the device clock: a mounted screen only re-renders on state changes.
  const view = outdoorView(outdoor, useNow(), receivedAt);
  if (!view) return null;
  const { fg, bg } = toneColors(colors, TONE[view.level]);
  return (
    <View
      style={[styles.card, { backgroundColor: bg, borderLeftColor: fg }]}
      accessible
      accessibilityLabel={`Na dwór: ${view.headline}. ${view.reasonLines.join(". ")}`}
    >
      <Text style={styles.kicker}>Na dwór</Text>
      <View style={styles.headRow}>
        <Text style={[styles.icon, { color: fg }]} importantForAccessibility="no" accessibilityElementsHidden>
          {view.icon}
        </Text>
        <Text style={[styles.headline, { color: fg }]}>{view.headline}</Text>
      </View>
      {view.reasonLines.map((line) => (
        <Text key={line} style={styles.line}>
          {line}
        </Text>
      ))}
      {view.missingLine && <Text style={styles.note}>{view.missingLine}</Text>}
      <Text style={styles.note}>{OUTDOOR_DISCLAIMER}</Text>
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    card: {
      gap: space.xs,
      padding: space.lg,
      borderRadius: radius.lg,
      borderLeftWidth: 6,
    },
    kicker: { ...typo.caption, color: t.colors.textSecondary, fontWeight: "600" },
    headRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
    icon: { ...typo.display },
    headline: { ...typo.display, flexShrink: 1 },
    line: { ...typo.body, color: t.colors.text },
    note: { ...typo.caption, color: t.colors.textSecondary },
  });
