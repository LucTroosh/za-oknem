import { useRouter } from "expo-router";
import { PixelRatio, StyleSheet, View, useWindowDimensions } from "react-native";

import { type QuickTile, longestTileWords, quickGridColumns } from "../lib/start";
import { space } from "../lib/theme";
import StatusTile from "./StatusTile";

// Quick status (production UI v1 §5): one row of tiles when they stay readable, otherwise 2 x 2
// (also at large system font). Tapping a tile opens its detail screen. An odd last tile in the
// 2-column layout stays half width instead of stretching.
export default function QuickStatusGrid({ tiles }: { tiles: QuickTile[] }) {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const cols = quickGridColumns(width - 2 * space.lg, PixelRatio.getFontScale(), tiles.length, longestTileWords(tiles));
  const rows: QuickTile[][] = [];
  for (let i = 0; i < tiles.length; i += cols) rows.push(tiles.slice(i, i + cols));
  return (
    <View style={styles.grid}>
      {rows.map((row, ri) => (
        <View key={ri} style={styles.row}>
          {row.map((t) => (
            <StatusTile
              key={t.key}
              domain={t.domain}
              icon={t.icon}
              label={t.label}
              value={t.value}
              supporting={t.supporting}
              unavailable={t.unavailable}
              onPress={() => router.push(t.route)}
            />
          ))}
          {row.length < cols && Array.from({ length: cols - row.length }, (_, i) => <View key={`pad${i}`} style={styles.pad} />)}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: { gap: 8 },
  row: { flexDirection: "row", gap: 8, alignItems: "stretch" },
  pad: { flex: 1 },
});
