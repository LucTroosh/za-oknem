import { StyleSheet, Text, View } from "react-native";

import { type AlertsBlock, alertAreasLabel, alertKey, summarizeAlerts } from "../lib/alerts";
import { formatObservedAt } from "../lib/dashboardTypes";
import { FRESHNESS_LABEL } from "../lib/freshness";
import { alertsArt } from "../lib/stateArt";
import { type Theme, space, typo } from "../lib/theme";
import Card from "./Card";
import FreshnessBadge from "./FreshnessBadge";
import StateIllustration from "./StateIllustration";
import useNow from "./useNow";
import { useThemedStyles } from "./useTheme";

const lastSuccess = (at: string | null) =>
  at === null ? "brak udanej aktualizacji" : `ostatnia aktualizacja ${formatObservedAt(at)}`;

// TASK-7.2: nationwide IMGW alerts, shown verbatim (rule #10). Labelled "cała Polska":
// an unfiltered alert must never look like it concerns the user's location (geo matching
// arrives with the location screen). ADR-012: "brak ostrzeżeń" only when every alert
// source is FRESH/RECENT; otherwise the source is silent and we say so.
export default function AlertsSection({ alerts, refreshFailed = false }: { alerts: AlertsBlock; refreshFailed?: boolean }) {
  const styles = useThemedStyles(createStyles);
  // Ages on the device clock: a FRESH status that crosses the bound stops claiming "brak
  // ostrzeżeń" without user action.
  const summary = summarizeAlerts(alerts, useNow());
  // A zero from cached data after a failed refresh is not a confirmed all-clear.
  const unconfirmedZero = refreshFailed && summary.kind === "none-confirmed";
  const art = alertsArt(summary, refreshFailed);
  return (
    <Card>
      {art ? <StateIllustration art={art} /> : null}
      <Text style={styles.title} accessibilityRole="header">
        Ostrzeżenia hydrologiczne
      </Text>
      <Text style={styles.scope}>Cała Polska — lista nie jest jeszcze dopasowana do Twojej lokalizacji.</Text>
      {summary.kind === "unavailable" && (
        <Text style={styles.body}>Nie udało się sprawdzić ostrzeżeń. Ostrzeżenia chwilowo niedostępne ({lastSuccess(summary.lastSuccessAt)}).</Text>
      )}
      {unconfirmedZero && (
        <Text style={styles.body}>Nie udało się odświeżyć ostrzeżeń, więc nie potwierdzamy ich braku.</Text>
      )}
      {summary.kind === "none-confirmed" && !unconfirmedZero && (
        <Text style={styles.body}>Brak aktywnych ostrzeżeń: {summary.sources.join(", ")}.</Text>
      )}
      {summary.kind === "list-maybe-outdated" && (
        <Text style={styles.warn}>Lista może być nieaktualna ({lastSuccess(summary.lastSuccessAt)}).</Text>
      )}
      {alerts.items.map((alert) => (
        <View key={alertKey(alert)} style={styles.item}>
          <Text style={styles.strong}>
            {alert.event_type} (stopień {alert.severity_raw})
          </Text>
          {alertAreasLabel(alert.areas) !== "" && <Text style={styles.body}>{alertAreasLabel(alert.areas)}</Text>}
          <Text style={styles.meta}>
            do {formatObservedAt(alert.valid_until)} · {alert.issuing_office}
          </Text>
          <FreshnessBadge state={alert.freshness} label={FRESHNESS_LABEL[alert.freshness]} />
        </View>
      ))}
      <Text style={styles.micro}>{alerts.attribution}</Text>
    </Card>
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
    micro: { ...typo.micro, color: t.colors.textSecondary, marginTop: space.xs },
    item: {
      gap: 2,
      paddingTop: space.md,
      marginTop: space.xs,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: t.colors.border,
    },
  });
