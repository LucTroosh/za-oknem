import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MIN_TOUCH, type Theme, space, typo } from "../lib/theme";
import useTheme, { useThemedStyles } from "./useTheme";

// Header of a sub-screen: back + large page title (28/34, 800). Detail screens are hidden tabs, so
// there is no navigator header: back returns to where the user came from, or to Start.
export default function PageHeader({ title, subtitle, backLabel = "Wróć" }: { title: string; subtitle?: string; backLabel?: string }) {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.wrap}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={backLabel}
        hitSlop={8}
        onPress={() => (router.canGoBack() ? router.back() : router.navigate("/"))}
        style={styles.back}
      >
        <Ionicons name="chevron-back" size={24} color={colors.accent} />
        <Text style={styles.backText}>{backLabel}</Text>
      </Pressable>
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    wrap: { gap: space.xs },
    back: { flexDirection: "row", alignItems: "center", minHeight: MIN_TOUCH, alignSelf: "flex-start", marginLeft: -space.xs },
    backText: { ...typo.strong, color: t.colors.accent },
    title: { ...typo.display, color: t.colors.text },
    subtitle: { ...typo.supporting, color: t.colors.textSecondary },
  });

// Title of a top-level tab screen (no back button).
export function TabTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.wrap}>
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}
