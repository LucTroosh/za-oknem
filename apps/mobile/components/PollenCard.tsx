import Ionicons from "@expo/vector-icons/Ionicons";
import { StyleSheet, Text, View } from "react-native";

import { pollenView } from "../lib/pollen";
import { type Theme, type Tone, space, typo } from "../lib/theme";
import Card from "./Card";
import StatusBadge from "./StatusBadge";
import useTheme, { useThemedStyles } from "./useTheme";

// Taxa list (production UI v1 §11): compact rows, flower glyph + name on the left, the level in
// WORDS on the right (badge with glyph, never colour alone). All wording/levels come from
// lib/pollen.ts + the backend block; renders nothing when the backend sent no `pollen`.
const LEVEL_TONE: Record<string, Tone> = { BELOW_SEASON: "good", SEASON: "warning", PEAK: "danger" };

// null for an unparsable timestamp: never render "Invalid Date".
function format(iso: string | null, opts: Intl.DateTimeFormatOptions): string | null {
  if (iso === null || Number.isNaN(new Date(iso).getTime())) return null;
  return new Date(iso).toLocaleString("pl-PL", opts);
}

export default function PollenCard({ pollen }: { pollen: unknown }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const view = pollenView(pollen);
  if (!view) return null;
  const fetched = format(view.fetchedAt, { dateStyle: "short", timeStyle: "short" });
  const validHour = format(view.validAt, { hour: "2-digit", minute: "2-digit" });
  return (
    <Card>
      {view.status ? <Text style={view.state === "recent" ? styles.note : styles.status}>{view.status}</Text> : null}
      {view.lines.map((line, i) => (
        <View key={line.species} style={[styles.row, i > 0 && styles.divider]}>
          <Ionicons name="flower-outline" size={20} color={colors.pollenFg} importantForAccessibility="no" />
          <View style={styles.nameBox}>
            <Text style={styles.name}>{line.name}</Text>
            {line.valueText ? <Text style={styles.note}>{line.valueText}</Text> : null}
          </View>
          {line.level && line.levelLabel ? (
            <View style={styles.badge}>
              <StatusBadge tone={LEVEL_TONE[line.level] ?? "neutral"} label={line.levelLabel} />
            </View>
          ) : (
            <Text style={styles.note}>{line.text}</Text>
          )}
        </View>
      ))}
      {view.lines.length > 0 && validHour ? <Text style={styles.note}>Wartości na godz. {validHour}</Text> : null}
      {fetched ? <Text style={styles.note}>Pobrano {fetched}</Text> : null}
      <Text style={styles.note}>{view.note}</Text>
      <Text style={styles.note}>{view.attribution}</Text>
    </Card>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    row: { minHeight: 56, flexDirection: "row", alignItems: "center", gap: space.md, paddingVertical: space.xs },
    divider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: t.colors.border },
    nameBox: { flex: 1 },
    badge: { flexShrink: 1, maxWidth: "52%" },
    name: { ...typo.strong, color: t.colors.text },
    status: { ...typo.supporting, color: t.colors.warning, fontWeight: "600" },
    note: { ...typo.meta, color: t.colors.textSecondary },
  });
