import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";

import { type Theme, elevation, radius } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// Major surface (production UI v1 §4): radius 24, min height 150, padding 20, soft semantic
// tint, subtle elevation, no hard border.
export default function HeroSurface({ children, tint, minHeight = 150 }: { children: ReactNode; tint: string; minHeight?: number }) {
  const styles = useThemedStyles(createStyles);
  return <View style={[styles.hero, { backgroundColor: tint, minHeight }]}>{children}</View>;
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    hero: { borderRadius: radius.hero, padding: 20, gap: 12, ...elevation(t.scheme, 2) },
  });
