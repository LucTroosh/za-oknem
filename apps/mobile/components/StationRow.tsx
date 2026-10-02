import { StyleSheet, Text, View } from "react-native";

import { formatObservedAt } from "../lib/dashboardTypes";
import { HYDRO_FRESHNESS_LABEL, HYDRO_STATUS_LABEL, type HydroItem, hydroLevelLine } from "../lib/hydro";
import { type Theme, space, typo } from "../lib/theme";
import FreshnessBadge from "./FreshnessBadge";
import { useThemedStyles } from "./useTheme";

// One IMGW water-level station: status word (never colour alone), level and IMGW's own
// thresholds, observation time and freshness. `statusText` overrides the word when the
// group knows better (e.g. an old NORMAL reading must not say "poniżej progów").
export default function StationRow({ item, statusText }: { item: HydroItem; statusText?: string }) {
  const styles = useThemedStyles(createStyles);
  const { station, freshness } = item;
  return (
    <View style={styles.item}>
      <Text style={styles.strong}>
        {station.station_name} —{" "}
        <Text style={station.status === "ALARM" ? styles.alarm : station.status === "WARNING" ? styles.warning : styles.plain}>
          {statusText ?? HYDRO_STATUS_LABEL[station.status]}
        </Text>
      </Text>
      <Text style={styles.body}>{hydroLevelLine(station)}</Text>
      <Text style={styles.meta}>{formatObservedAt(station.observed_at)}</Text>
      <FreshnessBadge state={freshness} label={HYDRO_FRESHNESS_LABEL[freshness]} />
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    strong: { ...typo.strong, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    meta: { ...typo.caption, color: t.colors.textSecondary },
    alarm: { color: t.colors.danger, fontWeight: "700" },
    warning: { color: t.colors.warning, fontWeight: "700" },
    plain: { color: t.colors.textSecondary, fontWeight: "600" },
    item: {
      gap: 2,
      paddingTop: space.md,
      marginTop: space.xs,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: t.colors.border,
    },
  });
