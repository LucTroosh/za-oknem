import { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";

import { type AlertsBlock, alertAreasLabel, alertKey } from "./alerts";
import { apiGet } from "./api";
import { type ForecastDay, forecastLine } from "./forecast";
import { FRESHNESS_LABEL, type Freshness } from "./freshness";

// No shared api-contract package yet (packages/api-contract is still a
// placeholder) — hand-typed here, one endpoint doesn't justify generating an
// OpenAPI client.
//
// Freshness is always the server's own value (app/api/v1/dashboard.py), never
// recomputed here: air and weather use different thresholds (2h/6h vs 4h/8h,
// ADR-004), so one client-side function can't correctly classify both. Trade-off:
// labels no longer tick forward live while the screen stays open (previously via
// a 60s timer) - acceptable, since an accurate label needs a refetch anyway.
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
  } | null;
  // TASK-5.5: daily forecast from the same dashboard aggregate. Freshness is
  // about when we fetched it (fetched_at), not about the forecast period.
  forecast: {
    attribution: string;
    fetched_at: string;
    freshness: Freshness;
    days: ForecastDay[];
  } | null;
};

type LoadState = "loading" | "ready" | "error";

// Codex review (round 2): toLocaleTimeString() alone made an observation from
// yesterday 14:00 look identical to one from today 14:00 — STALE only gives a
// broad age bucket, not the actual day. Date + time together, always.
function formatObservedAt(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
}

export default function Home() {
  const [state, setState] = useState<LoadState>("loading");
  const [areas, setAreas] = useState<DashboardArea[]>([]);
  const [alerts, setAlerts] = useState<AlertsBlock | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(() => {
    return apiGet<{ areas: DashboardArea[]; alerts: AlertsBlock }>("/api/v1/dashboard/latest")
      .then((body) => {
        setAreas(body.areas);
        setAlerts(body.alerts);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = useCallback(() => {
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
        // Empty list renders nothing (not "brak ostrzeżeń"): without source-level
        // freshness (TASK-7.4) an empty list can't be told apart from IMGW being
        // down, and a false all-clear is worse than silence for safety data.
        ListHeaderComponent={
          alerts && alerts.items.length > 0 ? (
            <View style={styles.alerts}>
              <Text style={styles.alertsTitle}>Ostrzeżenia — cała Polska</Text>
              {alerts.items.map((alert) => (
                <View key={alertKey(alert)} style={styles.alertItem}>
                  <Text style={styles.metric}>
                    {alert.event_type} (stopień {alert.severity_raw})
                  </Text>
                  {alertAreasLabel(alert.areas) !== "" && (
                    <Text>{alertAreasLabel(alert.areas)}</Text>
                  )}
                  <Text style={styles.freshness}>
                    do {formatObservedAt(alert.valid_until)} · {alert.issuing_office} ·{" "}
                    {FRESHNESS_LABEL[alert.freshness]}
                  </Text>
                </View>
              ))}
              <Text style={styles.attribution}>{alerts.attribution}</Text>
            </View>
          ) : null
        }
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
              {item.air ? (
                <View style={styles.metricsColumn}>
                  {Object.entries(item.air.params).map(([code, param]) => (
                    <Text key={code} style={styles.metric}>
                      {code}: {param.value} {param.unit}{" "}
                      <Text style={styles.freshness}>
                        ({FRESHNESS_LABEL[param.freshness]}, {formatObservedAt(param.observed_at)})
                      </Text>
                    </Text>
                  ))}
                  <Text style={styles.attribution}>{item.air.attribution}</Text>
                </View>
              ) : (
                <Text style={styles.metric}>Powietrze: brak stacji w pobliżu</Text>
              )}
              {item.weather?.params.temperature_2m ? (
                <View style={styles.metricsColumn}>
                  <Text style={styles.metric}>
                    {item.weather.params.temperature_2m.value}
                    {item.weather.params.temperature_2m.unit}{" "}
                    <Text style={styles.freshness}>
                      ({FRESHNESS_LABEL[item.weather.params.temperature_2m.freshness]},{" "}
                      {formatObservedAt(item.weather.params.temperature_2m.observed_at)})
                    </Text>
                  </Text>
                  <Text style={styles.attribution}>{item.weather.attribution}</Text>
                </View>
              ) : (
                <Text style={styles.metric}>pogoda: brak danych</Text>
              )}
            </View>
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
