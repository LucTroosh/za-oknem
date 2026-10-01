import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { HomeBanner } from "../lib/alertsBanner";
import { ALERTS_NONE_TEXT, type AlertsStatus as AlertsStatusModel } from "../lib/home";
import { MIN_TOUCH, type Theme, radius, space, toneColors, typo } from "../lib/theme";
import { SkeletonCard } from "./Skeleton";
import useTheme, { useThemedStyles } from "./useTheme";

// Glyph + word per tone (never colour alone), drawn with the one icon library.
const TONE_ICON = { danger: "close-circle", warning: "alert-circle", neutral: "help-circle" } as const;
const TONE_WORD = { danger: "Alarm", warning: "Ostrzeżenie", neutral: "Brak danych" } as const;

function Banner({ banner }: { banner: HomeBanner }) {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const { fg, bg } = toneColors(colors, banner.tone);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${TONE_WORD[banner.tone]}: ${banner.text}`}
      accessibilityHint="Otwiera zakładkę Alerty"
      onPress={() => router.navigate("/alerts")}
      style={[styles.box, { backgroundColor: bg, borderColor: fg }]}
    >
      <Ionicons name={TONE_ICON[banner.tone]} size={22} color={fg} importantForAccessibility="no" />
      <Text style={[styles.text, { color: fg }]}>{banner.text}</Text>
      <Ionicons name="chevron-forward" size={20} color={fg} importantForAccessibility="no" />
    </Pressable>
  );
}

// Spec §16/§44. A real warning is a banner (the screen puts it high); a confirmed all-clear is
// one quiet line; "could not check" is its own state and never reads as an all-clear (ADR-012).
// Until a request finishes its part is a skeleton (status computed in lib/home.ts).
export default function AlertsStatus({ status }: { status: AlertsStatusModel }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  if (status.kind === "loading") return <SkeletonCard label="Sprawdzanie ostrzeżeń" lines={1} />;
  if (status.kind === "none") {
    return (
      <View style={styles.quiet} accessible accessibilityLabel={ALERTS_NONE_TEXT}>
        <Ionicons name="checkmark-circle" size={20} color={colors.good} importantForAccessibility="no" />
        <Text style={styles.quietText}>{ALERTS_NONE_TEXT}</Text>
      </View>
    );
  }
  return (
    <View style={styles.list}>
      {status.banners.map((b) => (
        <Banner key={b.text} banner={b} />
      ))}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    list: { gap: space.sm },
    box: {
      minHeight: MIN_TOUCH,
      flexDirection: "row",
      alignItems: "center",
      gap: space.sm,
      paddingHorizontal: space.lg,
      paddingVertical: space.sm,
      borderRadius: radius.md,
      borderWidth: 1,
    },
    text: { ...typo.strong, flex: 1 },
    quiet: { flexDirection: "row", alignItems: "center", gap: space.sm, minHeight: MIN_TOUCH },
    quietText: { ...typo.body, color: t.colors.textSecondary },
  });
