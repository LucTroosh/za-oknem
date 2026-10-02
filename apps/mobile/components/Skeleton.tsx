import { StyleSheet, View, type DimensionValue } from "react-native";

import { type Theme, elevation, radius } from "../lib/theme";
import useTheme, { useThemedStyles } from "./useTheme";

// Static placeholder block (no animation: nothing to switch off for Reduce Motion).
export default function Skeleton({ width = "100%", height = 16 }: { width?: DimensionValue; height?: number }) {
  const { colors } = useTheme();
  return <View style={[styles.block, { width, height, backgroundColor: colors.elevated }]} />;
}

// One module while it loads: hidden from screen readers except for a single label.
export function SkeletonCard({ label, lines = 2, minHeight }: { label: string; lines?: number; minHeight?: number }) {
  const styles = useThemedStyles(createStyles);
  return (
    <View accessible accessibilityRole="progressbar" accessibilityLabel={label} style={[styles.card, minHeight ? { minHeight } : null]}>
      <Skeleton width="40%" height={14} />
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} width={i === 0 ? "70%" : "90%"} height={i === 0 ? 24 : 14} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({ block: { borderRadius: radius.sm } });

const createStyles = (t: Theme) =>
  StyleSheet.create({
    card: {
      gap: 8,
      padding: 16,
      borderRadius: radius.card,
      backgroundColor: t.colors.surface,
      ...elevation(t.scheme),
    },
  });
