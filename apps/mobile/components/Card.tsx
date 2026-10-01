import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";

import { type Theme, radius, space } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// The one surface everything on a screen sits on.
export default function Card({ children }: { children: ReactNode }) {
  const styles = useThemedStyles(createStyles);
  return <View style={styles.card}>{children}</View>;
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    card: {
      backgroundColor: t.colors.surface,
      borderRadius: radius.md,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: t.colors.border,
      padding: space.lg,
      gap: space.xs,
    },
  });
