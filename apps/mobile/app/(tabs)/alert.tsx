import { useLocalSearchParams } from "expo-router";
import { StyleSheet, Text } from "react-native";

import Card from "../../components/Card";
import DetailBack from "../../components/DetailBack";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import FreshnessBadge from "../../components/FreshnessBadge";
import Notice from "../../components/Notice";
import Screen from "../../components/Screen";
import useArea from "../../components/useArea";
import { useThemedStyles } from "../../components/useTheme";
import { areaNames, findAlert, GEO_MATCH_TEXT } from "../../lib/alertsScreen";
import { formatObservedAt } from "../../lib/dashboardTypes";
import { FRESHNESS_LABEL } from "../../lib/freshness";
import { type Theme, space, typo } from "../../lib/theme";

// S3 Szczegół alertu (TASK-9.7). Everything is the source's own text, verbatim (rule #10): no
// summary, no translation of degrees, no interpretation. ("Co to oznacza?" does not exist: it
// needs editorial text the owner has not provided; without text the section is not drawn.)
export default function AlertDetails() {
  const { key } = useLocalSearchParams<{ key?: string }>();
  const d = useDashboard();
  const area = useArea();
  const styles = useThemedStyles(createStyles);
  const alert = findAlert(key, area?.local_alerts, d.alerts?.items);
  const regions = alert ? areaNames(alert.areas) : [];
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh}>
      <DetailBack title="Ostrzeżenie" />
      {d.state === "error" && alert && <Notice tone="danger" text="Nie udało się odświeżyć. Pokazane dane mogą być nieaktualne." />}
      {alert === null ? (
        d.state === "loading" ? (
          <LoadingState label="Ładowanie ostrzeżenia…" />
        ) : (
          <EmptyState
            title="Tego ostrzeżenia nie ma już na liście"
            message="Mogło wygasnąć albo zostać zaktualizowane. Wróć do listy ostrzeżeń."
          />
        )
      ) : (
        <>
          <Card>
            <Text style={styles.title} accessibilityRole="header">
              {alert.event_type} (stopień {alert.severity_raw})
            </Text>
            {alert.geo_match && <Text style={styles.geo}>{GEO_MATCH_TEXT[alert.geo_match]}</Text>}
            {regions.length > 0 && <Text style={styles.body}>Obszary: {regions.join(", ")}</Text>}
            <FreshnessBadge state={alert.freshness} label={FRESHNESS_LABEL[alert.freshness]} />
          </Card>
          <Card>
            <Text style={styles.heading} accessibilityRole="header">
              Oficjalny komunikat
            </Text>
            <Text style={styles.body} selectable>
              {alert.description}
            </Text>
            {alert.comment ? (
              <Text style={styles.body} selectable>
                {alert.comment}
              </Text>
            ) : null}
            {alert.probability_pct !== null && <Text style={styles.caption}>Prawdopodobieństwo: {alert.probability_pct}%</Text>}
          </Card>
          <Card>
            <Text style={styles.heading} accessibilityRole="header">
              Źródło
            </Text>
            <Text style={styles.body}>Wydał: {alert.issuing_office}</Text>
            <Text style={styles.caption}>Opublikowano: {formatObservedAt(alert.published_at)}</Text>
            <Text style={styles.caption}>
              Ważne: {formatObservedAt(alert.valid_from)} – {formatObservedAt(alert.valid_until)}
            </Text>
            <Text style={styles.caption}>Pobrano: {formatObservedAt(alert.fetched_at)}</Text>
            {d.alerts?.attribution && <Text style={styles.caption}>{d.alerts.attribution}</Text>}
          </Card>
        </>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.title, color: t.colors.danger },
    heading: { ...typo.heading, color: t.colors.text },
    geo: { ...typo.strong, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text, marginBottom: space.xs },
    caption: { ...typo.caption, color: t.colors.textSecondary },
  });
