import { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";

// Android emulator: 10.0.2.2, iOS simulator/web: localhost. Override with
// EXPO_PUBLIC_API_URL when running on a physical device (your machine's LAN IP).
const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

// Matches app/api/v1/air.py's response shape (see apps/api). No shared
// api-contract package yet (packages/api-contract is still a placeholder) —
// hand-typed here, one endpoint doesn't justify generating an OpenAPI client.
type Freshness = "FRESH" | "RECENT" | "STALE";

type Station = {
  station_id: string;
  station_name: string;
  pm25: number;
  unit: string;
  observed_at: string;
  freshness: Freshness;
};

type LoadState = "loading" | "ready" | "error";

const FRESHNESS_LABEL: Record<Freshness, string> = {
  FRESH: "świeże",
  RECENT: "niedawne",
  STALE: "nieaktualne",
};

export default function Home() {
  const [state, setState] = useState<LoadState>("loading");
  const [stations, setStations] = useState<Station[]>([]);
  const [refreshing, setRefreshing] = useState(false);

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

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    load().finally(() => setRefreshing(false));
  }, [load]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Za Oknem — PM2.5</Text>

      {state === "loading" && <Text>Ładowanie...</Text>}
      {state === "error" && <Text>Błąd połączenia z API</Text>}
      {state === "ready" && stations.length === 0 && (
        <Text>Brak danych — uruchom ingest na backendzie.</Text>
      )}

      {state === "ready" && stations.length > 0 && (
        <FlatList
          style={styles.list}
          data={stations}
          keyExtractor={(item) => item.station_id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={({ item }) => (
            <View style={styles.row}>
              <Text style={styles.stationName}>{item.station_name}</Text>
              <Text style={styles.pm25}>
                {item.pm25} {item.unit}
              </Text>
              <Text style={styles.freshness}>{FRESHNESS_LABEL[item.freshness]}</Text>
            </View>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 60, paddingHorizontal: 16, gap: 12 },
  title: { fontSize: 24, fontWeight: "600" },
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
