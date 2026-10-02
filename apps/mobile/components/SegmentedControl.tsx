import { Pressable, StyleSheet, Text, View } from "react-native";

import { MIN_TOUCH, type Theme, radius, space, typo } from "../lib/theme";
import { useThemedStyles } from "./useTheme";

// Radio-like segmented control (Appearance). Selected = fill + bold + check semantics in state;
// every segment >= 48 dp. Only for choices that really exist.
export default function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  label: string;
}) {
  const styles = useThemedStyles(createStyles);
  return (
    <View accessibilityRole="radiogroup" accessibilityLabel={label} style={styles.track}>
      {options.map((o) => {
        const selected = o.value === value;
        return (
          <Pressable
            key={o.value}
            accessibilityRole="radio"
            accessibilityLabel={o.label}
            accessibilityState={{ selected, checked: selected }}
            onPress={() => onChange(o.value)}
            style={[styles.segment, selected && styles.selected]}
          >
            <Text style={[styles.text, selected && styles.selectedText]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    track: { flexDirection: "row", gap: space.xs, padding: space.xs, borderRadius: radius.pill, backgroundColor: t.colors.elevated },
    segment: { flex: 1, minHeight: MIN_TOUCH, alignItems: "center", justifyContent: "center", paddingHorizontal: space.sm, borderRadius: radius.pill },
    selected: { backgroundColor: t.colors.accent },
    text: { ...typo.strong, color: t.colors.text },
    selectedText: { color: t.colors.onAccent, fontWeight: "800" },
  });
