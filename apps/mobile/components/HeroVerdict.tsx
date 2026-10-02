import Ionicons from "@expo/vector-icons/Ionicons";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { type VerdictModel } from "../lib/home";
import { OUTDOOR_DISCLAIMER } from "../lib/outdoor";
import { MIN_TOUCH, type Theme, radius, space, toneColors, typo } from "../lib/theme";
import StatusGlyph, { GLYPH_TONE } from "./StatusGlyph";
import useTheme, { useThemedStyles } from "./useTheme";

// Spec §11: the first thing on Start. LIVE verdict from the backend block (never a mock);
// glyph + word + tint, colour is never the only carrier. Tap -> the reasons (backend
// `reasons[]`, already formatted by outdoorView). UNKNOWN has no toggle: its line says WHY
// there is no verdict, so it stays visible. The disclaimer is always visible.
export default function HeroVerdict({ verdict }: { verdict: VerdictModel }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const [open, setOpen] = useState(false);
  const { fg, bg } = toneColors(colors, GLYPH_TONE[verdict.level]);
  const toggle = verdict.level !== "UNKNOWN" && verdict.lines.length > 0;
  const showLines = !toggle || open;
  const head = (
    <View style={styles.head}>
      <StatusGlyph level={verdict.level} size={32} />
      <Text style={[styles.headline, { color: fg }]}>{verdict.headline}</Text>
      {toggle && <Ionicons name={open ? "chevron-up" : "chevron-down"} size={22} color={fg} importantForAccessibility="no" />}
    </View>
  );
  return (
    <View style={[styles.card, { backgroundColor: bg, borderLeftColor: fg }]}>
      {toggle ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={verdict.headline}
          accessibilityHint={open ? "Ukrywa powody oceny" : "Pokazuje powody oceny"}
          accessibilityState={{ expanded: open }}
          onPress={() => setOpen((v) => !v)}
          style={styles.toggle}
        >
          {head}
        </Pressable>
      ) : (
        <View accessible accessibilityRole="header" accessibilityLabel={verdict.headline}>
          {head}
        </View>
      )}
      {showLines &&
        verdict.lines.map((line) => (
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
    toggle: { minHeight: MIN_TOUCH, justifyContent: "center" },
    head: { flexDirection: "row", alignItems: "center", gap: space.sm },
    headline: { ...typo.title, flexShrink: 1, flex: 1 },
    line: { ...typo.body, color: t.colors.text },
    note: { ...typo.caption, color: t.colors.textSecondary },
  });
