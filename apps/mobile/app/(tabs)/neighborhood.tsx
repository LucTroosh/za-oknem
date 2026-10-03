import { useCallback, useMemo, useState } from "react";
import { Text } from "react-native";

import EmptyState from "../../components/EmptyState";
import useLocation from "../../components/LocationProvider";
import NeighborhoodSectionCard from "../../components/NeighborhoodSectionCard";
import PageHeader from "../../components/PageHeader";
import Screen from "../../components/Screen";
import { SkeletonCard } from "../../components/Skeleton";
import SourceMeta from "../../components/SourceMeta";
import useNeighborhood from "../../components/useNeighborhood";
import { ENTRY_TITLE, SCREEN_INTRO, sectionView } from "../../lib/neighborhood";
import { loadErrorArt } from "../../lib/stateArt";

// "Twoja okolica" (ADR-032): historical / long-term / register data for the chosen location. A hidden
// tab screen reached from the entry row on Start (no tab, map, account or push). Sections load and
// fail independently (rule #1); this screen never calls an external source (rule #14).
export default function NeighborhoodScreen() {
  const { settings } = useLocation();
  const geoAreaId = settings.location?.geoAreaId ?? 0;
  const [tick, setTick] = useState(0);
  const { block, status } = useNeighborhood(geoAreaId, tick);
  const refresh = useCallback(() => setTick((t) => t + 1), []);
  const views = useMemo(() => (block ? block.sections.map(sectionView) : []), [block]);

  return (
    <Screen padTop refreshing={false} onRefresh={refresh} gap={12}>
      <PageHeader title={ENTRY_TITLE} backLabel="Start" />
      <SourceMeta lines={[SCREEN_INTRO]} />
      {views.length > 0 ? (
        views.map((v) => <NeighborhoodSectionCard key={v.id} view={v} />)
      ) : status === "loading" ? (
        <SkeletonCard label="Ładowanie danych o okolicy" lines={3} />
      ) : status === "error" ? (
        <EmptyState
          art={loadErrorArt(false)}
          title="Nie udało się pobrać danych"
          message="Sprawdź połączenie z internetem i spróbuj ponownie."
          actionLabel="Spróbuj ponownie"
          onAction={refresh}
        />
      ) : (
        <Text accessibilityRole="text">Dane o okolicy nie są jeszcze włączone.</Text>
      )}
    </Screen>
  );
}
