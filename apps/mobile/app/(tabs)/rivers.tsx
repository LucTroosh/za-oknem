import { useState } from "react";
import { StyleSheet, Text } from "react-native";

import Button from "../../components/Button";
import Card from "../../components/Card";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import InfoBanner from "../../components/InfoBanner";
import PageHeader from "../../components/PageHeader";
import SearchField from "../../components/SearchField";
import SectionHeader from "../../components/SectionHeader";
import Screen from "../../components/Screen";
import StationRow from "../../components/StationRow";
import useNow from "../../components/useNow";
import { useThemedStyles } from "../../components/useTheme";
import { formatObservedAt } from "../../lib/dashboardTypes";
import { RIVERS_PAGE, buildRivers, limitGroups } from "../../lib/rivers";
import { type Theme, space, typo } from "../../lib/theme";

// S8: nearby IMGW gauges for the selected location; a geographic radius is not a catchment match.
export default function Rivers() {
  const d = useDashboard();
  const now = useNow();
  const styles = useThemedStyles(createStyles);
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(RIVERS_PAGE);
  const model = d.hydro ? buildRivers(d.hydro, now, query) : null;
  const shown = model ? limitGroups(model.groups, limit) : [];
  const shownCount = shown.reduce((n, g) => n + g.items.length, 0);
  if (d.hydro?.publication_enabled === false) {
    return <Screen padTop><PageHeader title="Stany rzek" /><EmptyState title="Stany rzek nie są jeszcze dostępne" message="Ten temat jest w przygotowaniu." /></Screen>;
  }
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh} gap={16}>
      <PageHeader title="Stany rzek" subtitle={d.hydro?.scope === "nearby" ? `Stacje IMGW w promieniu ${d.hydro.search_radius_km} km. Odległość nie oznacza powiązania z lokalną zlewnią.` : "Cała Polska: stacje wodowskazowe IMGW."} />
      {d.hydroState === "error" && d.hydro && <InfoBanner tone="warning" text="Nie udało się odświeżyć danych." detail="Pokazane informacje mogą być nieaktualne." />}
      {model && !model.sourceOk && (
        <InfoBanner tone="warning" text="Źródło nie odświeża się na bieżąco." detail={`Ostatnia udana aktualizacja: ${model.lastSuccessAt ? formatObservedAt(model.lastSuccessAt) : "brak"}. Stany mogą być nieaktualne.`} />
      )}
      {!d.hydro ? (
        d.hydroState === "loading" ? (
          <LoadingState label="Ładowanie stanów wody…" />
        ) : (
          <EmptyState
            title="Stany wody są niedostępne"
            message="Nie udało się pobrać danych. Spróbuj ponownie."
            actionLabel="Spróbuj ponownie"
            onAction={d.refresh}
          />
        )
      ) : (
        <>
          <SearchField
            value={query}
            onChangeText={(t) => {
              setQuery(t);
              setLimit(RIVERS_PAGE);
            }}
            placeholder="Szukaj stacji lub rzeki"
          />
          {model && model.total === 0 && (
            <Text style={styles.body}>{query.trim() === "" ? (d.hydro.scope === "nearby" ? `Brak pomiarów stacji IMGW w promieniu ${d.hydro.search_radius_km} km.` : "Brak stacji w danych.") : `Nie znaleziono stacji „${query.trim()}”.`}</Text>
          )}
          {shown.map((g) => (
            <Card key={g.key}>
              <SectionHeader title={g.title} />
              {g.note && <Text style={styles.scope}>{g.note}</Text>}
              {g.items.map((item, i) => (
                <StationRow key={item.station.station_id} item={item} first={i === 0} statusText={g.key === "outdated" ? "odczyt nieaktualny" : undefined} />
              ))}
            </Card>
          ))}
          {model && shownCount < model.total && (
            <Button variant="secondary" label={`Pokaż więcej (${model.total - shownCount})`} onPress={() => setLimit((n) => n + RIVERS_PAGE)} />
          )}
          <Text style={styles.micro}>{d.hydro.attribution}</Text>
        </>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    scope: { ...typo.caption, color: t.colors.textSecondary },
    body: { ...typo.body, color: t.colors.text },
    micro: { ...typo.meta, color: t.colors.textSecondary, marginBottom: space.md },
  });
