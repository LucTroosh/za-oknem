import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { type AlertItem, alertKey } from "../lib/alerts";
import { GEO_MATCH_TEXT, areaNames } from "../lib/alertsScreen";
import { formatObservedAt } from "../lib/dashboardTypes";
import { FRESHNESS_LABEL } from "../lib/freshness";
import { severityTone } from "../lib/alertSeverity";
import { type Theme, elevation, radius, space, toneColors, typo } from "../lib/theme";
import FreshnessBadge from "./FreshnessBadge";
import IconBox from "./IconBox";
import useTheme, { useThemedStyles } from "./useTheme";

const SOURCE_NAME: Record<string, string> = { imgw_warningshydro: "IMGW · ostrzeżenie hydrologiczne" };

// One alert in the feed (production UI v1 §12): severity glyph in a 36 dp container, source meta,
// the source's own headline (rule #10: never rewritten), scope, validity, freshness, chevron.
// SEVERITY (card tint + glyph colour) comes only from the source's degree; `emphasis` is RELEVANCE
// to the user and is shown as a separate labelled chip, never as a danger colour.
const RELEVANCE = {
  local: { icon: "location", text: "Dotyczy Twojej lokalizacji" },
  check: { icon: "help-circle", text: "Do sprawdzenia" },
} as const;

export default function AlertCard({ alert, emphasis }: { alert: AlertItem; emphasis: "local" | "check" | "other" }) {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const regions = areaNames(alert.areas).join(", ");
  const geo = alert.geo_match ? GEO_MATCH_TEXT[alert.geo_match] : null;
  const tone = severityTone(alert.severity_raw);
  const { fg, bg: tint } = toneColors(colors, tone);
  const relevance = emphasis === "other" ? null : RELEVANCE[emphasis];
  const source = SOURCE_NAME[alert.source] ?? alert.source;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={[`${alert.event_type}, stopień ${alert.severity_raw}`, relevance?.text ?? null, source, regions || null, geo, `ważne do ${formatObservedAt(alert.valid_until)}`].filter(Boolean).join(", ")}
      accessibilityHint="Otwiera szczegóły ostrzeżenia"
      onPress={() => router.push({ pathname: "/alert", params: { key: alertKey(alert) } })}
      style={[styles.card, { backgroundColor: tone === "neutral" ? colors.surface : tint }]}
    >
      <IconBox name={tone === "neutral" ? "alert-circle" : "warning"} fg={fg} bg={colors.surface} size={36} iconSize={20} rounded={12} />
      <View style={styles.body}>
        {relevance && (
          <View style={styles.chip}>
            <Ionicons name={relevance.icon} size={14} color={colors.accent} importantForAccessibility="no" />
            <Text style={styles.chipText}>{relevance.text}</Text>
          </View>
        )}
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
    chip: { flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start", backgroundColor: t.colors.surface, borderRadius: radius.pill, paddingHorizontal: 8, paddingVertical: 2 },
    chipText: { ...typo.meta, fontWeight: "700", color: t.colors.accent },
    source: { ...typo.meta, color: t.colors.textSecondary },
    headline: { ...typo.cardTitle, color: t.colors.text },
    scope: { ...typo.caption, color: t.colors.text },
    geo: { ...typo.caption, color: t.colors.text, fontWeight: "700" },
    meta: { ...typo.meta, fontWeight: "400", color: t.colors.textSecondary },
  });
