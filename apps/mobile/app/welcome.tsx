import Ionicons from "@expo/vector-icons/Ionicons";
import { Manrope_600SemiBold } from "@expo-google-fonts/manrope/600SemiBold";
import { Manrope_800ExtraBold } from "@expo-google-fonts/manrope/800ExtraBold";
import { useFonts } from "expo-font";
import { Redirect, useNavigation, useRouter } from "expo-router";
import { Image, ScrollView, StyleSheet, Text, View, useWindowDimensions } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import Button from "../components/Button";
import useLocation from "../components/LocationProvider";
import useTheme, { useThemedStyles } from "../components/useTheme";
import { entryRedirect } from "../lib/location";
import { type Theme, elevation, radius, space, typo } from "../lib/theme";
import {
  BOTTOM_VEIL,
  BOTTOM_VEIL_HEIGHT,
  TOP_VEIL,
  TOP_VEIL_HEIGHT,
  TOP_VEIL_PLATEAU,
  WELCOME_COPY,
  WELCOME_DOMAINS,
  WELCOME_TYPE,
  footerChipColor,
  heroFrame,
  scrimColor,
  veilAlphas,
  welcomeDomainColumns,
  welcomeTintColors,
} from "../lib/welcome";

// Welcome (spec §6; asset pack v2 contract §4-§8), first run only. The approved photo is a
// decorative background (the same JPG in both themes), cropped to show the panorama (about 38% sky,
// the rest city / river / greenery - lib/welcome.ts heroFrame). The brand mark, all text, the domain
// capsule, the button and the footer are native. Two light veils (not a white fade) keep the brand
// text readable over the sky and blend the bottom edge; dark mode only changes the veils and
// surfaces, not the photo. Says nothing about water (no source yet).
const HERO = require("../assets/za-oknem/backgrounds/welcome-hero-1242x2688.jpg");
const LOGO = require("../assets/za-oknem/brand/logo-mark-512.png");

function Veil({ color, alphas, style }: { color: (a: number) => string; alphas: number[]; style: object }) {
  return (
    <View style={style} pointerEvents="none" importantForAccessibility="no-hide-descendants">
      {alphas.map((a, i) => (
        <View key={i} style={{ flex: 1, backgroundColor: color(a) }} />
      ))}
    </View>
  );
}

export default function Welcome() {
  const { colors, scheme } = useTheme();
  const { fontScale, width, height } = useWindowDimensions();
  const styles = useThemedStyles(createStyles);
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { settings, startOnboarding } = useLocation();
  const navigation = useNavigation();
  // Local font files: loads in a few ms; until then (or if it fails) the plain background / system font.
  const [fontsLoaded, fontError] = useFonts({ Manrope_600SemiBold, Manrope_800ExtraBold });
  const redirect = entryRedirect(settings, "welcome");
  // Welcome stays in the stack under Location (so Back returns here). When the location is chosen
  // onboardingDone flips while Welcome is hidden underneath: it must not redirect from the
  // background, the picker resets the history itself (lib/navigation.ts).
  if (redirect !== null) return navigation.isFocused() ? <Redirect href={redirect} /> : null;
  if (!fontsLoaded && !fontError) return <View style={styles.screen} />; // no font flash
  const frame = heroFrame(width, height);
  const color = (a: number) => scrimColor(colors, a);
  return (
    <View style={styles.screen}>
      <Image
        source={HERO}
        resizeMode="stretch"
        style={{ position: "absolute", width: frame.width, height: frame.height, left: frame.left, top: frame.top }}
        accessible={false}
        importantForAccessibility="no"
      />
      <Veil color={color} alphas={veilAlphas(TOP_VEIL[scheme], TOP_VEIL_PLATEAU)} style={[styles.veil, { top: 0, height: TOP_VEIL_HEIGHT }]} />
      <Veil
        color={color}
        alphas={veilAlphas(BOTTOM_VEIL[scheme]).slice().reverse()}
        style={[styles.veil, { bottom: 0, height: BOTTOM_VEIL_HEIGHT }]}
      />
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content} bounces={false}>
        <View style={[styles.top, { paddingTop: insets.top + space.xxl }]}>
          {/* Decorative: "Za Oknem" is announced by the text right below. */}
          <Image source={LOGO} style={styles.logo} accessible={false} importantForAccessibility="no" />
          <Text style={styles.eyebrow}>{WELCOME_COPY.headline}</Text>
          <Text style={styles.brand} accessibilityRole="header">
            {WELCOME_COPY.brand}
          </Text>
        </View>
        <View style={[styles.bottom, { paddingBottom: Math.max(space.xl, insets.bottom + space.md) }]}>
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
          <View style={styles.cta}>
            <Button
              label={WELCOME_COPY.cta}
              hint={WELCOME_COPY.ctaHint}
              onPress={() => {
                startOnboarding();
                router.push("/location");
              }}
            />
          </View>
          <View style={[styles.chip, { backgroundColor: footerChipColor(colors) }]}>
            <Ionicons name="lock-closed-outline" size={14} color={colors.textSecondary} importantForAccessibility="no" />
            <Text style={styles.privacyText}>{WELCOME_COPY.privacy}</Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    screen: { flex: 1, backgroundColor: t.colors.bg, overflow: "hidden" },
    veil: { position: "absolute", left: 0, right: 0 },
    // Transparent: the photo behind must show through.
    scroll: { flex: 1 },
    // The gap between the two groups is the panorama.
    content: { flexGrow: 1, justifyContent: "space-between" },
    top: { alignItems: "center", paddingHorizontal: space.xl },
    logo: { width: 84, height: 84, marginBottom: space.lg },
    // Weight comes from the font family (Manrope), so no fontWeight; the system font is the fallback
    // when the font fails to load.
    eyebrow: { ...WELCOME_TYPE.eyebrow, color: t.colors.text, textAlign: "center" },
    brand: { ...WELCOME_TYPE.brand, color: t.colors.text, textAlign: "center", marginTop: space.xs },
    bottom: { paddingHorizontal: space.xl, paddingTop: space.xxl },
    capsule: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "center",
      rowGap: space.md,
      paddingVertical: space.lg,
      paddingHorizontal: space.sm,
      borderRadius: radius.hero,
      backgroundColor: t.scheme === "dark" ? t.colors.elevated : t.colors.surface,
      ...elevation(t.scheme, 2),
    },
    domain: { alignItems: "center", gap: space.xs },
    iconCircle: { width: 48, height: 48, borderRadius: 24, alignItems: "center", justifyContent: "center" },
    domainText: { ...typo.caption, fontWeight: "600", color: t.colors.text, textAlign: "center" },
    cta: { marginTop: space.xl },
    chip: {
      flexDirection: "row",
      alignItems: "center",
      alignSelf: "center",
      gap: space.sm,
      marginTop: space.lg,
      paddingVertical: space.xs + 2,
      paddingHorizontal: space.md,
      borderRadius: radius.pill,
    },
    privacyText: { ...typo.caption, color: t.colors.textSecondary, flexShrink: 1 },
  });
