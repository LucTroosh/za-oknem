import Ionicons from "@expo/vector-icons/Ionicons";
import type { ComponentProps } from "react";
import { Redirect, Tabs } from "expo-router";

import { DashboardProvider } from "../../components/DashboardProvider";
import useLocation from "../../components/LocationProvider";
import useTheme from "../../components/useTheme";
import { entryRedirect } from "../../lib/location";
import { typo } from "../../lib/theme";

// Icons: @expo/vector-icons ships with the Expo SDK (dependency of `expo`), no new package.
// Every tab also has a text label, so the icon is never the only carrier.
type IconName = ComponentProps<typeof Ionicons>["name"];
const icon = (name: IconName, focusedName: IconName) =>
  function TabIcon({ color, size, focused }: { color: string; size: number; focused: boolean }) {
    return <Ionicons name={focused ? focusedName : name} size={size} color={color} />;
  };

export default function TabsLayout() {
  const { colors } = useTheme();
  const { settings } = useLocation();
  const redirect = entryRedirect(settings, "tabs");
  if (redirect !== null || settings.location === null) return <Redirect href={redirect ?? "/location"} />;
  return (
    <DashboardProvider key={settings.location.geoAreaId} geoAreaId={settings.location.geoAreaId}>
      <Tabs
        screenOptions={{
          sceneStyle: { backgroundColor: colors.bg },
          headerStyle: { backgroundColor: colors.surface },
          headerTitleStyle: { ...typo.heading },
          headerTintColor: colors.text,
          headerShadowVisible: false,
          tabBarActiveTintColor: colors.accent,
          tabBarInactiveTintColor: colors.textSecondary,
          tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
          tabBarLabelStyle: { fontSize: typo.micro.fontSize, fontWeight: "600" },
        }}
      >
        {/* Start draws its own header (location, date, temperature). */}
        <Tabs.Screen name="index" options={{ title: "Start", headerShown: false, tabBarIcon: icon("home-outline", "home") }} />
        <Tabs.Screen name="alerts" options={{ title: "Alerty", tabBarIcon: icon("notifications-outline", "notifications") }} />
        {/* Detail screens (S5/S6): reachable from the Start cards only, no tab of their own. */}
        <Tabs.Screen name="air" options={{ href: null, headerShown: false }} />
        <Tabs.Screen name="weather" options={{ href: null, headerShown: false }} />
        <Tabs.Screen name="alert" options={{ href: null, headerShown: false }} />
        <Tabs.Screen name="rivers" options={{ href: null, headerShown: false }} />
        <Tabs.Screen name="settings" options={{ title: "Ustawienia", tabBarIcon: icon("settings-outline", "settings") }} />
      </Tabs>
    </DashboardProvider>
  );
}
