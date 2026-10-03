import { StyleSheet, Text, View } from "react-native";

import { formatObservedAt } from "../lib/dashboardTypes";
import { HYDRO_FRESHNESS_LABEL, HYDRO_STATUS_LABEL, type HydroItem, hydroLevelLine } from "../lib/hydro";
import { type Theme, type Tone, space, typo } from "../lib/theme";
import FreshnessBadge from "./FreshnessBadge";
import StatusBadge from "./StatusBadge";
import { useThemedStyles } from "./useTheme";

// One IMGW water-level station: name, status badge (glyph + word, never colour alone), level and
// IMGW's own thresholds, observation time and freshness. `statusText` overrides the word when the
// group knows better (an old NORMAL reading must not say "poniżej progów").
const TONE: Record<string, Tone> = { ALARM: "danger", WARNING: "warning", NORMAL: "good", UNKNOWN: "neutral" };

export default function StationRow({ item, statusText, first }: { item: HydroItem; statusText?: string; first?: boolean }) {
  const styles = useThemedStyles(createStyles);
  const { station, freshness } = item;
  const tone: Tone = statusText ? "neutral" : (TONE[station.status] ?? "neutral");
  return (
    <View style={[styles.item, !first && styles.divider]}>
      <Text style={styles.name}>{station.station_name}</Text>
      <StatusBadge tone={tone} label={statusText ?? HYDRO_STATUS_LABEL[station.status]} />
      <Text style={styles.body}>{hydroLevelLine(station)}</Text>
      {station.distance_km != null && <Text style={styles.meta}>Około {station.distance_km.toFixed(1).replace(".", ",")} km od wybranej lokalizacji</Text>}
      <Text style={styles.meta}>{formatObservedAt(station.observed_at)}</Text>
      <FreshnessBadge state={freshness} label={HYDRO_FRESHNESS_LABEL[freshness]} />
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    item: { gap: 4, paddingVertical: space.md },
    divider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: t.colors.border },
    name: { ...typo.cardTitle, color: t.colors.text },
    body: { ...typo.supporting, color: t.colors.text },
    meta: { ...typo.meta, fontWeight: "400", color: t.colors.textSecondary },
  });
