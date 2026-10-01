import { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";

import AirIndexBadge from "../components/AirIndexBadge";
import AirParams from "../components/AirParams";
import OutdoorCard from "../components/OutdoorCard";
import PollenCard from "../components/PollenCard";
import WeatherCard from "../components/WeatherCard";
import { type AlertsBlock, alertAreasLabel, alertKey, summarizeAlerts } from "./alerts";
import { apiGet } from "./api";
import { type ForecastDay, forecastLine } from "./forecast";
import { FRESHNESS_LABEL, type Freshness, type FreshnessState } from "./freshness";
import {
  HYDRO_FRESHNESS_LABEL,
  HYDRO_STATUS_LABEL,
  type HydroBlock,
  hydroLevelLine,
  summarizeHydro,
} from "./hydro";

// No shared api-contract package yet (packages/api-contract is still a
// placeholder) — hand-typed here, one endpoint doesn't justify generating an
// OpenAPI client.
//
// Freshness labels are the server's own (app/api/v1/dashboard.py, per-domain thresholds,
// ADR-004). The client never upgrades one; it only combines it with `source_status`
// (worst wins, ADR-012) and ages it on the device clock (app/readings.ts, TASK-7.3).
type DashboardArea = {
  geo_area_id: number;
  slug: string;
  name: string;
  air: {
    station_name: string;
    // TASK-7.1: source transparency (Master Plan Principle 2) — server-provided
    // attribution text, never hardcoded/reworded on the client. This top-level
    // observed_at is only the newest of any param at this station (dashboard.py)
    // — a rough station-level summary, not authoritative for any single
    // pollutant (Codex review, round 3): render each param's OWN observed_at
    // (below) next to that param, not this one.
    attribution: string;
    observed_at: string;
    // TASK-4.1: full GIOŚ param set (PM2.5/PM10/NO2/SO2/O3/CO/C6H6), not just PM2.5
    // — freshness AND observed_at are per-param since each param can be observed
    // at a different time (dashboard.py already returns both per param).
    params: Record<
      string,
      { value: number; unit: string; observed_at: string; freshness: Freshness }
    >;
    // TASK-4.2: optional - absent on an older backend; the badge renders nothing then.
    index?: unknown;
    // TASK-7.3 / ADR-012: optional - absent on an older backend.
    source_status?: { freshness: FreshnessState; last_success_at: string | null };
  } | null;
  weather: {
    attribution: string;
    observed_at: string;
    freshness: Freshness;
    // Per-param observed_at/freshness (dashboard.py) — the object-level pair above
    // is only the newest of any param, so a stale hourly-derived value must be
    // labelled with its own status, same as air params.
    params: Record<
      string,
      { value: number; unit: string; observed_at: string; freshness: Freshness }
    >;
    source_status?: { freshness: FreshnessState; last_success_at: string | null };
  } | null;
  // TASK-5.5: daily forecast from the same dashboard aggregate. Freshness is
  // about when we fetched it (fetched_at), not about the forecast period.
  forecast: {
    attribution: string;
    fetched_at: string;
    freshness: Freshness;
    days: ForecastDay[];
  } | null;
  // TASK-7.8: optional — absent on an older backend; the card renders nothing then.
  outdoor?: unknown;
  // TASK-8.8/8.9: CAMS model forecast (ADR-020), typed in pollen.ts (PollenBlock);
  // optional - absent on an older backend, the card renders nothing then.
  pollen?: unknown;
};

type LoadState = "loading" | "ready" | "error";

// Codex review (round 2): toLocaleTimeString() alone made an observation from
// yesterday 14:00 look identical to one from today 14:00 — STALE only gives a
// broad age bucket, not the actual day. Date + time together, always.
function formatObservedAt(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
}

function AlertsSection({ alerts }: { alerts: AlertsBlock }) {
  // The summary ages on the device clock (alerts.ts MAX_HEALTHY_AGE_MS), but a
  // mounted screen only re-renders on state changes - tick so a FRESH status
  // that crosses the bound stops claiming "brak ostrzeżeń" without user action.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);
  const summary = summarizeAlerts(alerts, now);
  const lastSuccess = (at: string | null) =>
    at === null ? "brak udanej aktualizacji" : `ostatnia aktualizacja ${formatObservedAt(at)}`;
  return (
    <View style={styles.alerts}>
      <Text style={styles.alertsTitle}>Ostrzeżenia — cała Polska</Text>
      {summary.kind === "unavailable" && (
        <Text style={styles.metric}>
          Ostrzeżenia chwilowo niedostępne ({lastSuccess(summary.lastSuccessAt)}).
        </Text>
      )}
      {summary.kind === "none-confirmed" && (
        <Text style={styles.metric}>Brak aktywnych ostrzeżeń: {summary.sources.join(", ")}.</Text>
      )}
      {summary.kind === "list-maybe-outdated" && (
        <Text style={styles.freshness}>
          Lista może być nieaktualna ({lastSuccess(summary.lastSuccessAt)}).
        </Text>
      )}
      {alerts.items.map((alert) => (
        <View key={alertKey(alert)} style={styles.alertItem}>
          <Text style={styles.metric}>
            {alert.event_type} (stopień {alert.severity_raw})
          </Text>
          {alertAreasLabel(alert.areas) !== "" && <Text>{alertAreasLabel(alert.areas)}</Text>}
          <Text style={styles.freshness}>
            do {formatObservedAt(alert.valid_until)} · {alert.issuing_office} ·{" "}
            {FRESHNESS_LABEL[alert.freshness]}
          </Text>
        </View>
      ))}
      <Text style={styles.attribution}>{alerts.attribution}</Text>
    </View>
  );
}

export default function Home() {
  const [state, setState] = useState<LoadState>("loading");
  const [areas, setAreas] = useState<DashboardArea[]>([]);
  const [alerts, setAlerts] = useState<AlertsBlock | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  // Device time of the last successful dashboard response (ages the outdoor verdict).
  const [loadedAt, setLoadedAt] = useState(() => Date.now());
  const [hydroRefreshTick, setHydroRefreshTick] = useState(0);

  const load = useCallback(() => {
    return apiGet<{ areas: DashboardArea[]; alerts: AlertsBlock }>("/api/v1/dashboard/latest")
      .then((body) => {
        setAreas(body.areas);
        setAlerts(body.alerts);
        setLoadedAt(Date.now());
        setState("ready");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = useCallback(() => {
    setHydroRefreshTick((t) => t + 1);
    setRefreshing(true);
    load().finally(() => setRefreshing(false));
  }, [load]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Za Oknem</Text>

      {/* Shown independently of the list so a failed pull-to-refresh is visible
          even when stale data from a previous successful load is still on screen
          (Codex review — state === "error" alone didn't reach the user because
          ListEmptyComponent only renders when the list is empty). */}
      {state === "error" && (
        <Text style={styles.errorBanner}>
          Błąd odświeżania —{" "}
          {areas.length > 0
            ? "pokazane dane mogą być nieaktualne."
            : "pociągnij w dół, aby spróbować ponownie."}
        </Text>
      )}

      <FlatList
        style={styles.list}
        data={areas}
        keyExtractor={(item) => item.slug}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        // TASK-7.2: labelled "cała Polska" until TASK-9.5 adds geo matching - an
        // unfiltered alert must never look like it concerns the user's location.
        // ADR-012: "brak ostrzeżeń" only when every alert source is FRESH/RECENT;
        // otherwise the source is silent and we say so (no false all-clear).
        ListHeaderComponent={alerts ? <AlertsSection alerts={alerts} /> : null}
        // TASK-7.2 (hydro): own fetch and own states - independent of the dashboard.
        ListFooterComponent={<HydroSection refreshTick={hydroRefreshTick} />}
        ListEmptyComponent={
          state === "error" ? null : (
            <Text>
              {state === "loading"
                ? "Ładowanie..."
                : "Brak danych — uruchom ingest na backendzie, potem pociągnij w dół."}
            </Text>
          )
        }
        renderItem={({ item }) => (
          <View style={styles.row}>
            <Text style={styles.stationName}>{item.name}</Text>
            <View style={styles.metricsRow}>
              <View style={styles.metricsColumn}>
                <AirParams air={item.air} />
                <AirIndexBadge index={item.air?.index} receivedAt={loadedAt} />
              </View>
              <View style={styles.metricsColumn}>
                <WeatherCard weather={item.weather} />
              </View>
            </View>
            <OutdoorCard outdoor={item.outdoor} receivedAt={loadedAt} />
            <PollenCard pollen={item.pollen} />
            {/* Slot for the pollen calendar section (separate PR, /pollen/calendar). */}
            {item.forecast && forecastLine(item.forecast.days) && (
              <View>
                <Text style={styles.metric}>
                  Prognoza: {forecastLine(item.forecast.days)}{" "}
                  <Text style={styles.freshness}>
                    ({FRESHNESS_LABEL[item.forecast.freshness]})
                  </Text>
                </Text>
                <Text style={styles.attribution}>
                  {item.forecast.attribution} · pobrano {formatObservedAt(item.forecast.fetched_at)}
                </Text>
              </View>
            )}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 60, paddingHorizontal: 16, gap: 12 },
  title: { fontSize: 24, fontWeight: "600" },
  errorBanner: { color: "#b00020" },
  list: { width: "100%" },
  row: {
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#ccc",
    gap: 4,
  },
  stationName: { fontSize: 16, fontWeight: "500" },
  // flex:1 on each column (Codex review — RN row children don't shrink by
  // default, so the attribution strings were overflowing/clipping instead of
  // wrapping on normal phone widths).
  metricsRow: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  metricsColumn: { flex: 1 },
  metric: { fontSize: 16 },
  freshness: { fontSize: 12, color: "#666" },
  attribution: { fontSize: 10, color: "#999" },
  alerts: { paddingVertical: 8, gap: 6 },
  alertsTitle: { fontSize: 18, fontWeight: "600", color: "#b00020" },
  alertItem: { gap: 2 },
});

// TASK-7.2 (hydro): separate fetch (hydrology isn't part of the dashboard aggregate,
// §55), so its failure never touches the rest of the screen and vice versa (rule #1).
// Nationwide until Phase 9 adds geo matching - hence the "cała Polska" label.
function HydroSection({ refreshTick }: { refreshTick: number }) {
  const [state, setState] = useState<LoadState>("loading");
  const [hydro, setHydro] = useState<HydroBlock | null>(null);
  // Re-evaluated every minute: labels age on the device without a refetch.
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let cancelled = false;
    apiGet<HydroBlock>("/api/v1/hydro/latest")
      .then((body) => {
        if (cancelled) return;
        setHydro(body);
        setNow(Date.now());
        setState("ready");
      })
      .catch(() => !cancelled && setState("error"));
    return () => {
      cancelled = true;
    };
  }, [refreshTick]);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const summary = hydro ? summarizeHydro(hydro, now) : null;
  const lastSuccess = (at: string | null) =>
    at === null ? "brak udanej aktualizacji" : `ostatnia aktualizacja ${formatObservedAt(at)}`;
  return (
    <View style={hydroStyles.section}>
      <Text style={hydroStyles.title}>Stany wody — cała Polska</Text>
      {state === "loading" && !hydro && <Text style={styles.metric}>Ładowanie...</Text>}
      {state === "error" && (
        <Text style={styles.errorBanner}>
          {hydro
            ? "Błąd odświeżania stanów wody — pokazane dane mogą być nieaktualne."
            : "Stany wody chwilowo niedostępne — pociągnij w dół, aby spróbować ponownie."}
        </Text>
      )}
      {summary?.kind === "unavailable" && (
        <Text style={styles.metric}>
          Dane o stanach wody niedostępne lub nieaktualne ({lastSuccess(summary.lastSuccessAt)}).
        </Text>
      )}
      {summary?.kind === "none-confirmed" && (
        <Text style={styles.metric}>
          Brak stacji w stanie ostrzegawczym lub alarmowym
          {summary.unassessed > 0
            ? ` (${summary.unassessed} stacji bez progów IMGW nie jest oceniane)`
            : ""}
          .
        </Text>
      )}
      {summary?.kind === "list" && summary.outdated && (
        <Text style={styles.freshness}>
          Lista może być nieaktualna ({lastSuccess(summary.lastSuccessAt)}).
        </Text>
      )}
      {summary?.kind === "list" &&
        summary.items.map(({ station, freshness }) => (
          <View key={station.station_id} style={hydroStyles.item}>
            <Text style={styles.metric}>
              {station.station_name} —{" "}
              <Text style={station.status === "ALARM" ? hydroStyles.alarm : hydroStyles.warning}>
                {HYDRO_STATUS_LABEL[station.status]}
              </Text>
            </Text>
            <Text>{hydroLevelLine(station)}</Text>
            <Text style={styles.freshness}>
              {HYDRO_FRESHNESS_LABEL[freshness]}, {formatObservedAt(station.observed_at)}
            </Text>
          </View>
        ))}
      {summary?.kind === "list" && summary.more > 0 && (
        <Text style={styles.freshness}>i {summary.more} więcej</Text>
      )}
      {hydro && <Text style={styles.attribution}>{hydro.attribution}</Text>}
    </View>
  );
}

const hydroStyles = StyleSheet.create({
  section: { paddingVertical: 12, gap: 6 },
  title: { fontSize: 18, fontWeight: "600" },
  item: { gap: 2 },
  alarm: { color: "#b00020", fontWeight: "700" },
  warning: { color: "#b26a00", fontWeight: "700" },
});
