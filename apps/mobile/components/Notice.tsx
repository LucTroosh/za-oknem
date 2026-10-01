import { StyleSheet, Text } from "react-native";

import { radius, space, toneColors, typo } from "../lib/theme";
import useTheme from "./useTheme";

// Inline notice (e.g. a failed refresh while older data is still on screen). Read out as
// an alert; the glyph keeps it understandable without colour.
export default function Notice({ tone, text }: { tone: "warning" | "danger"; text: string }) {
  const { colors } = useTheme();
  const { fg, bg } = toneColors(colors, tone);
  return (
    <Text accessibilityRole="alert" style={[styles.box, { color: fg, backgroundColor: bg }]}>
      {tone === "danger" ? "✕ " : "▲ "}
      {text}
    </Text>
  );
}

const styles = StyleSheet.create({
  box: { ...typo.strong, padding: space.md, borderRadius: radius.md, overflow: "hidden" },
});
