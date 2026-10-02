import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";

import { type Theme, elevation, radius, space } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// The one surface everything sits on (production UI v1 §15): radius 18, subtle shadow in light
// mode, elevated surface (no outline) in dark mode. No hard border.
export default function Card({ children, tint }: { children: ReactNode; tint?: string }) {
  const styles = useThemedStyles(createStyles);
  return <View style={[styles.card, tint ? { backgroundColor: tint } : null]}>{children}</View>;
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    card: {
      backgroundColor: t.scheme === "dark" ? t.colors.elevated : t.colors.surface,
      borderRadius: radius.card,
      padding: space.lg,
      gap: space.sm,
      ...elevation(t.scheme),
    },
  });
