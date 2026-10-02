import Ionicons from "@expo/vector-icons/Ionicons";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { type Theme, space, typo } from "../lib/theme";
import IconBox from "./IconBox";
import useTheme, { useThemedStyles } from "./useTheme";

// One selectable place (production UI v1 §14): pin in a soft container, title, optional secondary
// text, checkmark for the active one, chevron otherwise. >= 56 dp, the whole row is the target.
// Lives inside a grouped surface (LocationGroup), not as a standalone card.
export default function LocationRow({
  title,
  subtitle,
  active,
  busy,
  disabled,
  last,
  onPress,
}: {
  title: string;
  subtitle?: string;
  active?: boolean;
  busy?: boolean;
  disabled?: boolean;
  last?: boolean;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={[title, subtitle, active ? "aktualna lokalizacja" : null].filter(Boolean).join(", ")}
      accessibilityHint="Ustawia tę miejscowość jako lokalizację"
      accessibilityState={{ disabled: disabled ?? false, busy: busy ?? false, selected: active ?? false }}
      disabled={disabled}
      onPress={onPress}
      style={[styles.row, !last && styles.divider, disabled && !busy && styles.dim]}
    >
      <IconBox name="location-outline" fg={colors.accent} bg={colors.elevated} size={32} iconSize={18} rounded={10} />
      <View style={styles.texts}>
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      {busy ? (
        <ActivityIndicator color={colors.accent} />
      ) : active ? (
        <Ionicons name="checkmark-circle" size={22} color={colors.accent} importantForAccessibility="no" />
      ) : (
        <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} importantForAccessibility="no" />
      )}
    </Pressable>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    row: { minHeight: 56, flexDirection: "row", alignItems: "center", gap: space.md, paddingVertical: space.sm, paddingHorizontal: space.lg },
    divider: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: t.colors.border },
    dim: { opacity: 0.5 },
    texts: { flex: 1, gap: 2 },
    title: { ...typo.strong, color: t.colors.text },
    subtitle: { ...typo.caption, color: t.colors.textSecondary },
  });
