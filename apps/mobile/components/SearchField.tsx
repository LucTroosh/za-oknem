import Ionicons from "@expo/vector-icons/Ionicons";
import { Pressable, StyleSheet, TextInput, View } from "react-native";

import { MIN_TOUCH, type Theme, elevation, radius, space, typo } from "../lib/theme";
import useTheme, { useThemedStyles } from "./useTheme";

// Search input (production UI v1 §14): 52 dp, radius 16, search glyph left, clear affordance right
// (>= 48 dp target) once there is text. No outline: the elevated surface separates it.
export default function SearchField({
  value,
  onChangeText,
  placeholder,
  editable = true,
}: {
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  editable?: boolean;
}) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.box}>
      <Ionicons name="search" size={20} color={colors.textSecondary} importantForAccessibility="no" />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.dim}
        accessibilityLabel={placeholder}
        style={styles.input}
        autoCorrect={false}
        autoCapitalize="words"
        returnKeyType="search"
        maxLength={100}
        editable={editable}
      />
      {value !== "" && (
        <Pressable accessibilityRole="button" accessibilityLabel="Wyczyść" hitSlop={6} onPress={() => onChangeText("")} style={styles.clear}>
          <Ionicons name="close-circle" size={22} color={colors.textSecondary} importantForAccessibility="no" />
        </Pressable>
      )}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    box: {
      minHeight: 52,
      flexDirection: "row",
      alignItems: "center",
      gap: space.sm,
      paddingLeft: space.lg,
      borderRadius: radius.md,
      backgroundColor: t.scheme === "dark" ? t.colors.elevated : t.colors.surface,
      ...elevation(t.scheme),
    },
    input: { ...typo.body, flex: 1, minHeight: 52, color: t.colors.text },
    clear: { width: MIN_TOUCH, height: MIN_TOUCH, alignItems: "center", justifyContent: "center" },
  });
