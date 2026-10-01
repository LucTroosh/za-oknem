
import AreaSection from "../../components/AreaSection";
import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import HomeAlertsBanner from "../../components/HomeAlertsBanner";
import Notice from "../../components/Notice";
import PollenCalendarCard from "../../components/PollenCalendarCard";
import Screen from "../../components/Screen";
import usePollenCalendar from "../../components/usePollenCalendar";

// Home = the dashboard: per location the outdoor verdict, air, weather, pollen. Alerts and
// water levels moved to the Alerts tab; only a one-line pointer stays here.
export default function Home() {
  const d = useDashboard();
  // Typical pollen season (ADR-023): own fetch, nationwide, once per screen.
  const calendar = usePollenCalendar(d.refreshTick);
  const hasAreas = d.areas.length > 0;

  return (
    <Screen refreshing={d.refreshing} onRefresh={d.refresh}>
      {d.alerts && <HomeAlertsBanner alerts={d.alerts} />}

      {/* Visible next to older data too: a failed refresh must not look like a fresh screen. */}
      {d.state === "error" && hasAreas && (
        <Notice tone="danger" text="Nie udało się odświeżyć. Pokazane dane mogą być nieaktualne." />
      )}

      {d.state === "loading" && !hasAreas && <LoadingState label="Ładowanie danych…" />}
      {d.state === "error" && !hasAreas && (
        <EmptyState
          title="Nie udało się pobrać danych"
          message="Sprawdź połączenie z internetem i spróbuj ponownie."
          actionLabel="Spróbuj ponownie"
          onAction={d.refresh}
          devHint="serwer API niedostępny? Sprawdź EXPO_PUBLIC_API_URL (README, sekcja Mobile)."
        />
      )}
      {d.state === "ready" && !hasAreas && (
        <EmptyState
          title="Brak danych do pokazania"
          message="Dane dla Twoich lokalizacji nie są jeszcze dostępne. Odśwież widok za chwilę."
          actionLabel="Odśwież"
          onAction={d.refresh}
          devHint="uruchom ingest na backendzie (README), potem odśwież."
        />
      )}

      {d.areas.map((area) => (
        <AreaSection key={area.slug} area={area} sourceStatus={d.sourceStatus} receivedAt={d.loadedAt} />
      ))}

      <PollenCalendarCard calendar={calendar.data} error={calendar.error} />
    </Screen>
  );
}
