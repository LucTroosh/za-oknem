import { StyleSheet, Text, View } from "react-native";

import Card from "../../components/Card";
import DetailBack from "../../components/DetailBack";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import FreshnessBadge from "../../components/FreshnessBadge";
import Notice from "../../components/Notice";
import ReadingsList from "../../components/ReadingsList";
import Screen from "../../components/Screen";
import useArea from "../../components/useArea";
import useNow from "../../components/useNow";
import { useThemedStyles } from "../../components/useTheme";
import { gridDescription } from "../../lib/coverage";
import { formatObservedAt } from "../../lib/dashboardTypes";
import { forecastRows, sourceLine } from "../../lib/details";
import { FRESHNESS_LABEL, ageFreshness, worstFreshness } from "../../lib/freshness";
import { WEATHER_AGE } from "../../lib/readings";
import { type Theme, space, typo } from "../../lib/theme";
import { weatherView } from "../../lib/weather";

// S6 Szczegóły: Pogoda i prognoza (TASK-12.12), live only: every field the backend stores
// with its unit and age, the daily forecast, source status and attributions. Weather is a
// model value on a grid, not a measurement in the town (the grid note says so).
export default function WeatherDetails() {
  const d = useDashboard();
  const area = useArea();
  const now = useNow();
  const styles = useThemedStyles(createStyles);
  const weather = area?.weather ?? null;
  const status = d.sourceStatus?.weather;
  const view = weatherView(weather, now, status);
  const forecast = area?.forecast ?? null;
  const rows = forecastRows(forecast?.days);
  const source = sourceLine(weather?.source_status ?? status, now, WEATHER_AGE);
  const forecastState = forecast ? worstFreshness(forecast.freshness, ageFreshness(forecast.fetched_at, now, WEATHER_AGE)) : null;
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh}>
      <DetailBack title="Pogoda" />
      {d.state === "error" && area && <Notice tone="danger" text="Nie udało się odświeżyć. Pokazane dane mogą być nieaktualne." />}
      {area === null ? (
        d.state === "loading" ? (
          <LoadingState label="Ładowanie danych pogodowych…" />
        ) : (
          <EmptyState title="Brak danych do pokazania" message="Dane dla Twojej lokalizacji nie są jeszcze dostępne." actionLabel="Odśwież" onAction={d.refresh} />
        )
      ) : (
        <>
          <Card>
            <ReadingsList
              title="Teraz"
              view={view}
              emptyText="Brak danych pogodowych dla tej lokalizacji."
              unavailableText="Dane pogodowe są chwilowo niedostępne."
            />
            <Text style={styles.caption}>{gridDescription(area.coverage)}</Text>
          </Card>
          <Card>
            <Text style={styles.heading} accessibilityRole="header">
              Prognoza dobowa
            </Text>
            {rows.length === 0 ? (
              <Text style={styles.dim}>Brak prognozy dla tej lokalizacji.</Text>
            ) : (
              rows.map((r) => (
                <View key={r.key} style={styles.row}>
                  <Text style={styles.strong}>{r.day}</Text>
                  {r.range && <Text style={styles.body}>{r.range}</Text>}
                  {r.condition && <Text style={styles.body}>{r.condition}</Text>}
                  {r.precipitation && <Text style={styles.caption}>{r.precipitation}</Text>}
                </View>
              ))
            )}
            {forecast && forecastState && (
              <>
                <FreshnessBadge state={forecastState} label={forecastState === "UNAVAILABLE" ? "niedostępne" : FRESHNESS_LABEL[forecastState]} />
                <Text style={styles.caption}>Pobrano {formatObservedAt(forecast.fetched_at)}. Doby liczone w UTC.</Text>
                <Text style={styles.caption}>{forecast.attribution}</Text>
              </>
            )}
          </Card>
          <Card>
            <Text style={styles.heading} accessibilityRole="header">
              Źródło
            </Text>
            {weather?.observed_at && <Text style={styles.body}>Ostatni odczyt: {formatObservedAt(weather.observed_at)}</Text>}
            {source ? <FreshnessBadge state={source.state} label={source.text} /> : <Text style={styles.caption}>Brak informacji o statusie źródła.</Text>}
          </Card>
        </>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    heading: { ...typo.heading, color: t.colors.text },
    strong: { ...typo.strong, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    dim: { ...typo.body, color: t.colors.dim },
    caption: { ...typo.caption, color: t.colors.textSecondary },
    row: { gap: 2, paddingTop: space.sm, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: t.colors.border },
  });
