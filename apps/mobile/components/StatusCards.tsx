import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { type ComponentProps, type ReactNode, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { DashboardArea } from "../lib/dashboardTypes";
import { gridDescription } from "../lib/coverage";
import { type ModuleKey, type StatusCardModel } from "../lib/home";
import { MIN_TOUCH, type Theme, radius, space, typo } from "../lib/theme";
import PollenCard from "./PollenCard";
import StatusGlyph from "./StatusGlyph";
import useTheme, { useThemedStyles } from "./useTheme";

type IconName = ComponentProps<typeof Ionicons>["name"];
const MODULE_ICON: Record<ModuleKey, IconName> = {
  air: "leaf-outline",
  weather: "partly-sunny-outline",
  pollen: "flower-outline",
};

const DETAIL_ROUTE: Partial<Record<ModuleKey, "/air" | "/weather">> = { air: "/air", weather: "/weather" };

// One status card (spec §12). Tap = progressive disclosure (§2.2): the full readings that
// used to sit on Home open inline until dedicated detail screens exist.
function StatusCard({ model, children }: { model: StatusCardModel; children: ReactNode }) {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const [open, setOpen] = useState(false);
  // Air and weather have their own detail screens (S5/S6); pollen still opens inline (S7 = TASK-12.14).
  const route = DETAIL_ROUTE[model.key] ?? null;
  const label = [model.title, model.headline, model.supporting, model.coverageNote, model.freshnessNote].filter(Boolean).join(". ");
  return (
    <View style={styles.wrap}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityHint={route ? "Otwiera szczegóły" : open ? "Zwija szczegóły" : "Rozwija szczegóły"}
        accessibilityState={route ? undefined : { expanded: open }}
        onPress={() => (route ? router.push(route) : setOpen((o) => !o))}
        style={styles.card}
      >
        <View style={styles.titleRow}>
          <Ionicons name={MODULE_ICON[model.key]} size={20} color={colors.textSecondary} />
          <Text style={styles.title} importantForAccessibility="no">
            {model.title}
          </Text>
          <Ionicons
            name={route ? "chevron-forward" : open ? "chevron-up" : "chevron-down"}
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
      {!route && open && <View style={styles.details}>{children}</View>}
    </View>
  );
}

// Weather and pollen are model values on a grid, not a measurement in the town (ADR-029 §5).
function GridNote({ text }: { text: string }) {
  const styles = useThemedStyles(createStyles);
  return <Text style={styles.micro}>{text}</Text>;
}

// Renders exactly the modules `cards` lists (data-driven, §50) - any length.
export default function StatusCards({ cards, area }: { cards: StatusCardModel[]; area: DashboardArea }) {
  const grid = gridDescription(area.coverage);
  // Air and weather open their own screens (DETAIL_ROUTE); only pollen expands inline.
  const details: Partial<Record<ModuleKey, ReactNode>> = {
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
          {details[c.key] ?? null}
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
    micro: { ...typo.micro, color: t.colors.textSecondary },
  });
