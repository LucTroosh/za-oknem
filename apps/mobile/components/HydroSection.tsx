import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text } from "react-native";

import { type LoadState, formatObservedAt } from "../lib/dashboardTypes";
import { type HydroBlock, summarizeHydro } from "../lib/hydro";
import { MIN_TOUCH, type Theme, space, typo } from "../lib/theme";
import Card from "./Card";
import StationRow from "./StationRow";
import useNow from "./useNow";
import { LoadingState } from "./EmptyState";
import useTheme, { useThemedStyles } from "./useTheme";

const lastSuccess = (at: string | null) =>
  at === null ? "brak udanej aktualizacji" : `ostatnia aktualizacja ${formatObservedAt(at)}`;

// TASK-7.2 (hydro): own request (DashboardProvider) and own states - independent of the dashboard (rule #1).
// Nationwide until geo matching - hence the "cała Polska" label. Statuses come from the
// backend (IMGW's own thresholds); nothing here classifies a level (rule #10).
export default function HydroSection({ state, hydro }: { state: LoadState; hydro: HydroBlock | null }) {
  const styles = useThemedStyles(createStyles);
  const router = useRouter();
  const { colors } = useTheme();
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
      {summary?.kind === "list" && summary.items.map((item) => <StationRow key={item.station.station_id} item={item} />)}
      {summary?.kind === "list" && summary.more > 0 && <Text style={styles.meta}>i {summary.more} więcej</Text>}
      {hydro && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Zobacz wszystkie stacje wodowskazowe"
          accessibilityHint="Otwiera listę stanów rzek"
          onPress={() => router.push("/rivers")}
          style={styles.link}
        >
          <Text style={styles.linkText}>Wszystkie stacje</Text>
          <Ionicons name="chevron-forward" size={18} color={colors.accent} importantForAccessibility="no" />
        </Pressable>
      )}
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
    link: { flexDirection: "row", alignItems: "center", minHeight: MIN_TOUCH, alignSelf: "flex-start", gap: space.xs },
    linkText: { ...typo.strong, color: t.colors.accent },
  });
