import Ionicons from "@expo/vector-icons/Ionicons";
import { type ComponentProps, type ReactNode, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { DashboardArea, DashboardSourceStatus } from "../lib/dashboardTypes";
import { formatObservedAt } from "../lib/dashboardTypes";
import { gridDescription } from "../lib/coverage";
import { forecastLine } from "../lib/forecast";
import { FRESHNESS_LABEL } from "../lib/freshness";
import { type ModuleKey, type StatusCardModel } from "../lib/home";
import { MIN_TOUCH, type Theme, radius, space, typo } from "../lib/theme";
import AirParams from "./AirParams";
import Card from "./Card";
import FreshnessBadge from "./FreshnessBadge";
import PollenCard from "./PollenCard";
import StatusGlyph from "./StatusGlyph";
import WeatherCard from "./WeatherCard";
import useTheme, { useThemedStyles } from "./useTheme";

type IconName = ComponentProps<typeof Ionicons>["name"];
const MODULE_ICON: Record<ModuleKey, IconName> = {
  air: "leaf-outline",
  weather: "partly-sunny-outline",
  pollen: "flower-outline",
};

// One status card (spec §12). Tap = progressive disclosure (§2.2): the full readings that
// used to sit on Home open inline until dedicated detail screens exist.
function StatusCard({ model, children }: { model: StatusCardModel; children: ReactNode }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const [open, setOpen] = useState(false);
  const label = [model.title, model.headline, model.supporting, model.coverageNote, model.freshnessNote].filter(Boolean).join(". ");
  return (
    <View style={styles.wrap}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityHint={open ? "Zwija szczegóły" : "Rozwija szczegóły"}
        accessibilityState={{ expanded: open }}
        onPress={() => setOpen((o) => !o)}
        style={styles.card}
      >
        <View style={styles.titleRow}>
          <Ionicons name={MODULE_ICON[model.key]} size={20} color={colors.textSecondary} />
          <Text style={styles.title} importantForAccessibility="no">
            {model.title}
          </Text>
          <Ionicons
            name={open ? "chevron-up" : "chevron-down"}
            size={20}
            color={colors.textSecondary}
            style={styles.chevron}
          />
        </View>
        <View style={styles.headRow}>
          {model.level !== null && <StatusGlyph level={model.level} />}
          <Text style={[styles.headline, model.state === "unavailable" && styles.dim]}>{model.headline}</Text>
        </View>
        {model.supporting && <Text style={styles.supporting}>{model.supporting}</Text>}
        {model.coverageNote && <Text style={styles.coverage}>{model.coverageNote}</Text>}
        {model.freshnessNote && <Text style={styles.stale}>{model.freshnessNote}</Text>}
      </Pressable>
      {open && <View style={styles.details}>{children}</View>}
    </View>
  );
}

function ForecastCard({ forecast }: { forecast: NonNullable<DashboardArea["forecast"]> }) {
  const styles = useThemedStyles(createStyles);
  return (
    <Card>
      <Text style={styles.detailHeading} accessibilityRole="header">
        Prognoza
      </Text>
      <Text style={styles.body}>{forecastLine(forecast.days)}</Text>
      <FreshnessBadge state={forecast.freshness} label={FRESHNESS_LABEL[forecast.freshness]} />
      <Text style={styles.micro}>
        {forecast.attribution} · pobrano {formatObservedAt(forecast.fetched_at)}
      </Text>
    </Card>
  );
}

// Weather and pollen are model values on a grid, not a measurement in the town (ADR-029 §5).
function GridNote({ text }: { text: string }) {
  const styles = useThemedStyles(createStyles);
  return <Text style={styles.micro}>{text}</Text>;
}

// Renders exactly the modules `cards` lists (data-driven, §50) - any length.
export default function StatusCards({
  cards,
  area,
  sourceStatus,
  receivedAt,
}: {
  cards: StatusCardModel[];
  area: DashboardArea;
  sourceStatus: DashboardSourceStatus | null;
  receivedAt: number;
}) {
  const forecast = area.forecast && forecastLine(area.forecast.days) ? area.forecast : null;
  const grid = gridDescription(area.coverage);
  const details: Record<ModuleKey, ReactNode> = {
    air: <AirParams air={area.air} coverage={area.coverage} sourceStatus={sourceStatus?.air} receivedAt={receivedAt} />,
    weather: (
      <>
        <WeatherCard weather={area.weather} sourceStatus={sourceStatus?.weather} />
        {forecast && <ForecastCard forecast={forecast} />}
        <GridNote text={grid} />
      </>
    ),
    pollen: (
      <>
        <PollenCard pollen={area.pollen} />
        <GridNote text={grid} />
      </>
    ),
  };
  return (
    <>
      {cards.map((c) => (
        <StatusCard key={c.key} model={c}>
          {details[c.key]}
        </StatusCard>
      ))}
    </>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    wrap: { gap: space.sm },
    card: {
      minHeight: MIN_TOUCH,
      gap: space.xs,
      padding: space.lg,
      borderRadius: radius.md,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: t.colors.border,
      backgroundColor: t.colors.surface,
    },
    titleRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
    title: { ...typo.strong, color: t.colors.textSecondary, flex: 1 },
    chevron: { marginLeft: "auto" },
    headRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
    headline: { ...typo.title, color: t.colors.text, flexShrink: 1 },
    dim: { color: t.colors.dim },
    supporting: { ...typo.body, color: t.colors.textSecondary },
    coverage: { ...typo.caption, color: t.colors.textSecondary },
    stale: { ...typo.caption, color: t.colors.warning, fontWeight: "600" },
    details: { gap: space.sm },
    detailHeading: { ...typo.heading, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    micro: { ...typo.micro, color: t.colors.textSecondary },
  });
