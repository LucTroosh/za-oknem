import { StyleSheet, Text, View } from "react-native";

import { formatObservedAt } from "../app/dashboardTypes";
import {
  HYDRO_FRESHNESS_LABEL,
  HYDRO_STATUS_LABEL,
  hydroLevelLine,
  summarizeHydro,
} from "../app/hydro";
import { type Theme, space, typo } from "../app/theme";
import Card from "./Card";
import FreshnessBadge from "./FreshnessBadge";
import useHydro from "./useHydro";
import useNow from "./useNow";
import { LoadingState } from "./EmptyState";
import { useThemedStyles } from "./useTheme";

const lastSuccess = (at: string | null) =>
  at === null ? "brak udanej aktualizacji" : `ostatnia aktualizacja ${formatObservedAt(at)}`;

// TASK-7.2 (hydro): own fetch and own states - independent of the dashboard (rule #1).
// Nationwide until geo matching - hence the "cała Polska" label. Statuses come from the
// backend (IMGW's own thresholds); nothing here classifies a level (rule #10).
export default function HydroSection({ refreshTick }: { refreshTick: number }) {
  const styles = useThemedStyles(createStyles);
  const { state, hydro } = useHydro(refreshTick);
  // Labels age on the device without a refetch.
  const now = useNow();
  const summary = hydro ? summarizeHydro(hydro, now) : null;
  return (
    <Card>
      <Text style={styles.title} accessibilityRole="header">
        Stany wody
      </Text>
      <Text style={styles.scope}>Cała Polska — stacje w stanie ostrzegawczym lub alarmowym.</Text>
      {state === "loading" && !hydro && <LoadingState label="Ładowanie stanów wody…" />}
      {state === "error" && (
        <Text style={styles.error} accessibilityRole="alert">
          {hydro
            ? "Nie udało się odświeżyć stanów wody — pokazane dane mogą być nieaktualne."
            : "Stany wody są chwilowo niedostępne. Odśwież widok, aby spróbować ponownie."}
        </Text>
      )}
      {summary?.kind === "unavailable" && (
        <Text style={styles.body}>
          Dane o stanach wody niedostępne lub nieaktualne ({lastSuccess(summary.lastSuccessAt)}).
        </Text>
      )}
      {summary?.kind === "none-confirmed" && (
        <Text style={styles.body}>
          Brak stacji w stanie ostrzegawczym lub alarmowym
          {summary.unassessed > 0
            ? ` (${summary.unassessed} stacji bez progów IMGW nie jest oceniane)`
            : ""}
          .
        </Text>
      )}
      {summary?.kind === "list" && summary.outdated && (
        <Text style={styles.warn}>Lista może być nieaktualna ({lastSuccess(summary.lastSuccessAt)}).</Text>
      )}
      {summary?.kind === "list" &&
        summary.items.map(({ station, freshness }) => (
          <View key={station.station_id} style={styles.item}>
            <Text style={styles.strong}>
              {station.station_name} —{" "}
              <Text style={station.status === "ALARM" ? styles.alarm : styles.warning}>
                {HYDRO_STATUS_LABEL[station.status]}
              </Text>
            </Text>
            <Text style={styles.body}>{hydroLevelLine(station)}</Text>
            <Text style={styles.meta}>{formatObservedAt(station.observed_at)}</Text>
            <FreshnessBadge state={freshness} label={HYDRO_FRESHNESS_LABEL[freshness]} />
          </View>
        ))}
      {summary?.kind === "list" && summary.more > 0 && <Text style={styles.meta}>i {summary.more} więcej</Text>}
      {hydro && <Text style={styles.micro}>{hydro.attribution}</Text>}
    </Card>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.heading, color: t.colors.text },
    scope: { ...typo.caption, color: t.colors.textSecondary, marginBottom: space.xs },
    body: { ...typo.body, color: t.colors.text },
    strong: { ...typo.strong, color: t.colors.text },
    meta: { ...typo.caption, color: t.colors.textSecondary },
    micro: { ...typo.micro, color: t.colors.textSecondary, marginTop: space.xs },
    warn: { ...typo.caption, color: t.colors.warning, fontWeight: "600" },
    error: { ...typo.caption, color: t.colors.danger, fontWeight: "600" },
    alarm: { color: t.colors.danger, fontWeight: "700" },
    warning: { color: t.colors.warning, fontWeight: "700" },
    item: {
      gap: 2,
      paddingTop: space.md,
      marginTop: space.xs,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: t.colors.border,
    },
  });
