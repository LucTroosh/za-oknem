import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text } from "react-native";

import { MIN_TOUCH, type Theme, typo } from "../lib/theme";
import useTheme, { useThemedStyles } from "./useTheme";

// Detail screens are hidden tabs (they need the tabs' DashboardProvider), so there is no
// header back button: this one returns to where the user came from, or to Start.
export default function DetailBack({ title }: { title: string }) {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Wróć"
        hitSlop={8}
        onPress={() => (router.canGoBack() ? router.back() : router.navigate("/"))}
        style={styles.back}
      >
        <Ionicons name="chevron-back" size={22} color={colors.accent} />
        <Text style={styles.backText}>Wróć</Text>
      </Pressable>
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
    </>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    back: { flexDirection: "row", alignItems: "center", minHeight: MIN_TOUCH, alignSelf: "flex-start" },
    backText: { ...typo.strong, color: t.colors.accent },
    title: { ...typo.display, color: t.colors.text },
  });
