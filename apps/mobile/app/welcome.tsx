import Ionicons from "@expo/vector-icons/Ionicons";
import { Redirect, useRouter } from "expo-router";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import Button from "../components/Button";
import useLocation from "../components/LocationProvider";
import useTheme, { useThemedStyles } from "../components/useTheme";
import { entryRedirect } from "../lib/location";
import { type Theme, space, typo } from "../lib/theme";

// Welcome (spec §6), first run only. The hero is a neutral placeholder drawn from the tokens:
// the photo/illustration is the owner's design work. Copy is verbatim from the spec - and says
// nothing about water (no source yet).
export default function Welcome() {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { settings, startOnboarding } = useLocation();
  const redirect = entryRedirect(settings, "welcome");
  if (redirect !== null) return <Redirect href={redirect} />;
  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content} bounces={false}>
      <View style={[styles.hero, { paddingTop: insets.top }]} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
        <Ionicons name="partly-sunny-outline" size={96} color={colors.accent} />
      </View>
      <View style={[styles.body, { paddingBottom: Math.max(space.xl, insets.bottom) }]}>
        <Text style={styles.brand}>Za Oknem</Text>
        <Text style={styles.headline} accessibilityRole="header">
          Sprawdź, co dzieje się wokół Ciebie
        </Text>
        <Text style={styles.supporting}>Powietrze, pogoda, pyłki i lokalne alerty w jednym miejscu.</Text>
        <View style={styles.privacy}>
          <Ionicons name="lock-closed-outline" size={18} color={colors.textSecondary} />
          <Text style={styles.privacyText}>Bez konta. Bez zbędnych danych.</Text>
        </View>
        {/* replace, not push: Back from the picker must not return to Welcome. */}
        <Button
          label="Zaczynamy"
          hint="Przechodzi do wyboru lokalizacji"
          onPress={() => {
            startOnboarding();
            router.replace("/location");
          }}
        />
      </View>
    </ScrollView>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    screen: { flex: 1, backgroundColor: t.colors.bg },
    content: { flexGrow: 1 },
    hero: { flex: 3, minHeight: 240, alignItems: "center", justifyContent: "center", backgroundColor: t.colors.neutralBg },
    body: { flex: 2, gap: space.md, paddingHorizontal: space.xl, paddingTop: space.xl },
    brand: { ...typo.title, color: t.colors.accent },
    headline: { ...typo.display, color: t.colors.text },
    supporting: { ...typo.body, color: t.colors.textSecondary },
    privacy: { flexDirection: "row", alignItems: "center", gap: space.sm },
    privacyText: { ...typo.body, color: t.colors.textSecondary, flexShrink: 1 },
  });
