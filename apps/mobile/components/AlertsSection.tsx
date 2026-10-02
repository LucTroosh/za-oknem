import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { type AlertItem, type AlertsBlock, alertKey, summarizeAlerts } from "../lib/alerts";
import { LOCAL_NONE_TEXT, NATIONAL_UNMATCHED_NOTE, UNRESOLVED_NOTE, buildAlertsScreen } from "../lib/alertsScreen";
import { formatObservedAt } from "../lib/dashboardTypes";
import { alertsArt, localAlertsArt } from "../lib/stateArt";
import { MIN_TOUCH, type Theme, space, typo } from "../lib/theme";
import AlertCard from "./AlertCard";
import EmptyState from "./EmptyState";
import InfoBanner from "./InfoBanner";
import SectionHeader from "./SectionHeader";
import SourceMeta from "./SourceMeta";
import useNow from "./useNow";
import { useThemedStyles } from "./useTheme";

const lastSuccess = (at: string | null) => (at === null ? "brak udanej aktualizacji" : `ostatnia aktualizacja ${formatObservedAt(at)}`);

// Alert feed (production UI v1 §12), ordered by relevance: 1. for your location (`local_alerts`),
// 2. "needs checking" (unresolved, NEVER hidden), 3. the rest of Poland, collapsed. Texts are the
// source's own (rule #10). ADR-012: "Brak aktywnych ostrzeżeń" only while every alert source is
// FRESH/RECENT and the last refresh succeeded; otherwise "Nie udało się sprawdzić ostrzeżeń".
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
  const [showRest, setShowRest] = useState(false);
  const now = useNow(); // ages on the device clock: a FRESH status that crosses the bound stops claiming "brak"
  const summary = summarizeAlerts(alerts, now);
  const model = buildAlertsScreen(alerts, localAlerts, now, refreshFailed);
  const listed = model.local.length + model.unresolved.length > 0;
  const art = model.located ? localAlertsArt(model.localStatus, listed) : alertsArt(summary, refreshFailed);
  const lastSuccessText = summary.kind === "unavailable" || summary.kind === "list-maybe-outdated" ? lastSuccess(summary.lastSuccessAt) : null;
  const rest = model.located ? model.elsewhere : [];

  return (
    <>
      {summary.kind === "list-maybe-outdated" && (
        <InfoBanner tone="warning" text="Lista może być nieaktualna." detail={`Źródło: ${lastSuccessText}.`} />
      )}

      {model.located && model.localStatus === "none-confirmed" && (
        <EmptyState art={art ?? "noAlerts"} title={LOCAL_NONE_TEXT} message="Sprawdziliśmy aktualne ostrzeżenia dla Twojego województwa." />
      )}
      {model.located && model.localStatus === "unknown" && !listed && (
        <EmptyState
          art={art ?? "noData"}
          title="Nie udało się sprawdzić ostrzeżeń"
          message={lastSuccessText ? `Nie potwierdzamy braku ostrzeżeń (${lastSuccessText}).` : "Nie potwierdzamy braku ostrzeżeń."}
        />
      )}

      {model.local.length > 0 && (
        <View style={styles.section}>
          <SectionHeader title="Dla Twojej lokalizacji" />
          {model.local.map((a) => (
            <AlertCard key={alertKey(a)} alert={a} emphasis="local" />
          ))}
        </View>
      )}

      {model.unresolved.length > 0 && (
        <View style={styles.section}>
          <SectionHeader title="Do sprawdzenia" />
          <Text style={styles.note}>{UNRESOLVED_NOTE}</Text>
          {model.unresolved.map((a) => (
            <AlertCard key={alertKey(a)} alert={a} emphasis="check" />
          ))}
        </View>
      )}

      {!model.located && (
        <View style={styles.section}>
          <SectionHeader title="Ostrzeżenia hydrologiczne" />
          <Text style={styles.note}>{NATIONAL_UNMATCHED_NOTE}</Text>
          {summary.kind === "unavailable" && <InfoBanner tone="neutral" text="Nie udało się sprawdzić ostrzeżeń." detail={lastSuccessText ? `Źródło: ${lastSuccessText}.` : undefined} />}
          {model.elsewhere.map((a) => (
            <AlertCard key={alertKey(a)} alert={a} emphasis="other" />
          ))}
        </View>
      )}

      {rest.length > 0 && (
        <View style={styles.section}>
          <SectionHeader title="Pozostałe w Polsce" />
          <Text style={styles.note}>Ostrzeżenia, które nie dotyczą Twojego województwa.</Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={showRest ? "Ukryj pozostałe ostrzeżenia" : `Pokaż pozostałe ostrzeżenia: ${rest.length}`}
            accessibilityState={{ expanded: showRest }}
            onPress={() => setShowRest((v) => !v)}
            style={styles.toggle}
          >
            <Text style={styles.toggleText}>{showRest ? "Ukryj" : `Pokaż (${rest.length})`}</Text>
          </Pressable>
          {showRest && rest.map((a) => <AlertCard key={alertKey(a)} alert={a} emphasis="other" />)}
        </View>
      )}

      <SourceMeta lines={[alerts.attribution]} />
    </>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    section: { gap: space.md },
    note: { ...typo.caption, color: t.colors.textSecondary },
    toggle: { minHeight: MIN_TOUCH, justifyContent: "center", alignSelf: "flex-start" },
    toggleText: { ...typo.strong, color: t.colors.accent },
  });
