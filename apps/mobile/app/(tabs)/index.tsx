import { useRouter } from "expo-router";
import { useMemo } from "react";

import AlertsStatus from "../../components/AlertsStatus";
import useDashboard from "../../components/DashboardProvider";
import useLocation from "../../components/LocationProvider";
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
import { todayRange } from "../../lib/forecast";
import { homeAlertsBanner, homeHydroBanner } from "../../lib/alertsBanner";
import { alertsStatus, currentTemperature, formatHeaderDate, pollingOff, pollingPending, sectionOrder, selectArea, statusCards, verdictModel } from "../../lib/home";
import { summarizeHydro } from "../../lib/hydro";
import { showAlertsStatus, showPollenCalendar, visibleCards } from "../../lib/topics";
import { POLLING_OFF_NOTICE, POLLING_PENDING_NOTICE } from "../../lib/places";

// Start (spec §9-§17): header -> verdict -> status cards -> alerts (-> pollen calendar).
// The "what can I do today" section is not rendered: no backend for it yet. Modules load and
// fail independently (rule #1); one failing never blanks the screen.
export default function Start() {
  const d = useDashboard();
  const now = useNow();
  const router = useRouter();
  const { settings } = useLocation();
  const location = settings.location;
  const area = useMemo(() => (location ? selectArea(d.areas, location.geoAreaId) : null), [d.areas, location]);
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
        // A failed refresh keeps the cached blocks: never re-confirm an all-clear from them.
        { alerts: d.state === "error", hydro: d.hydroState === "error" },
      ),
    [alertsLoaded, hydroLoaded, d.alerts, d.hydro, d.state, d.hydroState, now],
  );

  const verdict = area ? verdictModel(area.outdoor, now, d.loadedAt) : null;
  const topics = settings.topics;
  // Local topic choice (TASK-12.13): a hidden topic is a missing card. The verdict stays (it needs
  // air + weather itself) and a real warning banner is never hidden (lib/topics.ts).
  const cards = area ? visibleCards(statusCards(area, d.sourceStatus, now, d.loadedAt), topics) : [];

  // Failed refresh while older data is on screen: right under the header, before the cached
  // sections, so it does not look like a fresh screen.
  const notice =
    d.state === "error" && area ? (
      <Notice key="notice" tone="danger" text="Nie udało się pobrać aktualnych danych. Pokazane dane mogą być nieaktualne." />
    ) : null;

  // No weather polling for this place (capacity / budget / expired): say why the weather and
  // pollen cards are empty, instead of leaving it looking broken (ADR-026/029).
  const pollingNotice = pollingOff(area) ? (
    <Notice key="polling" tone="warning" text={POLLING_OFF_NOTICE} />
  ) : pollingPending(area) ? (
    <Notice key="polling" tone="warning" text={POLLING_PENDING_NOTICE} />
  ) : null;

  const sections = {
    header: (
      <HomeHeader
        key="header"
        name={location?.name ?? area?.name ?? null}
        loading={loading}
        onChangeLocation={() => router.push("/location")}
        dateText={formatHeaderDate(now)}
        range={area ? todayRange(area.forecast, d.sourceStatus?.weather, now) : null}
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
      <StatusCards key="cards" cards={cards} area={area} />
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
    alerts: showAlertsStatus(alerts, topics) ? <AlertsStatus key="alerts" status={alerts} /> : null,
    calendar: !showPollenCalendar(topics) ? null : d.calendar === null && !d.calendarError ? (
      <SkeletonCard key="calendar" label="Ładowanie kalendarza pylenia" lines={2} />
    ) : (
      <PollenCalendarCard key="calendar" calendar={d.calendar} error={d.calendarError} />
    ),
  };

  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh}>
      {sectionOrder(alerts).flatMap((s) => (s === "header" ? [sections.header, notice, pollingNotice] : [sections[s]]))}
    </Screen>
  );
}
