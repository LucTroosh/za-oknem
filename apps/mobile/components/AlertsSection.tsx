import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text } from "react-native";

import { type AlertItem, type AlertsBlock, alertKey, summarizeAlerts } from "../lib/alerts";
import {
  GEO_MATCH_TEXT,
  LOCAL_NONE_TEXT,
  LOCAL_UNKNOWN_TEXT,
  NATIONAL_UNMATCHED_NOTE,
  UNRESOLVED_NOTE,
  areaNames,
  buildAlertsScreen,
} from "../lib/alertsScreen";
import { formatObservedAt } from "../lib/dashboardTypes";
import { FRESHNESS_LABEL } from "../lib/freshness";
import { MIN_TOUCH, type Theme, radius, space, typo } from "../lib/theme";
import Card from "./Card";
import FreshnessBadge from "./FreshnessBadge";
import useNow from "./useNow";
import { useThemedStyles } from "./useTheme";

const lastSuccess = (at: string | null) =>
  at === null ? "brak udanej aktualizacji" : `ostatnia aktualizacja ${formatObservedAt(at)}`;

// One alert in a list: the source's own title/degree/regions (rule #10), tap -> detail (S3).
function AlertCard({ alert }: { alert: AlertItem }) {
  const router = useRouter();
  const styles = useThemedStyles(createStyles);
  const regions = areaNames(alert.areas).join(", ");
  const geo = alert.geo_match ? GEO_MATCH_TEXT[alert.geo_match] : null;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${alert.event_type}, stopień ${alert.severity_raw}${regions ? `, ${regions}` : ""}`}
      accessibilityHint="Otwiera szczegóły ostrzeżenia"
      onPress={() => router.push({ pathname: "/alert", params: { key: alertKey(alert) } })}
      style={styles.item}
    >
      <Text style={styles.strong}>
        {alert.event_type} (stopień {alert.severity_raw})
      </Text>
      {regions !== "" && <Text style={styles.body}>{regions}</Text>}
      {geo && <Text style={styles.geo}>{geo}</Text>}
      <Text style={styles.meta}>
        do {formatObservedAt(alert.valid_until)} · {alert.issuing_office}
      </Text>
      <FreshnessBadge state={alert.freshness} label={FRESHNESS_LABEL[alert.freshness]} />
    </Pressable>
  );
}

// TASK-9.7 / ADR-013: IMGW hydrological alerts split by the backend's own location matching:
// "Dla Twojej lokalizacji" (`local_alerts`, voivodeship), "Do sprawdzenia" (`unresolved`, never
// hidden) and "Pozostałe w Polsce". Texts are verbatim from the source (rule #10). ADR-012:
// an all-clear is said only while every alert source is FRESH/RECENT.
export default function AlertsSection({
  alerts,
  localAlerts,
  refreshFailed = false,
}: {
  alerts: AlertsBlock;
  localAlerts?: AlertItem[] | null;
  refreshFailed?: boolean;
}) {
  const styles = useThemedStyles(createStyles);
  // Ages on the device clock: a FRESH status that crosses the bound stops claiming "brak
  // ostrzeżeń" without user action.
  const now = useNow();
  const summary = summarizeAlerts(alerts, now);
  const model = buildAlertsScreen(alerts, localAlerts, now, refreshFailed);
  return (
    <>
      <Card>
        <Text style={styles.title} accessibilityRole="header">
          {model.located ? "Dla Twojej lokalizacji" : "Ostrzeżenia hydrologiczne"}
        </Text>
        {!model.located && <Text style={styles.scope}>{NATIONAL_UNMATCHED_NOTE}</Text>}
        {summary.kind === "unavailable" && (
          <Text style={styles.body}>Nie udało się sprawdzić ostrzeżeń ({lastSuccess(summary.lastSuccessAt)}).</Text>
        )}
        {summary.kind === "list-maybe-outdated" && (
          <Text style={styles.warn}>Lista może być nieaktualna ({lastSuccess(summary.lastSuccessAt)}).</Text>
        )}
        {model.located && model.localStatus === "none-confirmed" && <Text style={styles.body}>{LOCAL_NONE_TEXT}.</Text>}
        {model.located && model.localStatus === "unknown" && summary.kind !== "unavailable" && model.local.length === 0 && (
          <Text style={styles.body}>{LOCAL_UNKNOWN_TEXT}: nie potwierdzamy braku ostrzeżeń.</Text>
        )}
        {model.local.map((a) => (
          <AlertCard key={alertKey(a)} alert={a} />
        ))}
        {!model.located && model.elsewhere.map((a) => <AlertCard key={alertKey(a)} alert={a} />)}
        <Text style={styles.micro}>{alerts.attribution}</Text>
      </Card>
      {model.unresolved.length > 0 && (
        <Card>
          <Text style={styles.title} accessibilityRole="header">
            Do sprawdzenia
          </Text>
          <Text style={styles.scope}>{UNRESOLVED_NOTE}</Text>
          {model.unresolved.map((a) => (
            <AlertCard key={alertKey(a)} alert={a} />
          ))}
        </Card>
      )}
      {model.located && model.elsewhere.length > 0 && (
        <Card>
          <Text style={styles.title} accessibilityRole="header">
            Pozostałe w Polsce
          </Text>
          <Text style={styles.scope}>Ostrzeżenia, które nie dotyczą Twojego województwa.</Text>
          {model.elsewhere.map((a) => (
            <AlertCard key={alertKey(a)} alert={a} />
          ))}
        </Card>
      )}
    </>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.heading, color: t.colors.text },
    scope: { ...typo.caption, color: t.colors.textSecondary, marginBottom: space.xs },
    body: { ...typo.body, color: t.colors.text },
    strong: { ...typo.strong, color: t.colors.danger },
    warn: { ...typo.caption, color: t.colors.warning, fontWeight: "600" },
    meta: { ...typo.caption, color: t.colors.textSecondary },
    geo: { ...typo.caption, color: t.colors.text, fontWeight: "600" },
    micro: { ...typo.micro, color: t.colors.textSecondary, marginTop: space.xs },
    item: {
      gap: 2,
      minHeight: MIN_TOUCH,
      paddingTop: space.md,
      marginTop: space.xs,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: t.colors.border,
      borderRadius: radius.sm,
    },
  });
