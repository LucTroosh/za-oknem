import { useMemo } from "react";

import AlertsStatus from "../../components/AlertsStatus";
import useDashboard from "../../components/DashboardProvider";
import EmptyState from "../../components/EmptyState";
import HeroVerdict from "../../components/HeroVerdict";
import HomeHeader from "../../components/HomeHeader";
import Notice from "../../components/Notice";
import PollenCalendarCard from "../../components/PollenCalendarCard";
import Screen from "../../components/Screen";
import { SkeletonCard } from "../../components/Skeleton";
import StatusCards from "../../components/StatusCards";
import useNow from "../../components/useNow";
import { summarizeAlerts } from "../../lib/alerts";
import { homeAlertsBanner, homeHydroBanner } from "../../lib/alertsBanner";
import { alertsStatus, currentTemperature, formatHeaderDate, sectionOrder, statusCards, verdictModel } from "../../lib/home";
import { summarizeHydro } from "../../lib/hydro";

// Start (spec §9-§17): header -> verdict -> status cards -> alerts (-> pollen calendar).
// The "what can I do today" section is not rendered: no backend for it yet. Modules load and
// fail independently (rule #1); one failing never blanks the screen.
export default function Start() {
  const d = useDashboard();
  const now = useNow();
  // TODO(TASK-12.7): the chosen location; until the picker exists, the first area.
  const area = d.areas[0] ?? null;
  const loading = d.state === "loading" && area === null;

  const alertsLoaded = d.state !== "loading";
  const hydroLoaded = d.hydroState !== "loading";
  const alerts = useMemo(
    () =>
      alertsStatus(
        [
          alertsLoaded ? homeAlertsBanner(d.alerts ? summarizeAlerts(d.alerts, now) : null, d.alerts?.items.length ?? 0) : null,
          hydroLoaded ? homeHydroBanner(d.hydro ? summarizeHydro(d.hydro, now, Number.MAX_SAFE_INTEGER) : null) : null,
        ],
        { alerts: alertsLoaded, hydro: hydroLoaded },
      ),
    [alertsLoaded, hydroLoaded, d.alerts, d.hydro, now],
  );

  const verdict = area ? verdictModel(area.outdoor, now, d.loadedAt) : null;
  const cards = area ? statusCards(area, d.sourceStatus, now, d.loadedAt) : [];

  const sections = {
    header: (
      <HomeHeader
        key="header"
        name={area?.name ?? null}
        loading={loading}
        dateText={formatHeaderDate(now)}
        temperature={area ? currentTemperature(area.weather, d.sourceStatus?.weather, now, true) : null}
      />
    ),
    verdict: loading ? (
      <SkeletonCard key="verdict" label="Ładowanie oceny warunków" lines={3} />
    ) : verdict ? (
      <HeroVerdict key="verdict" verdict={verdict} />
    ) : null,
    cards: loading ? (
      [0, 1, 2].map((i) => <SkeletonCard key={`sk${i}`} label="Ładowanie danych" />)
    ) : area ? (
      <StatusCards key="cards" cards={cards} area={area} sourceStatus={d.sourceStatus} receivedAt={d.loadedAt} />
    ) : d.state === "error" ? (
      <EmptyState
        key="cards"
        title="Nie udało się pobrać aktualnych danych"
        message="Sprawdź połączenie z internetem."
        actionLabel="Spróbuj ponownie"
        onAction={d.refresh}
        devHint="serwer API niedostępny? Sprawdź EXPO_PUBLIC_API_URL (README, sekcja Mobile)."
      />
    ) : (
      <EmptyState
        key="cards"
        title="Brak danych do pokazania"
        message="Dane dla Twojej lokalizacji nie są jeszcze dostępne. Odśwież widok za chwilę."
        actionLabel="Odśwież"
        onAction={d.refresh}
        devHint="uruchom ingest na backendzie (README), potem odśwież."
      />
    ),
    alerts: <AlertsStatus key="alerts" status={alerts} />,
    calendar: <PollenCalendarCard key="calendar" calendar={d.calendar} error={d.calendarError} />,
  };

  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh}>
      {sectionOrder(alerts).map((s) => sections[s])}
      {/* Failed refresh while older data is on screen: it must not look like a fresh screen. */}
      {d.state === "error" && area && (
        <Notice tone="danger" text="Nie udało się pobrać aktualnych danych. Pokazane dane mogą być nieaktualne." />
      )}
    </Screen>
  );
}
