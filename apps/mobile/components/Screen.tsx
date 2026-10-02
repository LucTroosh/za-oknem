import type { ReactNode } from "react";
import { RefreshControl, ScrollView, StyleSheet } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { space } from "../lib/theme";
import useTheme from "./useTheme";

// AppScreen: themed background, optional pull-to-refresh, 16 dp side padding (+ safe-area insets)
// and the 24 dp section rhythm of production UI v1. The navigator's own header handles the top inset.
export default function Screen({
  children,
  refreshing,
  onRefresh,
  padTop,
  gap = space.lg,
}: {
  children: ReactNode;
  refreshing?: boolean;
  onRefresh?: () => void;
  // The screen has no navigator header (Start draws its own): add the status-bar inset.
  padTop?: boolean;
  gap?: number;
}) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: colors.bg }]}
      keyboardShouldPersistTaps="handled"
      contentContainerStyle={[
        styles.content,
        { gap },
        padTop && { paddingTop: insets.top + space.md },
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
  content: { paddingTop: space.md, paddingBottom: space.xxl },
});
