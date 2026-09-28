import { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";

import { FRESHNESS_LABEL, freshnessOf } from "./freshness";

// Android emulator: 10.0.2.2, iOS simulator/web: localhost. Override with
// EXPO_PUBLIC_API_URL when running on a physical device (your machine's LAN IP).
const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

// No shared api-contract package yet (packages/api-contract is still a
// placeholder) — hand-typed here, one endpoint doesn't justify generating an
// OpenAPI client.
type Station = {
  station_id: string;
  station_name: string;
  pm25: number;
  unit: string;
  observed_at: string;
};

type WeatherArea = {
  geo_area_id: number;
  name: string;
  observed_at: string;
  // Computed server-side (app/api/v1/weather.py) against weather's own 4h/8h
  // thresholds (Open-Meteo's 3h cycle, ADR-004) — freshnessOf()'s constants are
  // air quality's 2h/6h and would misclassify weather data if reused here.
  freshness: "FRESH" | "RECENT" | "STALE";
  params: Record<string, { value: number; unit: string }>;
};

type LoadState = "loading" | "ready" | "error";

export default function Home() {
  const [state, setState] = useState<LoadState>("loading");
  const [stations, setStations] = useState<Station[]>([]);
  const [weatherAreas, setWeatherAreas] = useState<WeatherArea[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const load = useCallback(() => {
    // Weather isn't matched to a station yet (no geo-matching until Phase 6's
    // Geo Engine, ADR-005) — shown as its own section, not fused per-row.
    // Its own fetch failing shouldn't blank the PM2.5 list, so it's caught
    // separately rather than joined into the air-quality Promise chain.
    fetch(`${API_URL}/api/v1/weather/latest`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((body: { areas: WeatherArea[] }) => setWeatherAreas(body.areas))
      .catch(() => setWeatherAreas([]));

    return fetch(`${API_URL}/api/v1/air/latest`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((body: { stations: Station[] }) => {
        setStations(body.stations);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Ticks the freshness labels forward while the screen stays open, without
  // needing a network refetch.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    load().finally(() => setRefreshing(false));
  }, [load]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Za Oknem — PM2.5</Text>

      {/* Shown independently of the list so a failed pull-to-refresh is visible
          even when stale data from a previous successful load is still on screen
          (Codex review — state === "error" alone didn't reach the user because
          ListEmptyComponent only renders when the list is empty). */}
      {state === "error" && (
        <Text style={styles.errorBanner}>
          Błąd odświeżania —{" "}
          {stations.length > 0
            ? "pokazane dane mogą być nieaktualne."
            : "pociągnij w dół, aby spróbować ponownie."}
        </Text>
      )}

      <FlatList
        style={styles.list}
        data={stations}
        keyExtractor={(item) => item.station_id}
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
            <Text style={styles.stationName}>{item.station_name}</Text>
            <Text style={styles.pm25}>
              {item.pm25} {item.unit}
            </Text>
            <Text style={styles.freshness}>
              {FRESHNESS_LABEL[freshnessOf(item.observed_at, now)]}
            </Text>
          </View>
        )}
      />

      {weatherAreas.length > 0 && (
        <View>
          <Text style={styles.sectionTitle}>Pogoda</Text>
          {weatherAreas.map((area) => (
            <View key={area.geo_area_id} style={styles.row}>
              <Text style={styles.stationName}>{area.name}</Text>
              <Text style={styles.pm25}>
                {area.params.temperature_2m
                  ? `${area.params.temperature_2m.value} ${area.params.temperature_2m.unit}`
                  : "brak danych"}
              </Text>
              <Text style={styles.freshness}>{FRESHNESS_LABEL[area.freshness]}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 60, paddingHorizontal: 16, gap: 12 },
  title: { fontSize: 24, fontWeight: "600" },
  sectionTitle: { fontSize: 18, fontWeight: "600", marginTop: 8 },
  errorBanner: { color: "#b00020" },
  list: { width: "100%" },
  row: {
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#ccc",
  },
  stationName: { fontSize: 16, fontWeight: "500" },
  pm25: { fontSize: 20 },
  freshness: { fontSize: 12, color: "#666" },
});
