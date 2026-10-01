import { StyleSheet, Text } from "react-native";

import type { FreshnessState } from "../lib/freshness";
import { freshnessColor, typo } from "../lib/theme";
import useTheme from "./useTheme";

// Freshness is shown as glyph + word + colour - colour alone never carries it (a11y).
const GLYPH: Record<FreshnessState, string> = { FRESH: "●", RECENT: "◐", STALE: "▲", UNAVAILABLE: "○" };

export default function FreshnessBadge({ state, label }: { state: FreshnessState; label: string }) {
  const { colors } = useTheme();
  return (
    <Text
      accessibilityLabel={`Aktualność danych: ${label}`}
      style={[styles.text, { color: freshnessColor(colors, state) }]}
    >
      {GLYPH[state]} {label}
    </Text>
  );
}

const styles = StyleSheet.create({ text: { ...typo.caption, fontWeight: "600" } });
