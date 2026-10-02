import Ionicons from "@expo/vector-icons/Ionicons";
import { Redirect, useNavigation, useRouter } from "expo-router";
import { Image, ImageBackground, ScrollView, StyleSheet, Text, View, useWindowDimensions } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import Button from "../components/Button";
import useLocation from "../components/LocationProvider";
import useTheme, { useThemedStyles } from "../components/useTheme";
import { entryRedirect } from "../lib/location";
import { type Theme, elevation, radius, space, typo } from "../lib/theme";
import { SCRIM_FADE_ALPHAS, SCRIM_FADE_HEIGHT, SCRIM_TEXT_ALPHA, WELCOME_COPY, WELCOME_DOMAINS, scrimColor, welcomeDomainColumns, welcomeTintColors } from "../lib/welcome";

// Welcome (spec §6; asset pack v2 contract §4-§8), first run only. The approved photo is a
// decorative background (the same JPG in both themes); the brand mark, all text, the domain
// cues and the button are native. A scrim fades in behind the text; dark mode changes the
// scrim, text, button and privacy row, not the photo. Says nothing about water (no source yet).
const HERO = require("../assets/za-oknem/backgrounds/welcome-hero-1242x2688.jpg");
const LOGO = require("../assets/za-oknem/brand/logo-mark-512.png");

export default function Welcome() {
  const { colors } = useTheme();
  const { fontScale } = useWindowDimensions();
  const styles = useThemedStyles(createStyles);
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { settings, startOnboarding } = useLocation();
  const navigation = useNavigation();
  const redirect = entryRedirect(settings, "welcome");
  // Welcome stays in the stack under Location (so Back returns here). When the location is chosen
  // onboardingDone flips while Welcome is hidden underneath: it must not redirect from the
  // background, the picker resets the history itself (lib/navigation.ts).
  if (redirect !== null) return navigation.isFocused() ? <Redirect href={redirect} /> : null;
  return (
    <ImageBackground
      source={HERO}
      resizeMode="cover"
      style={styles.screen}
      imageStyle={styles.photo}
      accessible={false}
      importantForAccessibility="no"
    >
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content} bounces={false}>
        {/* Decorative: "Za Oknem" is announced by the text right below. */}
        <View style={[styles.top, { paddingTop: insets.top + space.xl }]}>
          <Image source={LOGO} style={styles.logo} accessible={false} importantForAccessibility="no" />
        </View>
        <View style={[styles.body, { paddingBottom: Math.max(space.xl, insets.bottom + space.md) }]}>
          <View style={styles.scrim} pointerEvents="none" importantForAccessibility="no-hide-descendants">
            <View style={{ height: SCRIM_FADE_HEIGHT }}>
              {SCRIM_FADE_ALPHAS.map((a, i) => (
                <View key={i} style={{ flex: 1, backgroundColor: scrimColor(colors, a) }} />
              ))}
            </View>
            <View style={{ flex: 1, backgroundColor: scrimColor(colors, SCRIM_TEXT_ALPHA) }} />
          </View>
          <Text style={styles.brand}>{WELCOME_COPY.brand}</Text>
          <Text style={styles.headline} accessibilityRole="header">
            {/* Non-breaking space after one-letter words: no orphan "u" at the end of a line. */}
            {WELCOME_COPY.headline.replace(/\b([uwzoiaUWZOIA]) /g, "$1\u00A0")}
          </Text>
          {/* One soft capsule, four domains; read as one line by TalkBack (icons are decorative). */}
          <View style={styles.capsule} accessible accessibilityLabel={WELCOME_DOMAINS.map((d) => d.label).join(", ")}>
            {WELCOME_DOMAINS.map((d) => {
              const c = welcomeTintColors(colors, d.tint);
              return (
                <View key={d.label} style={[styles.domain, { width: welcomeDomainColumns(fontScale) === 4 ? "25%" : "50%" }]}>
                  <View style={[styles.iconCircle, { backgroundColor: c.bg }]}>
                    <Ionicons name={d.icon} size={24} color={c.fg} importantForAccessibility="no" />
                  </View>
                  <Text style={styles.domainText}>{d.label}</Text>
                </View>
              );
            })}
          </View>
          {/* push, not replace: Back (header or Android) from the picker returns to Welcome. */}
          <Button
            label={WELCOME_COPY.cta}
            hint={WELCOME_COPY.ctaHint}
            onPress={() => {
              startOnboarding();
              router.push("/location");
            }}
          />
          <View style={styles.privacy}>
            <Ionicons name="lock-closed-outline" size={16} color={colors.textSecondary} importantForAccessibility="no" />
            <Text style={styles.privacyText}>{WELCOME_COPY.privacy}</Text>
          </View>
        </View>
      </ScrollView>
    </ImageBackground>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    screen: { flex: 1, backgroundColor: t.colors.bg },
    // Transparent: the photo behind must show through.
    scroll: { flex: 1 },
    photo: { width: "100%", height: "100%" },
    content: { flexGrow: 1, justifyContent: "space-between" },
    top: { alignItems: "center", paddingHorizontal: space.xl },
    logo: { width: 112, height: 112 },
    // The scrim reaches up by the fade height, so the photo fades into the panel (no hard edge)
    // and the text block itself sits on the constant-alpha panel.
    body: { gap: space.lg, paddingHorizontal: space.xl, paddingTop: space.lg, marginTop: SCRIM_FADE_HEIGHT },
    scrim: { position: "absolute", top: -SCRIM_FADE_HEIGHT, left: 0, right: 0, bottom: 0 },
    brand: { ...typo.title, color: t.colors.accent, textAlign: "center" },
    headline: { ...typo.hero, color: t.colors.text, textAlign: "center" },
    capsule: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "center",
      rowGap: space.md,
      paddingVertical: space.md,
      paddingHorizontal: space.sm,
      borderRadius: radius.hero,
      backgroundColor: t.scheme === "dark" ? t.colors.elevated : t.colors.surface,
      ...elevation(t.scheme, 2),
    },
    domain: { alignItems: "center", gap: space.xs },
    iconCircle: { width: 48, height: 48, borderRadius: 24, alignItems: "center", justifyContent: "center" },
    domainText: { ...typo.caption, fontWeight: "600", color: t.colors.text, textAlign: "center" },
    privacy: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: space.sm },
    privacyText: { ...typo.caption, color: t.colors.textSecondary, flexShrink: 1 },
  });
