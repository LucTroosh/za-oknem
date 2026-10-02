import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { View } from "react-native";

import useLocation, { LocationProvider } from "../components/LocationProvider";
import useTheme from "../components/useTheme";

// Routes: welcome, location (picker: onboarding and change), (tabs). Each guards itself with
// entryRedirect (lib/location.ts), so the first run goes Welcome -> location -> Start and a
// returning user lands on Start. Until the stored choice is read the screen is just the
// themed background (no Welcome flash). The status bar follows the system light/dark setting,
// the stack's scene colour comes from the tokens (no white flash in dark mode).
function RootStack() {
  const { colors } = useTheme();
  const { ready } = useLocation();
  if (!ready) return <View style={{ flex: 1, backgroundColor: colors.bg }} />;
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }} />;
}

export default function RootLayout() {
  return (
    <LocationProvider>
      <StatusBar style="auto" />
      <RootStack />
    </LocationProvider>
  );
}
