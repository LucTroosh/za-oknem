import { Pressable, StyleSheet, Text, View } from "react-native";

import { MIN_TOUCH, type Theme, typo } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// "Section title                      Action >": the action only when it has a real destination.
export default function SectionHeader({ title, actionLabel, onAction }: { title: string; actionLabel?: string; onAction?: () => void }) {
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.row}>
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      {actionLabel && onAction ? (
        <Pressable accessibilityRole="button" accessibilityLabel={actionLabel} onPress={onAction} hitSlop={8} style={styles.action}>
          <Text style={styles.actionText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
    title: { ...typo.heading, color: t.colors.text, flexShrink: 1 },
    action: { minHeight: MIN_TOUCH, justifyContent: "center" },
    actionText: { ...typo.meta, fontSize: 13, color: t.colors.accent, fontWeight: "600" },
  });
