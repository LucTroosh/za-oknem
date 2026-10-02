import Ionicons from "@expo/vector-icons/Ionicons";
import { ScrollView, StyleSheet, Text, View } from "react-native";

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
import { gridDescription } from "../../lib/coverage";
import { formatObservedAt } from "../../lib/dashboardTypes";
import { forecastRows, sourceLine } from "../../lib/details";
import { hourlyStrip, todayRange } from "../../lib/forecast";
import { FRESHNESS_LABEL, ageFreshness, worstFreshness } from "../../lib/freshness";
import { WEATHER_AGE } from "../../lib/readings";
import { weatherHero, weatherMetrics } from "../../lib/start";
import { type Theme, space, typo } from "../../lib/theme";

// Weather (production UI v1 §9): current hero -> hourly strip -> measurement grid -> summary ->
// daily forecast -> source meta. Real data only: hours come from the 48 h model forecast, a missing
// field is omitted, methodology ("Prognoza dla Twojego obszaru") sits below, not in the hero.
export default function WeatherDetails() {
  const d = useDashboard();
  const area = useArea();
  const now = useNow();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const weather = area?.weather ?? null;
  const status = d.sourceStatus?.weather;
  const hero = weatherHero(weather, status, now);
  const range = area ? todayRange(area.forecast, status, now) : null;
  const strip = area ? hourlyStrip(area.forecast, status, now) : [];
  const metrics = weatherMetrics(weather, status, now);
  const forecast = area?.forecast ?? null;
  const rows = forecastRows(forecast?.days);
  const source = sourceLine(weather?.source_status ?? status, now, WEATHER_AGE);
  const forecastState = forecast ? worstFreshness(forecast.freshness, ageFreshness(forecast.fetched_at, now, WEATHER_AGE)) : null;
  const hasAny = hero.temp !== null || hero.condition !== null;
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh} gap={16}>
      <PageHeader title="Pogoda" />
      {d.state === "error" && area && <InfoBanner tone="warning" text="Nie udało się odświeżyć danych." detail="Pokazane informacje mogą być nieaktualne." />}
      {area === null ? (
        d.state === "loading" ? (
          <LoadingState label="Ładowanie danych pogodowych…" />
        ) : (
          <EmptyState art="noData" title="Brak danych do pokazania" message="Dane dla Twojej lokalizacji nie są jeszcze dostępne." actionLabel="Odśwież" onAction={d.refresh} />
        )
      ) : (
        <>
          <HeroSurface tint={colors.weatherBg} minHeight={140}>
            {hasAny ? (
              <View style={styles.heroRow} accessible accessibilityLabel={[hero.temp ? `Teraz ${hero.temp}` : null, hero.condition, range].filter(Boolean).join(", ")}>
                <IconBox name={hero.icon ?? "partly-sunny"} fg={colors.weatherFg} bg={colors.surface} size={64} iconSize={36} rounded={20} />
                <View style={styles.heroTexts}>
                  {hero.temp ? <Text style={styles.temp}>{hero.temp}</Text> : null}
                  {hero.condition ? <Text style={styles.condition}>{hero.condition}</Text> : null}
                  {range ? <Text style={styles.range}>{range}</Text> : null}
                </View>
              </View>
            ) : (
              <View style={styles.heroRow}>
                <IconBox name="help-circle" fg={colors.textSecondary} bg={colors.surface} size={56} iconSize={30} rounded={18} />
                <View style={styles.heroTexts}>
                  <Text style={styles.condition}>Dane pogodowe chwilowo niedostępne</Text>
                  <Text style={styles.range}>Spróbuj odświeżyć widok za chwilę.</Text>
                </View>
              </View>
            )}
          </HeroSurface>

          {strip.length > 0 && (
            <View style={styles.block}>
              <SectionHeader title="Najbliższe godziny" />
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.strip} accessibilityLabel="Prognoza godzinowa">
                {strip.map((h) => (
                  <View key={h.key} accessible accessibilityLabel={`${h.time}, ${h.temp}`} style={styles.cell}>
                    <Text style={styles.cellTime}>{h.time}</Text>
                    {h.icon ? <Ionicons name={h.icon} size={22} color={colors.weatherFg} importantForAccessibility="no" /> : <View style={styles.noIcon} />}
                    <Text style={styles.cellTemp}>{h.temp}</Text>
                  </View>
                ))}
              </ScrollView>
            </View>
          )}

          {metrics.length > 0 && (
            <View style={styles.block}>
              <SectionHeader title="Teraz" />
              <View style={styles.grid}>
                {metrics.map((m) => (
                  <MetricTile key={m.key} domain="weather" icon={m.icon} label={m.label} value={m.value} note={m.note} dim={m.dim} />
                ))}
              </View>
            </View>
          )}

          {hero.summary ? (
            <Card tint={colors.weatherBg}>
              <Text style={styles.cardTitle} accessibilityRole="header">
                W skrócie
              </Text>
              <Text style={styles.body}>{hero.summary}</Text>
            </Card>
          ) : null}

          {rows.length > 0 && (
            <View style={styles.block}>
              <SectionHeader title="Prognoza dobowa" />
              <Card>
                {rows.map((r, i) => (
                  <View key={r.key} style={[styles.dayRow, i > 0 && styles.divider]}>
                    <Text style={styles.dayName}>{r.day}</Text>
                    <Text style={styles.dayValue}>{[r.range, r.condition].filter(Boolean).join(" · ")}</Text>
                    {r.precipitation ? <Text style={styles.meta}>{r.precipitation}</Text> : null}
                  </View>
                ))}
                {forecast && forecastState && (
                  <FreshnessBadge state={forecastState} label={forecastState === "UNAVAILABLE" ? "niedostępne" : FRESHNESS_LABEL[forecastState]} />
                )}
              </Card>
            </View>
          )}

          <SourceMeta
            lines={[
              gridDescription(area.coverage),
              weather?.observed_at ? `Ostatni odczyt: ${formatObservedAt(weather.observed_at)}.` : null,
              source?.text ?? null,
              forecast ? `Prognoza pobrana ${formatObservedAt(forecast.fetched_at)}, doby liczone w UTC.` : null,
              weather?.attribution ?? null,
              forecast?.attribution && forecast.attribution !== weather?.attribution ? forecast.attribution : null,
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
    heroTexts: { flex: 1, gap: 2 },
    temp: { fontSize: 44, lineHeight: 50, fontWeight: "800", color: t.colors.text },
    condition: { ...typo.strong, fontSize: 15, color: t.colors.text },
    range: { ...typo.caption, color: t.colors.textSecondary },
    strip: { gap: space.sm, paddingVertical: space.xs },
    cell: { width: 62, alignItems: "center", gap: 6, paddingVertical: space.sm, borderRadius: 16, backgroundColor: t.scheme === "dark" ? t.colors.elevated : t.colors.surface },
    cellTime: { ...typo.meta, color: t.colors.textSecondary },
    cellTemp: { ...typo.strong, color: t.colors.text },
    noIcon: { width: 22, height: 22 },
    grid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
    cardTitle: { ...typo.cardTitle, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    dayRow: { gap: 2, paddingVertical: space.sm },
    divider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: t.colors.border },
    dayName: { ...typo.strong, color: t.colors.text },
    dayValue: { ...typo.supporting, color: t.colors.text },
    meta: { ...typo.meta, color: t.colors.textSecondary },
  });
