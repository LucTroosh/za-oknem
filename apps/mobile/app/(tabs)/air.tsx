import { StyleSheet, Text, View } from "react-native";

import AirIndexBadge from "../../components/AirIndexBadge";
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
import { airCoverage } from "../../lib/coverage";
import { airIndexDetail, airIndexUnavailableText, airStation, sourceLine } from "../../lib/details";
import { formatObservedAt } from "../../lib/dashboardTypes";
import { AIR_AGE, airView } from "../../lib/readings";
import { type Theme, space, typo } from "../../lib/theme";

// S5 Szczegóły: Powietrze (TASK-12.12), live only. Station, distance and how it was assigned,
// the EAQI with its components (only where the station speaks for "here"), every parameter
// with its age, source status and attribution. Rule #8: silent/regional/none -> no index.
export default function AirDetails() {
  const d = useDashboard();
  const area = useArea();
  const now = useNow();
  const styles = useThemedStyles(createStyles);
  const air = area?.air ?? null;
  const status = d.sourceStatus?.air;
  const view = airView(air, now, status);
  const station = airStation(air, area?.coverage);
  const cov = airCoverage(area?.coverage, air);
  const suppress = view === null || view.suppressDerived || view.unavailable;
  const index = airIndexDetail(air, area?.coverage, suppress, now, d.loadedAt);
  const source = sourceLine(air?.source_status ?? status, now, AIR_AGE);
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh}>
      <DetailBack title="Powietrze" />
      {d.state === "error" && area && <Notice tone="danger" text="Nie udało się odświeżyć. Pokazane dane mogą być nieaktualne." />}
      {area === null ? (
        d.state === "loading" ? (
          <LoadingState label="Ładowanie danych o powietrzu…" />
        ) : (
          <EmptyState title="Brak danych do pokazania" message="Dane dla Twojej lokalizacji nie są jeszcze dostępne." actionLabel="Odśwież" onAction={d.refresh} />
        )
      ) : (
        <>
          <Card>
            <Text style={styles.heading} accessibilityRole="header">
              Stacja pomiarowa
            </Text>
            {station ? (
              <>
                <Text style={styles.strong}>{station.name}</Text>
                {station.distance && <Text style={styles.body}>Odległość: {station.distance}</Text>}
                {station.method && <Text style={styles.body}>Dobrana jako: {station.method}</Text>}
                {station.coverage !== "" && <Text style={styles.caption}>{station.coverage}</Text>}
              </>
            ) : (
              <Text style={styles.body}>{cov.unavailable ? "Brak stacji pomiarowej w okolicy." : "Brak informacji o stacji."}</Text>
            )}
          </Card>
          <Card>
            <Text style={styles.heading} accessibilityRole="header">
              Indeks jakości powietrza
            </Text>
            {index ? (
              <>
                <AirIndexBadge index={air?.index} receivedAt={d.loadedAt} />
                {index.components.length > 0 && (
                  <View style={styles.rows}>
                    {index.components.map((c) => (
                      <Text key={c.param} style={styles.body}>
                        {c.param}: {c.label.toLowerCase()}
                        {index.dominant.includes(c.param) ? " (decyduje)" : ""}
                      </Text>
                    ))}
                  </View>
                )}
                {!index.complete && <Text style={styles.caption}>Zestaw niepełny: indeks jest dolnym ograniczeniem.</Text>}
                {index.gaps.length > 0 && <Text style={styles.caption}>Brakujące składowe: {index.gaps.join(", ")}.</Text>}
                {index.validUntil && <Text style={styles.caption}>Ważny do {formatObservedAt(index.validUntil)}.</Text>}
              </>
            ) : (
              <Text style={styles.body}>{airIndexUnavailableText(air, area.coverage, suppress)}</Text>
            )}
          </Card>
          <Card>
            <ReadingsList
              title="Pomiary"
              view={view}
              emptyText="Brak stacji pomiarowej w pobliżu."
              unavailableText="Dane o powietrzu są chwilowo niedostępne."
            />
          </Card>
          <Card>
            <Text style={styles.heading} accessibilityRole="header">
              Źródło
            </Text>
            {air?.observed_at && <Text style={styles.body}>Ostatni pomiar: {formatObservedAt(air.observed_at)}</Text>}
            {source && <FreshnessBadge state={source.state} label={source.text} />}
            {!source && <Text style={styles.caption}>Brak informacji o statusie źródła.</Text>}
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
    caption: { ...typo.caption, color: t.colors.textSecondary },
    rows: { gap: space.xs, marginTop: space.xs },
  });
