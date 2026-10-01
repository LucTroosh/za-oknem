import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text } from "react-native";

import type { AlertsBlock } from "../lib/alerts";
import { summarizeAlerts } from "../lib/alerts";
import { type HomeBanner, homeAlertsBanner, homeHydroBanner } from "../lib/alertsBanner";
import { type HydroBlock, summarizeHydro } from "../lib/hydro";
import { MIN_TOUCH, radius, space, toneColors, typo } from "../lib/theme";
import useNow from "./useNow";
import useTheme, { useThemedStyles } from "./useTheme";

const GLYPH = { danger: "✕", warning: "▲", neutral: "○" } as const;

function Banner({ banner }: { banner: HomeBanner }) {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const { fg, bg } = toneColors(colors, banner.tone);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityHint="Otwiera zakładkę Alerty"
      onPress={() => router.navigate("/alerts")}
      style={[styles.box, { backgroundColor: bg, borderColor: fg }]}
    >
      <Text style={[styles.text, { color: fg }]}>
        {GLYPH[banner.tone]} {banner.text}
      </Text>
    </Pressable>
  );
}

// Up to two lines on Home about warnings and water levels; the lists live on the Alerts tab.
// `alertsLoaded` / `hydroLoaded`: that request has finished (with or without data). Once it
// has, missing data is a neutral "niedostępne" - never silence that reads as "all clear"
// (ADR-012; wording in lib/alertsBanner.ts).
export default function HomeBanners({
  alerts,
  alertsLoaded,
  hydro,
  hydroLoaded,
}: {
  alerts: AlertsBlock | null;
  alertsLoaded: boolean;
  hydro: HydroBlock | null;
  hydroLoaded: boolean;
}) {
  const now = useNow();
  const alertsBanner = alertsLoaded
    ? homeAlertsBanner(alerts ? summarizeAlerts(alerts, now) : null, alerts?.items.length ?? 0)
    : null;
  const hydroBanner = hydroLoaded
    ? homeHydroBanner(hydro ? summarizeHydro(hydro, now, Number.MAX_SAFE_INTEGER) : null)
    : null;
  return (
    <>
      {hydroBanner && <Banner banner={hydroBanner} />}
      {alertsBanner && <Banner banner={alertsBanner} />}
    </>
  );
}

const createStyles = () =>
  StyleSheet.create({
    box: {
      minHeight: MIN_TOUCH,
      justifyContent: "center",
      paddingHorizontal: space.lg,
      paddingVertical: space.sm,
      borderRadius: radius.md,
      borderWidth: 1,
    },
    text: { ...typo.strong },
  });
