import Ionicons from "@expo/vector-icons/Ionicons";
import type { ComponentProps } from "react";
import { Tabs } from "expo-router";

import { DashboardProvider } from "../../components/DashboardProvider";
import useTheme from "../../components/useTheme";
import { typo } from "../theme";

// Icons: @expo/vector-icons ships with the Expo SDK (dependency of `expo`), no new package.
// Every tab also has a text label, so the icon is never the only carrier.
type IconName = ComponentProps<typeof Ionicons>["name"];
const icon = (name: IconName, focusedName: IconName) =>
  function TabIcon({ color, size, focused }: { color: string; size: number; focused: boolean }) {
    return <Ionicons name={focused ? focusedName : name} size={size} color={color} />;
  };

export default function TabsLayout() {
  const { colors } = useTheme();
  return (
    <DashboardProvider>
      <Tabs
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTitleStyle: { ...typo.heading, color: colors.text },
          headerTintColor: colors.text,
          headerShadowVisible: false,
          tabBarActiveTintColor: colors.accent,
          tabBarInactiveTintColor: colors.textSecondary,
          tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
          tabBarLabelStyle: { fontSize: typo.micro.fontSize, fontWeight: "600" },
        }}
      >
        <Tabs.Screen name="index" options={{ title: "Za Oknem", tabBarLabel: "Home", tabBarIcon: icon("home-outline", "home") }} />
        <Tabs.Screen name="alerty" options={{ title: "Alerty", tabBarIcon: icon("warning-outline", "warning") }} />
        <Tabs.Screen name="settings" options={{ title: "Ustawienia", tabBarIcon: icon("settings-outline", "settings") }} />
      </Tabs>
    </DashboardProvider>
  );
}
