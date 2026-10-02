import Ionicons from "@expo/vector-icons/Ionicons";
import type { ComponentProps } from "react";

import type { GlyphLevel } from "../lib/home";
import { type Tone, toneColors } from "../lib/theme";
import useTheme from "./useTheme";

// The one status glyph (spec §15/§36), drawn with the app's single icon library. Always sits
// next to a word, so it is decorative for screen readers.
type IconName = ComponentProps<typeof Ionicons>["name"];
const ICON: Record<GlyphLevel, IconName> = {
  GOOD: "checkmark-circle",
  CAUTION: "alert-circle",
  AVOID: "warning",
  UNKNOWN: "help-circle",
};
export const GLYPH_TONE: Record<GlyphLevel, Tone> = {
  GOOD: "good",
  CAUTION: "warning",
  AVOID: "danger",
  UNKNOWN: "neutral",
};

export default function StatusGlyph({ level, size = 24 }: { level: GlyphLevel; size?: number }) {
  const { colors } = useTheme();
  return (
    <Ionicons
      name={ICON[level]}
      size={size}
      color={toneColors(colors, GLYPH_TONE[level]).fg}
      importantForAccessibility="no"
      accessibilityElementsHidden
    />
  );
}
