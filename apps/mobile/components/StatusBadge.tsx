import Ionicons from "@expo/vector-icons/Ionicons";
import type { ComponentProps } from "react";
import { StyleSheet, Text, View } from "react-native";

import { type Tone, radius, space, toneColors, typo } from "../lib/theme";
import useTheme from "./useTheme";

type IconName = ComponentProps<typeof Ionicons>["name"];
const ICON: Record<Tone, IconName> = { good: "checkmark-circle", warning: "alert-circle", danger: "warning", info: "information-circle", neutral: "help-circle" };

// Small pill: glyph + word (never colour alone).
export default function StatusBadge({ tone, label }: { tone: Tone; label: string }) {
  const { colors } = useTheme();
  const { fg, bg } = toneColors(colors, tone);
  return (
    <View accessible accessibilityLabel={label} style={[styles.pill, { backgroundColor: bg }]}>
      <Ionicons name={ICON[tone]} size={14} color={fg} importantForAccessibility="no" />
      <Text style={[styles.text, { color: fg, flexShrink: 1 }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: { flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start", paddingHorizontal: space.sm, paddingVertical: 4, borderRadius: radius.pill },
  text: { ...typo.meta, fontWeight: "700" },
});
