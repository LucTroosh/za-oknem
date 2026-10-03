import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { type LoadState, formatObservedAt } from "../lib/dashboardTypes";
import { type HydroBlock, summarizeHydro } from "../lib/hydro";
import { MIN_TOUCH, type Theme, space, typo } from "../lib/theme";
import Card from "./Card";
import { LoadingState } from "./EmptyState";
import InfoBanner from "./InfoBanner";
import SectionHeader from "./SectionHeader";
import SourceMeta from "./SourceMeta";
import StationRow from "./StationRow";
import useNow from "./useNow";
import useTheme, { useThemedStyles } from "./useTheme";

const lastSuccess = (at: string | null) => (at === null ? "brak udanej aktualizacji" : `ostatnia aktualizacja ${formatObservedAt(at)}`);

// Water levels (TASK-7.2 / 12.16): own request and own states, independent of the dashboard
// (rule #1). Nationwide until nearest-station matching, hence the "cała Polska" label. Statuses are
// IMGW's own thresholds via the backend; nothing here classifies a level (rule #10).
export default function HydroSection({ state, hydro }: { state: LoadState; hydro: HydroBlock | null }) {
  const styles = useThemedStyles(createStyles);
  const router = useRouter();
  const { colors } = useTheme();
  const now = useNow(); // labels age on the device without a refetch
  const summary = hydro ? summarizeHydro(hydro, now) : null;
  if (hydro?.publication_enabled === false) return null;
  return (
    <View style={styles.section}>
      <SectionHeader title="Stany wody" actionLabel={hydro ? "Wszystkie stacje" : undefined} onAction={() => router.push("/rivers")} />
      <Text style={styles.note}>Cała Polska: stacje w stanie ostrzegawczym lub alarmowym.</Text>
      {state === "loading" && !hydro && <LoadingState label="Ładowanie stanów wody…" />}
      {state === "error" && (
        <InfoBanner
          tone="warning"
          text={hydro ? "Nie udało się odświeżyć stanów wody." : "Stany wody są chwilowo niedostępne."}
          detail={hydro ? "Pokazane dane mogą być nieaktualne." : "Odśwież widok, aby spróbować ponownie."}
        />
      )}
      {summary?.kind === "unavailable" && (
        <InfoBanner tone="neutral" text="Dane o stanach wody są niedostępne lub nieaktualne." detail={`Źródło: ${lastSuccess(summary.lastSuccessAt)}.`} />
      )}
      {summary?.kind === "none-confirmed" && (
        <InfoBanner
          tone="good"
          text="Brak stacji w stanie ostrzegawczym lub alarmowym."
          detail={summary.unassessed > 0 ? `${summary.unassessed} stacji bez progów IMGW nie jest oceniane.` : undefined}
        />
      )}
      {summary?.kind === "list" && summary.outdated && <InfoBanner tone="warning" text="Lista może być nieaktualna." detail={`Źródło: ${lastSuccess(summary.lastSuccessAt)}.`} />}
      {summary?.kind === "list" && (
        <Card>
          {summary.items.map((item, i) => (
            <StationRow key={item.station.station_id} item={item} first={i === 0} />
          ))}
          {summary.more > 0 && <Text style={styles.note}>i {summary.more} więcej</Text>}
        </Card>
      )}
      {hydro && (
        <Pressable accessibilityRole="button" accessibilityLabel="Zobacz wszystkie stacje wodowskazowe" onPress={() => router.push("/rivers")} style={styles.link}>
          <Text style={styles.linkText}>Zobacz wszystkie stacje</Text>
          <Ionicons name="chevron-forward" size={18} color={colors.accent} importantForAccessibility="no" />
        </Pressable>
      )}
      {hydro && <SourceMeta lines={[hydro.attribution]} />}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    section: { gap: space.md },
    note: { ...typo.caption, color: t.colors.textSecondary },
    link: { flexDirection: "row", alignItems: "center", minHeight: MIN_TOUCH, alignSelf: "flex-start", gap: space.xs },
    linkText: { ...typo.strong, color: t.colors.accent },
  });
