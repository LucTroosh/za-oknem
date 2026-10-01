import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

// Navigation lives in (tabs); the root stack leaves room for later full-screen routes
// (e.g. location picker). The status bar follows the system light/dark setting.
export default function RootLayout() {
  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
