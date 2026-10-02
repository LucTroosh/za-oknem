import { useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import Card from "../../components/Card";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import FreshnessBadge from "../../components/FreshnessBadge";
import HeroSurface from "../../components/HeroSurface";
import IconBox from "../../components/IconBox";
import InfoBanner from "../../components/InfoBanner";
import PageHeader from "../../components/PageHeader";
import Screen from "../../components/Screen";
import SourceMeta from "../../components/SourceMeta";
import useArea from "../../components/useArea";
import useTheme, { useThemedStyles } from "../../components/useTheme";
import { GEO_MATCH_TEXT, areaNames, findAlert } from "../../lib/alertsScreen";
import { formatObservedAt } from "../../lib/dashboardTypes";
import { FRESHNESS_LABEL } from "../../lib/freshness";
import { type Theme, space, typo } from "../../lib/theme";

// Alert detail (production UI v1 §11). Everything is the source's own text, verbatim (rule #10):
// no summary, no translation of degrees, no interpretation. "Co to oznacza?" is NOT drawn: it needs
// editorial text from the owner; without text the section does not exist.
export default function AlertDetails() {
  const { key } = useLocalSearchParams<{ key?: string }>();
  const d = useDashboard();
  const area = useArea();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const alert = findAlert(key, area?.local_alerts, d.alerts?.items);
  const regions = alert ? areaNames(alert.areas) : [];
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh} gap={16}>
      <PageHeader title="Ostrzeżenie" />
      {d.state === "error" && alert && <InfoBanner tone="warning" text="Nie udało się odświeżyć danych." detail="Pokazane informacje mogą być nieaktualne." />}
      {alert === null ? (
        d.state === "loading" ? (
          <LoadingState label="Ładowanie ostrzeżenia…" />
        ) : (
          <EmptyState art="noData" title="Tego ostrzeżenia nie ma już na liście" message="Mogło wygasnąć albo zostać zaktualizowane. Wróć do listy ostrzeżeń." />
        )
      ) : (
        <>
          <HeroSurface tint={colors.infoBg} minHeight={120}>
            <View style={styles.heroRow} accessible accessibilityRole="header" accessibilityLabel={`${alert.event_type}, stopień ${alert.severity_raw}`}>
              <IconBox name="alert-circle" fg={colors.info} bg={colors.surface} size={56} iconSize={30} rounded={18} />
              <View style={styles.heroTexts}>
                <Text style={styles.headline}>
                  {alert.event_type} (stopień {alert.severity_raw})
                </Text>
                {alert.geo_match ? <Text style={styles.geo}>{GEO_MATCH_TEXT[alert.geo_match]}</Text> : null}
                {regions.length > 0 && <Text style={styles.supporting}>{regions.join(", ")}</Text>}
              </View>
            </View>
            <FreshnessBadge state={alert.freshness} label={FRESHNESS_LABEL[alert.freshness]} />
          </HeroSurface>

          <Card>
            <Text style={styles.cardTitle} accessibilityRole="header">
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
            {alert.probability_pct !== null && <Text style={styles.meta}>Prawdopodobieństwo: {alert.probability_pct}%</Text>}
          </Card>

          <Card>
            <Text style={styles.cardTitle} accessibilityRole="header">
              Źródło
            </Text>
            <Text style={styles.strong}>Wydał: {alert.issuing_office}</Text>
            <Text style={styles.meta}>Opublikowano: {formatObservedAt(alert.published_at)}</Text>
            <Text style={styles.meta}>
              Ważne: {formatObservedAt(alert.valid_from)} – {formatObservedAt(alert.valid_until)}
            </Text>
            <Text style={styles.meta}>Pobrano: {formatObservedAt(alert.fetched_at)}</Text>
          </Card>
          <SourceMeta lines={[d.alerts?.attribution]} />
        </>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    heroRow: { flexDirection: "row", alignItems: "center", gap: space.lg },
    heroTexts: { flex: 1, gap: space.xs },
    headline: { ...typo.title, fontSize: 22, lineHeight: 28, fontWeight: "800", color: t.colors.text },
    geo: { ...typo.strong, color: t.colors.text },
    supporting: { ...typo.supporting, color: t.colors.textSecondary },
    cardTitle: { ...typo.cardTitle, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    strong: { ...typo.strong, color: t.colors.text },
    meta: { ...typo.meta, fontWeight: "400", color: t.colors.textSecondary },
  });
