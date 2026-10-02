import Ionicons from "@expo/vector-icons/Ionicons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MIN_TOUCH, type Theme, radius, space, typo } from "../lib/theme";
import { TOPICS, type TopicKey, isTopicOn, toggleTopic } from "../lib/topics";
import useTheme, { useThemedStyles } from "./useTheme";

// "Co chcesz śledzić?" tiles (S10), shared by the onboarding step and Settings. Multi-select;
// the selection is a local preference, not a profile. Selected = check mark + fill (not colour
// alone); every tile >= 44 dp. Nothing selected is read as "all", so all tiles look on then.
export default function TopicsPicker({ value, onChange }: { value: TopicKey[]; onChange: (v: TopicKey[]) => void }) {
  const styles = useThemedStyles(createStyles);
  const { colors } = useTheme();
  return (
    <View style={styles.group} accessibilityLabel="Co chcesz śledzić?">
      {TOPICS.map((t) => {
        const on = isTopicOn(value, t.key);
        return (
          <Pressable
            key={t.key}
            accessibilityRole="checkbox"
            accessibilityLabel={t.label}
            accessibilityHint={t.hint}
            accessibilityState={{ checked: on }}
            onPress={() => onChange(toggleTopic(value, t.key))}
            style={[styles.tile, on && styles.on]}
          >
            <Ionicons name={on ? "checkbox" : "square-outline"} size={22} color={on ? colors.onAccent : colors.textSecondary} importantForAccessibility="no" />
            <View style={styles.texts}>
              <Text style={[styles.label, on && styles.onText]}>{t.label}</Text>
              <Text style={[styles.hint, on && styles.onText]}>{t.hint}</Text>
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    group: { gap: space.sm },
    tile: {
      minHeight: MIN_TOUCH + 12,
      flexDirection: "row",
      alignItems: "center",
      gap: space.md,
      paddingHorizontal: space.lg,
      paddingVertical: space.sm,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: t.colors.border,
      backgroundColor: t.colors.surface,
    },
    on: { backgroundColor: t.colors.accent, borderColor: t.colors.accent },
    texts: { flex: 1 },
    label: { ...typo.strong, color: t.colors.text },
    hint: { ...typo.caption, color: t.colors.textSecondary },
    onText: { color: t.colors.onAccent },
  });
