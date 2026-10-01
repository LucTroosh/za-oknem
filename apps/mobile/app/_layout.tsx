import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import useTheme from "../components/useTheme";

// Navigation lives in (tabs); the root stack leaves room for later full-screen routes
// (e.g. location picker). The status bar follows the system light/dark setting, and the
// stack's scene colour comes from the tokens (no white flash in dark mode).
export default function RootLayout() {
  const { colors } = useTheme();
  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }} />
    </>
  );
}
