import Ionicons from "@expo/vector-icons/Ionicons";
import type { ComponentProps } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MIN_TOUCH, type Theme, type Tone, radius, space, toneColors, typo } from "../lib/theme";
import useTheme, { useThemedStyles } from "./useTheme";

type IconName = ComponentProps<typeof Ionicons>["name"];
// Glyph + words per tone: status is never colour alone.
const ICON: Record<Tone, IconName> = {
  good: "checkmark-circle",
  warning: "alert-circle",
  danger: "warning",
  info: "information-circle",
  neutral: "help-circle",
};

// Inline banner: a short sentence in human language, optional one-line detail and action.
// Read out as an alert for warning/danger so a TalkBack user hears a failed refresh.
export default function InfoBanner({
  tone,
  text,
  detail,
  actionLabel,
  onAction,
}: {
  tone: Tone;
  text: string;
  detail?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const { fg, bg } = toneColors(colors, tone);
  const body = (
    <>
      <Ionicons name={ICON[tone]} size={22} color={fg} importantForAccessibility="no" />
      <View style={styles.texts}>
        <Text style={[styles.text, { color: colors.text }]}>{text}</Text>
        {detail ? <Text style={[styles.detail, { color: colors.textSecondary }]}>{detail}</Text> : null}
        {actionLabel ? <Text style={[styles.action, { color: fg }]}>{actionLabel}</Text> : null}
      </View>
      {onAction ? <Ionicons name="chevron-forward" size={20} color={fg} importantForAccessibility="no" /> : null}
    </>
  );
  const accessibilityLabel = [text, detail, actionLabel].filter(Boolean).join(". ");
  if (onAction) {
    return (
      <Pressable accessibilityRole="button" accessibilityLabel={accessibilityLabel} onPress={onAction} style={[styles.box, { backgroundColor: bg }]}>
        {body}
      </Pressable>
    );
  }
  return (
    <View
      accessible
      accessibilityRole={tone === "warning" || tone === "danger" ? "alert" : undefined}
      accessibilityLabel={accessibilityLabel}
      style={[styles.box, { backgroundColor: bg }]}
    >
      {body}
    </View>
  );
}

const createStyles = (_t: Theme) =>
  StyleSheet.create({
    box: { minHeight: MIN_TOUCH, flexDirection: "row", alignItems: "center", gap: space.md, padding: space.md, borderRadius: radius.card },
    texts: { flex: 1, gap: 2 },
    text: { ...typo.strong },
    detail: { ...typo.caption },
    action: { ...typo.caption, fontWeight: "700" },
  });
