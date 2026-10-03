import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import AirHistoryCard from "../../components/AirHistoryCard";
import AirScale from "../../components/AirScale";
import Card from "../../components/Card";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import FreshnessBadge from "../../components/FreshnessBadge";
import HeroSurface from "../../components/HeroSurface";
import IconBox from "../../components/IconBox";
import InfoBanner from "../../components/InfoBanner";
import MetricTile from "../../components/MetricTile";
import PageHeader from "../../components/PageHeader";
import Screen from "../../components/Screen";
import SectionHeader from "../../components/SectionHeader";
import SourceMeta from "../../components/SourceMeta";
import useArea from "../../components/useArea";
import useNow from "../../components/useNow";
import useTheme, { useThemedStyles } from "../../components/useTheme";
import { airCoverage } from "../../lib/coverage";
import { formatObservedAt } from "../../lib/dashboardTypes";
import { airHero, airIndexDetail, airMeaning, airMetrics, airStation, sourceLine } from "../../lib/details";
import { AIR_AGE, airView } from "../../lib/readings";
import { type Theme, space, toneColors, typo } from "../../lib/theme";

// Air (production UI v1 §10): status hero (human headline + the real EEA scale) -> pollutant tiles
// -> "Co to oznacza?" -> station / coverage / source below, visually secondary. Rule #8: with a
// silent, regional or missing station there is no index and no good-looking value.
export default function AirDetails() {
  const [historyTick, setHistoryTick] = useState(0);
  const d = useDashboard();
  const area = useArea();
  const now = useNow();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const air = area?.air ?? null;
  const status = d.sourceStatus?.air;
  const view = airView(air, now, status);
  const suppress = view === null || view.suppressDerived || view.unavailable;
  const hero = airHero(air, area?.coverage, suppress, now, d.loadedAt);
  const detail = airIndexDetail(air, area?.coverage, suppress, now, d.loadedAt);
  const meaning = airMeaning(detail);
  const metrics = airMetrics(air, now, status);
  const station = airStation(air, area?.coverage);
  const cov = airCoverage(area?.coverage, air);
  const source = sourceLine(air?.source_status ?? status, now, AIR_AGE);
  const { fg, bg } = toneColors(colors, hero.tone);
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={() => { setHistoryTick((n) => n + 1); d.refresh(); }} gap={16}>
      <PageHeader title="Powietrze" />
      {d.state === "error" && area && <InfoBanner tone="warning" text="Nie udało się odświeżyć danych." detail="Pokazane informacje mogą być nieaktualne." />}
      {area === null ? (
        d.state === "loading" ? (
          <LoadingState label="Ładowanie danych o powietrzu…" />
        ) : (
          <EmptyState art="noData" title="Brak danych do pokazania" message="Dane dla Twojej lokalizacji nie są jeszcze dostępne." actionLabel="Odśwież" onAction={d.refresh} />
        )
      ) : (
        <>
          <HeroSurface tint={hero.tone === "neutral" ? colors.neutralBg : bg} minHeight={130}>
            <View style={styles.heroRow} accessible accessibilityRole="header" accessibilityLabel={`${hero.headline}. ${hero.supporting}`}>
              <IconBox name="leaf" fg={fg} bg={colors.surface} size={56} iconSize={30} rounded={18} />
              <View style={styles.heroTexts}>
                <Text style={styles.headline}>{hero.headline}</Text>
                <Text style={styles.supporting}>{hero.supporting}</Text>
              </View>
            </View>
            {hero.step !== null && <AirScale step={hero.step} tone={hero.tone} />}
          </HeroSurface>

          {metrics.length > 0 ? (
            <View style={styles.block}>
              <SectionHeader title="Pomiary" />
              <View style={styles.grid}>
                {metrics.map((m) => (
                  <MetricTile key={m.key} domain="air" label={m.label} value={m.value} note={m.note} dim={m.dim} />
                ))}
              </View>
            </View>
          ) : (
            <InfoBanner tone="neutral" text={cov.unavailable ? "Brak stacji pomiarowej w okolicy." : "Pomiary powietrza są chwilowo niedostępne."} />
          )}

          <AirHistoryCard key={area.geo_area_id} geoAreaId={area.geo_area_id} refreshTick={historyTick} />

          {meaning.length > 0 && (
            <Card tint={colors.infoBg}>
              <Text style={styles.cardTitle} accessibilityRole="header">
                Co to oznacza?
              </Text>
              {meaning.map((l) => (
                <Text key={l} style={styles.body}>
                  {l}
                </Text>
              ))}
            </Card>
          )}

          <Card>
            <Text style={styles.cardTitle} accessibilityRole="header">
              Stacja pomiarowa
            </Text>
            {station ? (
              <>
                <Text style={styles.strong}>{station.name}</Text>
                <Text style={styles.supportingDark}>{[station.distance ? `${station.distance} od Ciebie` : null, station.method].filter(Boolean).join(" · ")}</Text>
                {station.coverage !== "" && <Text style={styles.meta}>{station.coverage}</Text>}
              </>
            ) : (
              <Text style={styles.supportingDark}>{cov.unavailable ? "W okolicy nie ma stacji pomiarowej." : "Brak informacji o stacji."}</Text>
            )}
            {source ? <FreshnessBadge state={source.state} label={source.text.replace(/^Status źródła: /, "")} /> : null}
          </Card>

          <SourceMeta
            lines={[
              air?.observed_at ? `Ostatni pomiar: ${formatObservedAt(air.observed_at)}.` : null,
              detail?.validUntil ? `Indeks ważny do ${formatObservedAt(detail.validUntil)}.` : null,
              air?.attribution ?? null,
            ]}
          />
        </>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    block: { gap: space.md },
    heroRow: { flexDirection: "row", alignItems: "center", gap: space.lg },
    heroTexts: { flex: 1, gap: space.xs },
    headline: { ...typo.title, fontSize: 22, lineHeight: 28, fontWeight: "800", color: t.colors.text },
    supporting: { ...typo.supporting, color: t.colors.textSecondary },
    grid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
    cardTitle: { ...typo.cardTitle, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    strong: { ...typo.strong, color: t.colors.text },
    supportingDark: { ...typo.supporting, color: t.colors.text },
    meta: { ...typo.meta, color: t.colors.textSecondary },
  });
