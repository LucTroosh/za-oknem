import { StyleSheet, Text, View } from "react-native";

import { airIndexView } from "../lib/aqi";
import { type Theme, type Tone, radius, space, toneColors, typo } from "../lib/theme";
import useNow from "./useNow";
import useTheme, { useThemedStyles } from "./useTheme";

// TASK-4.2: one badge per air block. All wording comes from lib/aqi.ts + the backend
// block; this only lays it out. Renders nothing when the backend sent no `index`.
// The level is carried by glyph + word + colour (colour alone is never enough).
const TONE: Record<string, Tone> = { GOOD: "good", FAIR: "good", MODERATE: "warning" };

export default function AirIndexBadge({
  index,
  receivedAt,
}: {
  index: unknown;
  // Device time of the response, owned by the screen (see OutdoorCard).
  receivedAt: number;
}) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  // A mounted screen only re-renders on state changes, so tick to let the badge expire.
  const now = useNow();

  const view = airIndexView(index, now, receivedAt);
  if (!view) return null;
  const { fg, bg } = toneColors(colors, view.level === null ? "neutral" : (TONE[view.level] ?? "danger"));
  return (
    <View style={[styles.box, { backgroundColor: bg }]} accessible accessibilityLabel={[view.headline, view.step !== null ? `poziom ${view.step} z 6` : null, view.detail].filter(Boolean).join(", ")}>
      <Text style={[styles.headline, { color: fg }]}>
        {view.icon} {view.headline}
        {view.step !== null ? ` (${view.step}/6)` : ""}
      </Text>
      {view.detail && <Text style={styles.detail}>{view.detail}</Text>}
      {view.note && <Text style={styles.note}>{view.note}</Text>}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    box: { gap: 2, padding: space.md, borderRadius: radius.sm, marginBottom: space.sm },
    headline: { ...typo.strong },
    detail: { ...typo.body, color: t.colors.text },
    note: { ...typo.micro, color: t.colors.textSecondary },
  });
