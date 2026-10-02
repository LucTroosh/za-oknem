import { useRouter } from "expo-router";
import { useMemo } from "react";

import AlertPreviewCard from "../../components/AlertPreviewCard";
import useDashboard from "../../components/DashboardProvider";
import useLocation from "../../components/LocationProvider";
import EmptyState from "../../components/EmptyState";
import HeroVerdict from "../../components/HeroVerdict";
import HomeHeader from "../../components/HomeHeader";
import InfoBanner from "../../components/InfoBanner";
import QuickStatusGrid from "../../components/QuickStatusGrid";
import Screen from "../../components/Screen";
import SourceMeta from "../../components/SourceMeta";
import { SkeletonCard } from "../../components/Skeleton";
import useNow from "../../components/useNow";
import { currentTemperature, formatHeaderDate, pollingOff, pollingPending, selectArea, verdictModel } from "../../lib/home";
import { todayRange } from "../../lib/forecast";
import { OUTDOOR_DISCLAIMER } from "../../lib/outdoor";
import { POLLING_OFF_NOTICE, POLLING_PENDING_NOTICE } from "../../lib/places";
import { alertPreview, currentWeatherIcon, quickTiles } from "../../lib/start";
import { loadErrorArt } from "../../lib/stateArt";

function hhmm(ms: number): string {
  const d = new Date(ms);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// Start (production UI v1 §7): answer first, data second. Compact header -> big verdict ->
// quick status tiles -> one alert preview -> secondary meta. "Co możesz dziś robić?" is not
// rendered: there is no production recommendation logic behind it (no mocks). Modules load and
// fail independently (rule #1): one failing never blanks the screen.
export default function Start() {
  const d = useDashboard();
  const now = useNow();
  const router = useRouter();
  const { settings } = useLocation();
  const location = settings.location;
  const area = useMemo(() => (location ? selectArea(d.areas, location.geoAreaId) : null), [d.areas, location]);
  const loading = d.state === "loading" && area === null;

  const verdict = area ? verdictModel(area.outdoor, now, d.loadedAt) : null;
  const tiles = area ? quickTiles(area, d.sourceStatus, now, d.loadedAt) : [];
  const preview = alertPreview(d.alerts, area?.local_alerts ?? null, now, d.state === "error", d.state === "loading");

  const pollingNotice = pollingOff(area) ? POLLING_OFF_NOTICE : pollingPending(area) ? POLLING_PENDING_NOTICE : null;

  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh} gap={12}>
      <HomeHeader
        name={location?.name ?? area?.name ?? null}
        loading={loading}
        onChangeLocation={() => router.push("/location")}
        dateText={formatHeaderDate(now)}
        temperature={area ? currentTemperature(area.weather, d.sourceStatus?.weather, now, true) : null}
        range={area ? todayRange(area.forecast, d.sourceStatus?.weather, now) : null}
        icon={area ? currentWeatherIcon(area.weather, d.sourceStatus?.weather, now) : null}
      />

      {/* A failed refresh while older data is on screen: right under the header, so cached data is not mistaken for fresh. */}
      {d.state === "error" && area && <InfoBanner tone="warning" text="Nie udało się odświeżyć danych." detail="Pokazane informacje mogą być nieaktualne." />}
      {pollingNotice && <InfoBanner tone="info" text={pollingNotice} />}

      {loading ? (
        <>
          <SkeletonCard label="Ładowanie oceny warunków" lines={3} minHeight={150} />
          <SkeletonCard label="Ładowanie danych" lines={2} minHeight={108} />
        </>
      ) : area ? (
        <>
          {verdict ? <HeroVerdict verdict={verdict} /> : null}
          {tiles.length > 0 && <QuickStatusGrid tiles={tiles} />}
          {preview && <AlertPreviewCard preview={preview} />}
          <SourceMeta
            lines={[
              `Dane odświeżone o ${hhmm(d.loadedAt)}. Źródła i licencje: Ustawienia.`,
              verdict ? OUTDOOR_DISCLAIMER : null,
            ]}
          />
        </>
      ) : d.state === "error" ? (
        <EmptyState
          art={loadErrorArt(d.networkFailure)}
          title="Nie udało się pobrać danych"
          message="Sprawdź połączenie z internetem i spróbuj ponownie."
          actionLabel="Spróbuj ponownie"
          onAction={d.refresh}
          devHint="serwer API niedostępny? Sprawdź EXPO_PUBLIC_API_URL (README, sekcja Mobile)."
        />
      ) : (
        <EmptyState
          art="noData"
          title="Brak danych do pokazania"
          message="Dane dla Twojej lokalizacji nie są jeszcze dostępne. Odśwież widok za chwilę."
          actionLabel="Odśwież"
          onAction={d.refresh}
          devHint="uruchom ingest na backendzie (README), potem odśwież."
        />
      )}
    </Screen>
  );
}
