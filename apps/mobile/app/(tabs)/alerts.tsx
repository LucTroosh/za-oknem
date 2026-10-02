import AlertsSection from "../../components/AlertsSection";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import HydroSection from "../../components/HydroSection";
import Notice from "../../components/Notice";
import Screen from "../../components/Screen";
import useArea from "../../components/useArea";
import { loadErrorArt } from "../../lib/stateArt";

// Alerts = IMGW warnings split by the backend's location matching (`area.local_alerts`, ADR-013:
// "Dla Twojej lokalizacji" / "Do sprawdzenia" (unresolved, never hidden) / "Pozostałe w Polsce")
// + water levels (still nationwide until the river screen, TASK-12.16). Alerts come with the
// dashboard response; water levels have their own fetch, so one failing never blanks the other.
export default function Alerts() {
  const d = useDashboard();
  const area = useArea();
  return (
    <Screen refreshing={d.refreshing} onRefresh={d.refresh}>
      {d.state === "error" && d.alerts && (
        <Notice tone="danger" text="Nie udało się odświeżyć. Pokazane dane mogą być nieaktualne." />
      )}
      {d.alerts ? (
        <AlertsSection alerts={d.alerts} localAlerts={area?.local_alerts ?? null} refreshFailed={d.state === "error"} />
      ) : d.state === "loading" ? (
        <LoadingState label="Ładowanie ostrzeżeń…" />
      ) : (
        <EmptyState
          art={loadErrorArt(d.networkFailure)}
          title="Ostrzeżenia są niedostępne"
          message="Nie udało się pobrać ostrzeżeń. Nie oznacza to, że ich nie ma. Spróbuj ponownie."
          actionLabel="Spróbuj ponownie"
          onAction={d.refresh}
          devHint="serwer API niedostępny? Sprawdź EXPO_PUBLIC_API_URL."
        />
      )}
      <HydroSection state={d.hydroState} hydro={d.hydro} />
    </Screen>
  );
}
