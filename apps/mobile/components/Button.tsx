import { Pressable, StyleSheet, Text } from "react-native";

import { type Theme, radius, space, typo } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// Primary action: accent pill, >= 44 dp (spec §38), disabled state announced.
export default function Button({
  label,
  onPress,
  disabled,
  hint,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  hint?: string;
}) {
  const styles = useThemedStyles(createStyles);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={hint}
      accessibilityState={{ disabled: disabled ?? false }}
      disabled={disabled}
      onPress={onPress}
      style={[styles.button, disabled && styles.disabled]}
    >
      <Text style={styles.text}>{label}</Text>
    </Pressable>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    button: {
      minHeight: 52,
      alignItems: "center",
      justifyContent: "center",
      paddingHorizontal: space.xl,
      borderRadius: radius.pill,
      backgroundColor: t.colors.accent,
    },
    disabled: { opacity: 0.5 },
    text: { ...typo.heading, color: t.colors.onAccent },
  });
