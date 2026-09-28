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

type LoadState = "loading" | "ready" | "error";

export default function Home() {
  const [state, setState] = useState<LoadState>("loading");
  const [stations, setStations] = useState<Station[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const load = useCallback(() => {
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
  },
  stationName: { fontSize: 16, fontWeight: "500" },
  pm25: { fontSize: 20 },
  freshness: { fontSize: 12, color: "#666" },
});
