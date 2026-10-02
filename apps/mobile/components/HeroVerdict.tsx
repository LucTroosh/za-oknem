import Ionicons from "@expo/vector-icons/Ionicons";
import { useState } from "react";
import { PixelRatio, Pressable, StyleSheet, Text, View } from "react-native";

import { type VerdictModel } from "../lib/home";
import { MIN_TOUCH, type Theme, space, toneColors, typo } from "../lib/theme";
import HeroSurface from "./HeroSurface";
import IconBox from "./IconBox";
import { GLYPH_TONE } from "./StatusGlyph";
import useTheme, { useThemedStyles } from "./useTheme";

const ICON = { GOOD: "checkmark-circle", CAUTION: "alert-circle", AVOID: "warning", UNKNOWN: "help-circle" } as const;

// The answer (production UI v1 §4/§7B): big semantic icon, one human headline, one short
// sentence. The backend reasons and any technical gap list sit behind a disclosure, never in the
// headline. Disclaimers and source text live lower on the screen, not in the hero.
export default function HeroVerdict({ verdict }: { verdict: VerdictModel }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const [open, setOpen] = useState(false);
  const { fg, bg } = toneColors(colors, GLYPH_TONE[verdict.level]);
  const items = [...verdict.reasons, ...verdict.details];
  // Large system font: the icon moves above the text so the headline gets the full card width.
  const stacked = PixelRatio.getFontScale() >= 1.3;
  const label = verdict.level === "UNKNOWN" ? "Szczegóły" : "Powody oceny";
  return (
    <HeroSurface tint={bg}>
      <View style={[styles.head, stacked && styles.headStacked]} accessible accessibilityRole="header" accessibilityLabel={`${verdict.headline}. ${verdict.supporting}`}>
        <IconBox name={ICON[verdict.level]} fg={fg} bg={colors.surface} size={56} iconSize={32} rounded={18} />
        <View style={styles.texts}>
          <Text style={styles.headline}>{verdict.headline}</Text>
          <Text style={styles.supporting}>{verdict.supporting}</Text>
        </View>
      </View>
      {items.length > 0 && (
        <>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={label}
            accessibilityHint={open ? "Ukrywa listę" : "Pokazuje listę"}
            accessibilityState={{ expanded: open }}
            onPress={() => setOpen((v) => !v)}
            style={styles.toggle}
          >
            <Text style={[styles.toggleText, { color: fg }]}>{label}</Text>
            <Ionicons name={open ? "chevron-up" : "chevron-down"} size={20} color={fg} importantForAccessibility="no" />
          </Pressable>
          {open && (
            <View style={styles.list}>
              {items.map((line) => (
                <Text key={line} style={styles.item}>
                  • {line}
                </Text>
              ))}
            </View>
          )}
        </>
      )}
    </HeroSurface>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    head: { flexDirection: "row", alignItems: "center", gap: space.md },
    headStacked: { flexDirection: "column", alignItems: "flex-start" },
    texts: { flex: 1, alignSelf: "stretch", gap: space.xs },
    headline: { ...typo.title, fontSize: 24, lineHeight: 30, fontWeight: "800", color: t.colors.text },
    supporting: { ...typo.supporting, color: t.colors.textSecondary },
    toggle: {
      minHeight: MIN_TOUCH,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      paddingHorizontal: space.md,
      borderRadius: 16,
      backgroundColor: t.scheme === "dark" ? t.colors.surface : "rgba(255,255,255,0.7)",
    },
    toggleText: { ...typo.strong },
    list: { gap: space.xs },
    item: { ...typo.supporting, color: t.colors.text },
  });
