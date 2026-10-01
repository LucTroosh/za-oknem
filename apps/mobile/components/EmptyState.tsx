import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { MIN_TOUCH, type Theme, radius, space, typo } from "../app/theme";
import Card from "./Card";
import useTheme, { useThemedStyles } from "./useTheme";

// One place for "nothing here yet" / "could not load": say what happened and what to do.
// `devHint` is shown only in development builds (never in the production UI).
export default function EmptyState({
  title,
  message,
  actionLabel,
  onAction,
  devHint,
}: {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  devHint?: string;
}) {
  const styles = useThemedStyles(createStyles);
  return (
    <Card>
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      <Text style={styles.message}>{message}</Text>
      {__DEV__ && devHint ? <Text style={styles.dev}>Dev: {devHint}</Text> : null}
      {actionLabel && onAction ? (
        <Pressable accessibilityRole="button" onPress={onAction} style={styles.button}>
          <Text style={styles.buttonText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </Card>
  );
}

export function LoadingState({ label }: { label: string }) {
  const { colors } = useTheme();
  return (
    <View style={loading.box} accessibilityRole="progressbar" accessibilityLabel={label}>
      <ActivityIndicator color={colors.accent} />
      <Text style={[loading.text, { color: colors.textSecondary }]}>{label}</Text>
    </View>
  );
}

const loading = StyleSheet.create({
  box: { flexDirection: "row", alignItems: "center", gap: space.md, paddingVertical: space.lg },
  text: { ...typo.body },
});

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.heading, color: t.colors.text },
    message: { ...typo.body, color: t.colors.textSecondary },
    dev: { ...typo.caption, color: t.colors.dim, fontStyle: "italic" },
    button: {
      alignSelf: "flex-start",
      minHeight: MIN_TOUCH,
      justifyContent: "center",
      paddingHorizontal: space.lg,
      marginTop: space.sm,
      borderRadius: radius.pill,
      backgroundColor: t.colors.accent,
    },
    buttonText: { ...typo.strong, color: t.colors.onAccent },
  });
