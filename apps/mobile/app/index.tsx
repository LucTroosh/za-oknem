import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

// Android emulator: 10.0.2.2, iOS simulator/web: localhost. Override with
// EXPO_PUBLIC_API_URL when running on a physical device (your machine's LAN IP).
const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

type HealthState = "loading" | "ok" | "error";

export default function Home() {
  const [state, setState] = useState<HealthState>("loading");

  useEffect(() => {
    fetch(`${API_URL}/api/v1/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((body) => setState(body.status === "ok" ? "ok" : "error"))
      .catch(() => setState("error"));
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Za Oknem</Text>
      <Text>
        API status:{" "}
        {state === "loading" ? "sprawdzam..." : state === "ok" ? "OK" : "błąd połączenia"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", gap: 8 },
  title: { fontSize: 24, fontWeight: "600" },
});
