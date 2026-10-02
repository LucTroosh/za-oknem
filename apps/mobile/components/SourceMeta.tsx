import { StyleSheet, Text, View } from "react-native";

import { type Theme, space, typo } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// Visually secondary source / freshness / methodology lines (production UI v1: "answer first,
// data second"). Full attribution stays reachable, just never dominant.
export default function SourceMeta({ lines }: { lines: (string | null | undefined)[] }) {
  const styles = useThemedStyles(createStyles);
  const shown = lines.filter((l): l is string => typeof l === "string" && l !== "");
  if (shown.length === 0) return null;
  return (
    <View style={styles.box}>
      {shown.map((l) => (
        <Text key={l} style={styles.text}>
          {l}
        </Text>
      ))}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    box: { gap: space.xs },
    text: { ...typo.meta, color: t.colors.textSecondary },
  });
