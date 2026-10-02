import { StyleSheet, Text, View } from "react-native";

import { type Theme, type Tone, radius, space, toneColors, typo } from "../lib/theme";
import useTheme, { useThemedStyles } from "./useTheme";

// The real six-band EEA scale (production UI v1 §10): drawn only when an index is shown. The
// active band is spelled out in text ("Poziom 3 z 6"), so the bar is never the only signal.
export default function AirScale({ step, tone }: { step: number; tone: Tone }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const { fg } = toneColors(colors, tone);
  return (
    <View accessible accessibilityLabel={`Poziom ${step} z 6`} style={styles.box}>
      <View style={styles.bar}>
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <View key={i} style={[styles.seg, { backgroundColor: i <= step ? fg : colors.border }, i === step && styles.active]} />
        ))}
      </View>
      <Text style={styles.text}>Poziom {step} z 6</Text>
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    box: { gap: space.xs },
    bar: { flexDirection: "row", gap: 4 },
    seg: { flex: 1, height: 8, borderRadius: radius.pill },
    active: { height: 12, marginTop: -2 },
    text: { ...typo.meta, color: t.colors.textSecondary },
  });
