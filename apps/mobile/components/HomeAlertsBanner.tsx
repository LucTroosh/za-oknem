import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text } from "react-native";

import type { AlertsBlock } from "../app/alerts";
import { summarizeAlerts } from "../app/alerts";
import { homeAlertsBanner } from "../app/alertsBanner";
import { MIN_TOUCH, radius, space, toneColors, typo } from "../app/theme";
import useNow from "./useNow";
import useTheme, { useThemedStyles } from "./useTheme";

// One line on Home about alerts; the list lives on the Alerts tab. Silent for a confirmed
// all-clear, never an all-clear when the source is silent (alertsBanner.ts, ADR-012).
export default function HomeAlertsBanner({ alerts }: { alerts: AlertsBlock }) {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const banner = homeAlertsBanner(summarizeAlerts(alerts, useNow()), alerts.items.length);
  if (!banner) return null;
  const { fg, bg } = toneColors(colors, banner.tone);
  return (
    <Pressable
      accessibilityRole="link"
      accessibilityHint="Otwiera zakładkę Alerty"
      onPress={() => router.navigate("/alerty")}
      style={[styles.box, { backgroundColor: bg, borderColor: fg }]}
    >
      <Text style={[styles.text, { color: fg }]}>
        {banner.tone === "warning" ? "▲ " : "○ "}
        {banner.text}
      </Text>
    </Pressable>
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
