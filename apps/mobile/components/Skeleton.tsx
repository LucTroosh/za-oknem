import { StyleSheet, View, type DimensionValue } from "react-native";

import { radius } from "../lib/theme";
import useTheme from "./useTheme";

// Static placeholder block (no animation: nothing to switch off for Reduce Motion).
export default function Skeleton({ width = "100%", height = 16 }: { width?: DimensionValue; height?: number }) {
  const { colors } = useTheme();
  return <View style={[styles.block, { width, height, backgroundColor: colors.border }]} />;
}

// One module while it loads: hidden from screen readers except for a single label.
export function SkeletonCard({ label, lines = 2 }: { label: string; lines?: number }) {
  const { colors } = useTheme();
  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}
    >
      <Skeleton width="40%" height={14} />
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} width={i === 0 ? "70%" : "90%"} height={i === 0 ? 24 : 14} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  block: { borderRadius: radius.sm },
  card: { gap: 8, padding: 16, borderRadius: radius.md, borderWidth: StyleSheet.hairlineWidth },
});
