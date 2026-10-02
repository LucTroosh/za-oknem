import Ionicons from "@expo/vector-icons/Ionicons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MIN_TOUCH, THEME_LABEL, THEME_PREFS, type Theme, type ThemePref, radius, space, typo } from "../lib/theme";
import useTheme, { useThemedStyles } from "./useTheme";

// Appearance (TASK-12.19): Systemowy | Jasny | Ciemny as a radio group. The selected option
// is marked by a check mark AND the filled surface (never colour alone), every option is >= 44 dp.
export default function ThemePicker({ value, onChange }: { value: ThemePref; onChange: (p: ThemePref) => void }) {
  const styles = useThemedStyles(createStyles);
  const { colors } = useTheme();
  return (
    <View accessibilityRole="radiogroup" accessibilityLabel="Wygląd" style={styles.group}>
      {THEME_PREFS.map((p) => {
        const selected = p === value;
        return (
          <Pressable
            key={p}
            accessibilityRole="radio"
            accessibilityLabel={THEME_LABEL[p]}
            accessibilityState={{ selected, checked: selected }}
            onPress={() => onChange(p)}
            style={[styles.option, selected && styles.selected]}
          >
            {selected && <Ionicons name="checkmark" size={18} color={colors.onAccent} importantForAccessibility="no" />}
            <Text style={[styles.text, selected && styles.selectedText]}>{THEME_LABEL[p]}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    group: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
    option: {
      minHeight: MIN_TOUCH,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: space.xs,
      paddingHorizontal: space.lg,
      borderRadius: radius.pill,
      borderWidth: 1,
      borderColor: t.colors.border,
      backgroundColor: t.colors.surface,
    },
    selected: { backgroundColor: t.colors.accent, borderColor: t.colors.accent },
    text: { ...typo.strong, color: t.colors.text },
    selectedText: { color: t.colors.onAccent },
  });
