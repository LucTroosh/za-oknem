import { Pressable, StyleSheet, Text, View } from "react-native";

import { type Domain, type Theme, domainColors, elevation, radius, space, typo } from "../lib/theme";
import IconBox, { type IconName } from "./IconBox";
import useTheme, { useThemedStyles } from "./useTheme";

// Quick-status tile (production UI v1 §5): domain icon in a tinted container, label, strong
// value, small supporting line. Soft domain tint, no hard border. An unavailable tile is
// neutral and still says so in words (never an empty fake tile).
export default function StatusTile({
  domain,
  icon,
  label,
  value,
  supporting,
  unavailable,
  onPress,
  hint,
}: {
  domain: Domain;
  icon: IconName;
  label: string;
  value: string;
  supporting?: string | null;
  unavailable?: boolean;
  onPress?: () => void;
  hint?: string;
}) {
  const { colors, scheme } = useTheme();
  const styles = useThemedStyles(createStyles);
  const d = domainColors(colors, domain);
  // Available tiles carry the domain tint across the whole tile in light mode (AA pairs are in
  // theme.test); dark keeps the elevated surface. Unavailable stays neutral.
  const bg = unavailable ? colors.neutralBg : scheme === "dark" ? colors.elevated : d.bg;
  const fg = unavailable ? colors.textSecondary : d.fg;
  const iconBg = scheme === "dark" && !unavailable ? d.bg : colors.surface;
  const label_ = [label, value, supporting].filter(Boolean).join(", ");
  const content = (
    <>
      <IconBox name={icon} fg={fg} bg={iconBg} size={32} iconSize={18} rounded={11} />
      <Text style={styles.label} numberOfLines={2}>
        {label}
      </Text>
      <Text style={[styles.value, unavailable && styles.dim]}>{value}</Text>
      {supporting ? <Text style={styles.supporting}>{supporting}</Text> : null}
    </>
  );
  const box = [styles.tile, { backgroundColor: bg }];
  if (onPress) {
    return (
      <Pressable accessibilityRole="button" accessibilityLabel={label_} accessibilityHint={hint ?? "Otwiera szczegóły"} onPress={onPress} style={box}>
        {content}
      </Pressable>
    );
  }
  return (
    <View accessible accessibilityLabel={label_} style={box}>
      {content}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    tile: { flex: 1, minHeight: 108, padding: 10, gap: 2, borderRadius: radius.card, ...elevation(t.scheme) },
    label: { ...typo.meta, fontSize: 12, fontWeight: "600", color: t.colors.textSecondary, marginTop: space.xs },
    value: { ...typo.cardTitle, fontSize: 17, fontWeight: "700", color: t.colors.text },
    dim: { color: t.colors.dim },
    supporting: { ...typo.meta, fontWeight: "400", color: t.colors.textSecondary },
  });
