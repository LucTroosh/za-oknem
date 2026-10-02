import Ionicons from "@expo/vector-icons/Ionicons";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { type Theme, radius, space, typo } from "../lib/theme";
import useTheme, { useThemedStyles } from "./useTheme";

// One selectable place. >= 56 dp high, the whole row is the target (spec §38).
export default function LocationRow({
  title,
  subtitle,
  busy,
  disabled,
  onPress,
}: {
  title: string;
  subtitle?: string;
  busy?: boolean;
  disabled?: boolean;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={subtitle ? `${title}, ${subtitle}` : title}
      accessibilityHint="Ustawia tę miejscowość jako lokalizację"
      accessibilityState={{ disabled: disabled ?? false, busy: busy ?? false }}
      disabled={disabled}
      onPress={onPress}
      style={[styles.row, disabled && !busy && styles.dim]}
    >
      <View style={styles.texts}>
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      {busy ? (
        <ActivityIndicator color={colors.accent} />
      ) : (
        <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
      )}
    </Pressable>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    row: {
      minHeight: 56,
      flexDirection: "row",
      alignItems: "center",
      gap: space.md,
      paddingVertical: space.md,
      paddingHorizontal: space.lg,
      borderRadius: radius.md,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: t.colors.border,
      backgroundColor: t.colors.surface,
    },
    dim: { opacity: 0.5 },
    texts: { flex: 1, gap: space.xs },
    title: { ...typo.heading, color: t.colors.text },
    subtitle: { ...typo.caption, color: t.colors.textSecondary },
  });
