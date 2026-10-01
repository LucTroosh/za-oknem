import { StyleSheet, Text, View } from "react-native";

import type { DashboardArea, DashboardSourceStatus } from "../lib/dashboardTypes";
import { formatObservedAt } from "../lib/dashboardTypes";
import { forecastLine } from "../lib/forecast";
import { FRESHNESS_LABEL } from "../lib/freshness";
import { type Theme, space, typo } from "../lib/theme";
import AirParams from "./AirParams";
import Card from "./Card";
import FreshnessBadge from "./FreshnessBadge";
import OutdoorCard from "./OutdoorCard";
import PollenCard from "./PollenCard";
import WeatherCard from "./WeatherCard";
import { useThemedStyles } from "./useTheme";

// One location on Home. Order = what the person decides on first: the outdoor verdict,
// then air, then weather (+ forecast), then pollen.
export default function AreaSection({
  area,
  sourceStatus,
  receivedAt,
}: {
  area: DashboardArea;
  sourceStatus: DashboardSourceStatus | null;
  receivedAt: number;
}) {
  const styles = useThemedStyles(createStyles);
  const forecast = area.forecast && forecastLine(area.forecast.days) ? area.forecast : null;
  return (
    <View style={styles.section}>
      <Text style={styles.name} accessibilityRole="header">
        {area.name}
      </Text>
      <OutdoorCard outdoor={area.outdoor} receivedAt={receivedAt} />
      <AirParams air={area.air} sourceStatus={sourceStatus?.air} receivedAt={receivedAt} />
      <WeatherCard weather={area.weather} sourceStatus={sourceStatus?.weather} />
      {forecast && (
        <Card>
          <Text style={styles.heading} accessibilityRole="header">
            Prognoza
          </Text>
          <Text style={styles.body}>{forecastLine(forecast.days)}</Text>
          <FreshnessBadge state={forecast.freshness} label={FRESHNESS_LABEL[forecast.freshness]} />
          <Text style={styles.micro}>
            {forecast.attribution} · pobrano {formatObservedAt(forecast.fetched_at)}
          </Text>
        </Card>
      )}
      <PollenCard pollen={area.pollen} />
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    section: { gap: space.md, marginTop: space.sm },
    name: { ...typo.title, color: t.colors.text },
    heading: { ...typo.heading, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    micro: { ...typo.micro, color: t.colors.textSecondary },
  });
