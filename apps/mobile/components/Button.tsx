import { Pressable, StyleSheet, Text } from "react-native";

import { type Theme, radius, space, typo } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// PrimaryButton / SecondaryButton (production UI v1): pill, >= 52 dp, disabled state announced.
export default function Button({
  label,
  onPress,
  disabled,
  hint,
  variant = "primary",
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  hint?: string;
  variant?: "primary" | "secondary";
}) {
  const styles = useThemedStyles(createStyles);
  const secondary = variant === "secondary";
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={hint}
      accessibilityState={{ disabled: disabled ?? false }}
      disabled={disabled}
      onPress={onPress}
      style={[styles.button, secondary ? styles.secondary : styles.primary, disabled && styles.disabled]}
    >
      <Text style={[styles.text, secondary ? styles.secondaryText : styles.primaryText]}>{label}</Text>
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
      paddingVertical: space.sm,
      borderRadius: radius.pill,
    },
    primary: { backgroundColor: t.colors.accent },
    secondary: { backgroundColor: t.colors.elevated },
    disabled: { opacity: 0.5 },
    text: { ...typo.cardTitle, textAlign: "center" },
    primaryText: { color: t.colors.onAccent },
    secondaryText: { color: t.colors.accent },
  });
