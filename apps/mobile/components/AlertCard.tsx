import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { type AlertItem, alertKey } from "../lib/alerts";
import { GEO_MATCH_TEXT, areaNames } from "../lib/alertsScreen";
import { formatObservedAt } from "../lib/dashboardTypes";
import { FRESHNESS_LABEL } from "../lib/freshness";
import { type Theme, elevation, radius, space, typo } from "../lib/theme";
import FreshnessBadge from "./FreshnessBadge";
import IconBox from "./IconBox";
import useTheme, { useThemedStyles } from "./useTheme";

const SOURCE_NAME: Record<string, string> = { imgw_warningshydro: "IMGW · ostrzeżenie hydrologiczne" };

// One alert in the feed (production UI v1 §12): severity glyph in a 36 dp container, source meta,
// the source's own headline (rule #10: never rewritten), scope, validity, freshness, chevron.
// `emphasis` is RELEVANCE to the user, not our own severity rating: "local" gets a soft danger
// tint, "check" (unresolved) a soft warning tint, "other" the plain surface.
export default function AlertCard({ alert, emphasis }: { alert: AlertItem; emphasis: "local" | "check" | "other" }) {
  const router = useRouter();
  const { colors, scheme } = useTheme();
  const styles = useThemedStyles(createStyles);
  const regions = areaNames(alert.areas).join(", ");
  const geo = alert.geo_match ? GEO_MATCH_TEXT[alert.geo_match] : null;
  const tint = emphasis === "local" ? colors.dangerBg : emphasis === "check" ? colors.warningBg : scheme === "dark" ? colors.elevated : colors.surface;
  const fg = emphasis === "local" ? colors.danger : emphasis === "check" ? colors.warning : colors.textSecondary;
  const source = SOURCE_NAME[alert.source] ?? alert.source;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={[`${alert.event_type}, stopień ${alert.severity_raw}`, source, regions || null, geo, `ważne do ${formatObservedAt(alert.valid_until)}`].filter(Boolean).join(", ")}
      accessibilityHint="Otwiera szczegóły ostrzeżenia"
      onPress={() => router.push({ pathname: "/alert", params: { key: alertKey(alert) } })}
      style={[styles.card, { backgroundColor: tint }]}
    >
      <IconBox name={emphasis === "other" ? "alert-circle" : "warning"} fg={fg} bg={colors.surface} size={36} iconSize={20} rounded={12} />
      <View style={styles.body}>
        <Text style={styles.source}>{source}</Text>
        <Text style={styles.headline}>
          {alert.event_type} (stopień {alert.severity_raw})
        </Text>
        {regions !== "" && <Text style={styles.scope}>{regions}</Text>}
        {geo && <Text style={styles.geo}>{geo}</Text>}
        <Text style={styles.meta}>Ważne do {formatObservedAt(alert.valid_until)}</Text>
        <FreshnessBadge state={alert.freshness} label={FRESHNESS_LABEL[alert.freshness]} />
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} importantForAccessibility="no" />
    </Pressable>
  );

}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    card: { flexDirection: "row", alignItems: "center", gap: space.md, padding: 14, borderRadius: radius.card, minHeight: 72, ...elevation(t.scheme) },
    body: { flex: 1, gap: 4 },
    source: { ...typo.meta, color: t.colors.textSecondary },
    headline: { ...typo.cardTitle, color: t.colors.text },
    scope: { ...typo.caption, color: t.colors.text },
    geo: { ...typo.caption, color: t.colors.text, fontWeight: "700" },
    meta: { ...typo.meta, fontWeight: "400", color: t.colors.textSecondary },
  });
