import { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";

import { apiGet } from "./api";
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
    // TASK-4.1: full GIOŚ param set (PM2.5/PM10/NO2/SO2/O3/CO/C6H6), not just PM2.5
    // — freshness is per-param since each param can be observed at a different time.
    params: Record<string, { value: number; unit: string; freshness: Freshness }>;
  } | null;
  weather: {
    freshness: Freshness;
    params: Record<string, { value: number; unit: string }>;
  } | null;
};

type LoadState = "loading" | "ready" | "error";

export default function Home() {
  const [state, setState] = useState<LoadState>("loading");
  const [areas, setAreas] = useState<DashboardArea[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(() => {
    return apiGet<{ areas: DashboardArea[] }>("/api/v1/dashboard/latest")
      .then((body) => {
        setAreas(body.areas);
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
                <View>
                  {Object.entries(item.air.params).map(([code, param]) => (
                    <Text key={code} style={styles.metric}>
                      {code}: {param.value} {param.unit}{" "}
                      <Text style={styles.freshness}>({FRESHNESS_LABEL[param.freshness]})</Text>
                    </Text>
                  ))}
                </View>
              ) : (
                <Text style={styles.metric}>Powietrze: brak stacji w pobliżu</Text>
              )}
              {item.weather?.params.temperature_2m ? (
                <Text style={styles.metric}>
                  {item.weather.params.temperature_2m.value}
                  {item.weather.params.temperature_2m.unit}{" "}
                  <Text style={styles.freshness}>({FRESHNESS_LABEL[item.weather.freshness]})</Text>
                </Text>
              ) : (
                <Text style={styles.metric}>pogoda: brak danych</Text>
              )}
            </View>
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
  metricsRow: { flexDirection: "row", justifyContent: "space-between" },
  metric: { fontSize: 16 },
  freshness: { fontSize: 12, color: "#666" },
});
