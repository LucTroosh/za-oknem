import { useState } from "react";
import { StyleSheet, Text, TextInput } from "react-native";

import Button from "../../components/Button";
import Card from "../../components/Card";
import DetailBack from "../../components/DetailBack";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import Notice from "../../components/Notice";
import Screen from "../../components/Screen";
import StationRow from "../../components/StationRow";
import useNow from "../../components/useNow";
import useTheme, { useThemedStyles } from "../../components/useTheme";
import { formatObservedAt } from "../../lib/dashboardTypes";
import { RIVERS_PAGE, buildRivers, limitGroups } from "../../lib/rivers";
import { type Theme, radius, space, typo } from "../../lib/theme";

// S8 Stany rzek (TASK-12.16): every IMGW water-level station from /hydro/latest, nationwide
// (matching to the location is TASK-9.5). Live only; hydrology and nothing else.
export default function Rivers() {
  const d = useDashboard();
  const now = useNow();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(RIVERS_PAGE);
  const model = d.hydro ? buildRivers(d.hydro, now, query) : null;
  const shown = model ? limitGroups(model.groups, limit) : [];
  const shownCount = shown.reduce((n, g) => n + g.items.length, 0);
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh}>
      <DetailBack title="Stany rzek" />
      <Text style={styles.scope}>Cała Polska — stacje wodowskazowe IMGW z progami ostrzegawczym i alarmowym.</Text>
      {d.hydroState === "error" && d.hydro && <Notice tone="danger" text="Nie udało się odświeżyć. Pokazane dane mogą być nieaktualne." />}
      {model && !model.sourceOk && (
        <Notice
          tone="warning"
          text={`Źródło nie odświeża się na bieżąco (ostatnia udana aktualizacja: ${model.lastSuccessAt ? formatObservedAt(model.lastSuccessAt) : "brak"}). Stany mogą być nieaktualne.`}
        />
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
          <TextInput
            value={query}
            onChangeText={(t) => {
              setQuery(t);
              setLimit(RIVERS_PAGE);
            }}
            placeholder="Szukaj stacji lub rzeki"
            placeholderTextColor={colors.dim}
            accessibilityLabel="Szukaj stacji"
            style={styles.input}
            autoCorrect={false}
            maxLength={60}
            clearButtonMode="while-editing"
          />
          {model && model.total === 0 && (
            <Text style={styles.body}>{query.trim() === "" ? "Brak stacji w danych." : `Nie znaleziono stacji „${query.trim()}”.`}</Text>
          )}
          {shown.map((g) => (
            <Card key={g.key}>
              <Text style={styles.heading} accessibilityRole="header">
                {g.title}
              </Text>
              {g.note && <Text style={styles.scope}>{g.note}</Text>}
              {g.items.map((item) => (
                <StationRow key={item.station.station_id} item={item} statusText={g.key === "outdated" ? "odczyt nieaktualny" : undefined} />
              ))}
            </Card>
          ))}
          {model && shownCount < model.total && (
            <Button label={`Pokaż więcej (${model.total - shownCount})`} onPress={() => setLimit((n) => n + RIVERS_PAGE)} />
          )}
          <Text style={styles.micro}>{d.hydro.attribution}</Text>
        </>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    heading: { ...typo.heading, color: t.colors.text },
    scope: { ...typo.caption, color: t.colors.textSecondary },
    body: { ...typo.body, color: t.colors.text },
    micro: { ...typo.micro, color: t.colors.textSecondary },
    input: {
      ...typo.body,
      minHeight: 48,
      paddingHorizontal: space.lg,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: t.colors.border,
      backgroundColor: t.colors.surface,
      color: t.colors.text,
    },
  });
