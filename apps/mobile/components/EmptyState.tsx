import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import type { StateArt } from "../lib/stateArt";
import { type Theme, space, typo } from "../lib/theme";
import Button from "./Button";
import Card from "./Card";
import StateIllustration from "./StateIllustration";
import useTheme, { useThemedStyles } from "./useTheme";

// One place for "nothing here yet" / "could not load": say what happened and what to do, in
// human language. The illustration is decorative; `devHint` shows only in development builds.
export default function EmptyState({
  title,
  message,
  actionLabel,
  onAction,
  devHint,
  art,
}: {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  devHint?: string;
  art?: StateArt;
}) {
  const styles = useThemedStyles(createStyles);
  return (
    <Card>
      <View style={styles.box}>
        {art ? <StateIllustration art={art} height={120} /> : null}
        <Text style={styles.title} accessibilityRole="header">
          {title}
        </Text>
        <Text style={styles.message}>{message}</Text>
        {__DEV__ && devHint ? <Text style={styles.dev}>Dev: {devHint}</Text> : null}
        {actionLabel && onAction ? <Button label={actionLabel} variant="secondary" onPress={onAction} /> : null}
      </View>
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
    box: { alignItems: "center", gap: space.sm, paddingVertical: space.sm },
    title: { ...typo.heading, color: t.colors.text, textAlign: "center" },
    message: { ...typo.supporting, color: t.colors.textSecondary, textAlign: "center" },
    dev: { ...typo.caption, color: t.colors.dim, fontStyle: "italic", textAlign: "center" },
  });
