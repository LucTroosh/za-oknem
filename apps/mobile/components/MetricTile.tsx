import { StyleSheet, Text, View } from "react-native";

import { type Domain, type Theme, domainColors, elevation, radius, space, typo } from "../lib/theme";
import IconBox, { type IconName } from "./IconBox";
import useTheme, { useThemedStyles } from "./useTheme";

// One measurement in a 2-/3-column grid (weather and air detail): label, bold value, unit/age.
// A missing value is "brak danych", never 0 (rule #8); `dim` shows it as secondary.
export default function MetricTile({
  icon,
  domain,
  label,
  value,
  note,
  dim,
}: {
  icon?: IconName;
  domain: Domain;
  label: string;
  value: string;
  note?: string | null;
  dim?: boolean;
}) {
  const { colors, scheme } = useTheme();
  const styles = useThemedStyles(createStyles);
  const d = domainColors(colors, domain);
  return (
    <View
      accessible
      accessibilityLabel={[label, value, note].filter(Boolean).join(", ")}
      style={[styles.tile, { backgroundColor: scheme === "dark" ? colors.elevated : colors.surface }]}
    >
      {icon ? <IconBox name={icon} fg={d.fg} bg={d.bg} size={30} iconSize={17} rounded={10} /> : null}
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, dim && styles.dim]}>{value}</Text>
      {note ? <Text style={styles.note}>{note}</Text> : null}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    tile: { flexGrow: 1, flexBasis: "30%", minWidth: 96, minHeight: 82, padding: space.md, gap: 2, borderRadius: radius.md, ...elevation(t.scheme) },
    label: { ...typo.meta, fontWeight: "600", color: t.colors.textSecondary },
    value: { ...typo.cardTitle, color: t.colors.text },
    dim: { color: t.colors.dim, fontWeight: "500" },
    note: { ...typo.meta, fontWeight: "400", color: t.colors.textSecondary },
  });
