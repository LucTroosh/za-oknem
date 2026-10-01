import AlertsSection from "../../components/AlertsSection";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import HydroSection from "../../components/HydroSection";
import Notice from "../../components/Notice";
import Screen from "../../components/Screen";

// (Route is "alerty", not "alerts": app/alerts.ts, the logic module, would otherwise collide
// with it as a route.)
// Alerts = IMGW warnings + water levels, both nationwide until the location screen brings
// geo matching (backend `local_alerts` / `?geo_area_id=` exist but are not used here yet).
// Alerts come with the dashboard response (same data as /alerts/latest, plus the
// attribution); water levels have their own fetch, so one failing never blanks the other.
export default function Alerts() {
  const d = useDashboard();
  return (
    <Screen refreshing={d.refreshing} onRefresh={d.refresh}>
      {d.state === "error" && d.alerts && (
        <Notice tone="danger" text="Nie udało się odświeżyć. Pokazane dane mogą być nieaktualne." />
      )}
      {d.alerts ? (
        <AlertsSection alerts={d.alerts} />
      ) : d.state === "loading" ? (
        <LoadingState label="Ładowanie ostrzeżeń…" />
      ) : (
        <EmptyState
          title="Ostrzeżenia są niedostępne"
          message="Nie udało się pobrać ostrzeżeń. Nie oznacza to, że ich nie ma. Spróbuj ponownie."
          actionLabel="Spróbuj ponownie"
          onAction={d.refresh}
          devHint="serwer API niedostępny? Sprawdź EXPO_PUBLIC_API_URL."
        />
      )}
      <HydroSection refreshTick={d.refreshTick} />
    </Screen>
  );
}
