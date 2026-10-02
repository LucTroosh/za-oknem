import AlertsSection from "../../components/AlertsSection";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import HydroSection from "../../components/HydroSection";
import InfoBanner from "../../components/InfoBanner";
import { TabTitle } from "../../components/PageHeader";
import Screen from "../../components/Screen";
import useArea from "../../components/useArea";
import { loadErrorArt } from "../../lib/stateArt";

// Alerty (production UI v1 §11): a consumer alert feed ordered by relevance (your location first),
// then water levels. Alerts come with the dashboard response; water levels have their own fetch,
// so one failing never blanks the other.
export default function Alerts() {
  const d = useDashboard();
  const area = useArea();
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh} gap={16}>
      <TabTitle title="Alerty" />
      {d.state === "error" && d.alerts && <InfoBanner tone="warning" text="Nie udało się odświeżyć ostrzeżeń." detail="Pokazane informacje mogą być nieaktualne." />}
      {d.alerts ? (
        <AlertsSection alerts={d.alerts} localAlerts={area?.local_alerts ?? null} refreshFailed={d.state === "error"} />
      ) : d.state === "loading" ? (
        <LoadingState label="Ładowanie ostrzeżeń…" />
      ) : (
        <EmptyState
          art={loadErrorArt(d.networkFailure)}
          title="Nie udało się sprawdzić ostrzeżeń"
          message="Nie potwierdzamy, że ich nie ma. Spróbuj ponownie."
          actionLabel="Spróbuj ponownie"
          onAction={d.refresh}
          devHint="serwer API niedostępny? Sprawdź EXPO_PUBLIC_API_URL."
        />
      )}
      <HydroSection state={d.hydroState} hydro={d.hydro} />
    </Screen>
  );
}
