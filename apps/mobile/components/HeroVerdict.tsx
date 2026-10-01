import { StyleSheet, Text, View } from "react-native";

import { type VerdictModel } from "../lib/home";
import { OUTDOOR_DISCLAIMER } from "../lib/outdoor";
import { type Theme, radius, space, toneColors, typo } from "../lib/theme";
import StatusGlyph, { GLYPH_TONE } from "./StatusGlyph";
import useTheme, { useThemedStyles } from "./useTheme";

// Spec §11: the first thing on Start. LIVE verdict from the backend block (never a mock);
// glyph + word + tint, colour is never the only carrier. No arrow: there is no details
// screen yet (a tappable hero without a destination would be a dead control).
export default function HeroVerdict({ verdict }: { verdict: VerdictModel }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const { fg, bg } = toneColors(colors, GLYPH_TONE[verdict.level]);
  return (
    <View
      style={[styles.card, { backgroundColor: bg, borderLeftColor: fg }]}
      accessible
      accessibilityLabel={[verdict.headline, ...verdict.lines, verdict.note].filter(Boolean).join(". ")}
    >
      <View style={styles.head}>
        <StatusGlyph level={verdict.level} size={32} />
        <Text style={[styles.headline, { color: fg }]}>{verdict.headline}</Text>
      </View>
      {verdict.lines.map((line) => (
        <Text key={line} style={styles.line}>
          {line}
        </Text>
      ))}
      {verdict.note && <Text style={styles.note}>{verdict.note}</Text>}
      <Text style={styles.note}>{OUTDOOR_DISCLAIMER}</Text>
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    card: { gap: space.xs, padding: space.lg, borderRadius: radius.lg, borderLeftWidth: 6 },
    head: { flexDirection: "row", alignItems: "center", gap: space.sm },
    headline: { ...typo.title, flexShrink: 1 },
    line: { ...typo.body, color: t.colors.text },
    note: { ...typo.caption, color: t.colors.textSecondary },
  });
