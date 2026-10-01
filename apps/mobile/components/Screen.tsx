import type { ReactNode } from "react";
import { RefreshControl, ScrollView, StyleSheet } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { space } from "../lib/theme";
import useTheme from "./useTheme";

// Shared screen body: themed background, optional pull-to-refresh, side/bottom safe-area
// insets (the navigator's header already handles the top one).
export default function Screen({
  children,
  refreshing,
  onRefresh,
  padTop,
}: {
  children: ReactNode;
  refreshing?: boolean;
  onRefresh?: () => void;
  // The screen has no navigator header (Start draws its own): add the status-bar inset.
  padTop?: boolean;
}) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: colors.bg }]}
      contentContainerStyle={[
        styles.content,
        padTop && { paddingTop: insets.top + space.lg },
        { paddingLeft: Math.max(space.lg, insets.left), paddingRight: Math.max(space.lg, insets.right) },
      ]}
      refreshControl={
        onRefresh ? (
          <RefreshControl
            refreshing={refreshing ?? false}
            onRefresh={onRefresh}
            tintColor={colors.accent}
            colors={[colors.accent]}
            progressBackgroundColor={colors.surface}
          />
        ) : undefined
      }
    >
      {children}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingTop: space.lg, paddingBottom: space.xxl, gap: space.md },
});
