import Ionicons from "@expo/vector-icons/Ionicons";
import type { ComponentProps } from "react";
import { Redirect, Tabs } from "expo-router";
import { StyleSheet } from "react-native";

import { DashboardProvider } from "../../components/DashboardProvider";
import useLocation from "../../components/LocationProvider";
import useTheme from "../../components/useTheme";
import { entryRedirect } from "../../lib/location";
import { elevation, typo } from "../../lib/theme";

// Icons: @expo/vector-icons ships with the Expo SDK (dependency of `expo`), no new package.
// Every tab also has a text label, so the icon is never the only carrier.
type IconName = ComponentProps<typeof Ionicons>["name"];
const icon = (name: IconName, focusedName: IconName) =>
  function TabIcon({ color, focused }: { color: string; focused: boolean }) {
    return <Ionicons name={focused ? focusedName : name} size={24} color={color} />;
  };

const HIDDEN = ["air", "weather", "pollen", "alert", "rivers", "appearance", "accessibility", "privacy", "sources", "about"] as const;

export default function TabsLayout() {
  const { colors, scheme } = useTheme();
  const { settings } = useLocation();
  const redirect = entryRedirect(settings, "tabs");
  if (redirect !== null || settings.location === null) return <Redirect href={redirect ?? "/location"} />;
  return (
    <DashboardProvider key={settings.location.geoAreaId} geoAreaId={settings.location.geoAreaId}>
      <Tabs
        screenOptions={{
          sceneStyle: { backgroundColor: colors.bg },
          // Every screen draws its own page header (production UI v1): no navigator header.
          headerShown: false,
          tabBarActiveTintColor: colors.accent,
          tabBarInactiveTintColor: colors.textSecondary,
          // Elevated surface + a soft top shadow instead of a hard border; safe-area aware by the navigator.
          tabBarStyle: {
            backgroundColor: scheme === "dark" ? colors.elevated : colors.surface,
            borderTopWidth: scheme === "dark" ? StyleSheet.hairlineWidth : 0,
            borderTopColor: colors.border,
            ...elevation(scheme, 2),
            shadowOffset: { width: 0, height: -3 },
          },
          tabBarLabelStyle: { fontSize: typo.meta.fontSize, fontWeight: "600" },
          tabBarItemStyle: { minHeight: 48 },
          // The bar has a fixed height: scaled labels would be clipped at 200% font. Icon + word stay
          // readable; every screen BODY scales with the system font.
          tabBarAllowFontScaling: false,
        }}
      >
        {/* Exactly three tabs (locked architecture): Start / Alerty / Ustawienia. */}
        <Tabs.Screen name="index" options={{ title: "Start", tabBarIcon: icon("home-outline", "home") }} />
        <Tabs.Screen name="alerts" options={{ title: "Alerty", tabBarIcon: icon("notifications-outline", "notifications") }} />
        <Tabs.Screen name="settings" options={{ title: "Ustawienia", tabBarIcon: icon("settings-outline", "settings") }} />
        {/* Detail screens are hidden tabs (they need this layout's DashboardProvider): no tab of their own. */}
        {HIDDEN.map((name) => (
          <Tabs.Screen key={name} name={name} options={{ href: null }} />
        ))}
      </Tabs>
    </DashboardProvider>
  );
}
