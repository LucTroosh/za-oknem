import Ionicons from "@expo/vector-icons/Ionicons";
import type { ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { type Theme, elevation, radius, space, typo } from "../lib/theme";
import IconBox, { type IconName } from "./IconBox";
import useTheme, { useThemedStyles } from "./useTheme";

// Settings list (production UI v1 §13): one rounded surface, rows >= 64 dp with a 36 dp icon box,
// title, optional secondary value and a chevron. Long copy lives on sub-pages.
export function SettingsGroup({ children }: { children: ReactNode }) {
  const styles = useThemedStyles(createStyles);
  return <View style={styles.group}>{children}</View>;
}

export default function SettingsRow({
  icon,
  title,
  value,
  onPress,
  last,
  hint,
}: {
  icon: IconName;
  title: string;
  value?: string;
  onPress: () => void;
  last?: boolean;
  hint?: string;
}) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={value ? `${title}: ${value}` : title}
      accessibilityHint={hint}
      onPress={onPress}
      style={[styles.row, !last && styles.divider]}
    >
      <IconBox name={icon} fg={colors.accent} bg={colors.elevated} size={36} iconSize={20} rounded={10} />
      <View style={styles.texts}>
        <Text style={styles.title}>{title}</Text>
        {value ? <Text style={styles.value}>{value}</Text> : null}
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} importantForAccessibility="no" />
    </Pressable>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    group: {
      backgroundColor: t.scheme === "dark" ? t.colors.elevated : t.colors.surface,
      borderRadius: radius.lg,
      overflow: "hidden",
      ...elevation(t.scheme),
    },
    row: { minHeight: 64, flexDirection: "row", alignItems: "center", gap: space.md, paddingHorizontal: space.lg, paddingVertical: space.sm },
    divider: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: t.colors.border },
    texts: { flex: 1 },
    title: { ...typo.strong, color: t.colors.text },
    value: { ...typo.caption, color: t.colors.textSecondary },
  });
