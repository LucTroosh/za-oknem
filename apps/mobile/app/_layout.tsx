import { Nunito_600SemiBold } from "@expo-google-fonts/nunito/600SemiBold";
import { Nunito_700Bold } from "@expo-google-fonts/nunito/700Bold";
import { Nunito_800ExtraBold } from "@expo-google-fonts/nunito/800ExtraBold";
import Ionicons from "@expo/vector-icons/Ionicons";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Text, View } from "react-native";

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

function FontsPending() {
  const { colors } = useTheme();
  return <View style={{ flex: 1, backgroundColor: colors.bg }} />;
}

// Light icons on a dark theme and vice versa - from the effective scheme (system or chosen).
function ThemedStatusBar() {
  const { scheme } = useTheme();
  return <StatusBar style={scheme === "dark" ? "light" : "dark"} />;
}

// Fonts are registered once, before the first screen: the Ionicons glyph font (every icon in the
// app) and Nunito (Welcome). Ionicons otherwise loads lazily per icon and swallows a failure, which
// leaves empty icon slots with no explanation. A failure never blocks the app (icons stay empty,
// text falls back to the system font); in the test APK (EXPO_PUBLIC_DEBUG_FONTS=1) it is printed.
function FontErrorNotice({ error }: { error: Error | null }) {
  if (!error || process.env.EXPO_PUBLIC_DEBUG_FONTS !== "1") return null;
  return (
    <Text style={{ position: "absolute", top: 40, left: 8, right: 8, zIndex: 10, color: "#fff", backgroundColor: "#b3261e", padding: 6, fontSize: 11 }}>
      Font load error: {String(error.message ?? error)}
    </Text>
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    ...Ionicons.font,
    Nunito_600SemiBold,
    Nunito_700Bold,
    Nunito_800ExtraBold,
  });
  const fontsSettled = fontsLoaded || fontError !== null;
  return (
    <LocationProvider>
      <ThemedStatusBar />
      {fontsSettled ? <RootStack /> : <FontsPending />}
      <FontErrorNotice error={fontError} />
    </LocationProvider>
  );
}
