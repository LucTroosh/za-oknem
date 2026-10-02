import Ionicons from "@expo/vector-icons/Ionicons";
import { Redirect, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import type { AreaOut, AreasResponse, PlaceOut } from "../../../packages/api-contract/schema";
import Button from "../components/Button";
import { LoadingState } from "../components/EmptyState";
import useLocation from "../components/LocationProvider";
import LocationRow from "../components/LocationRow";
import Notice from "../components/Notice";
import Screen from "../components/Screen";
import StateIllustration from "../components/StateIllustration";
import usePlaceSearch from "../components/usePlaceSearch";
import useTheme, { useThemedStyles } from "../components/useTheme";
import { apiGet } from "../lib/api";
import { entryRedirect, locationFromArea, locationFromPlace } from "../lib/location";
import { SEARCH_ERROR, SEARCH_HINT, activatePlace, emptyResultMessage } from "../lib/places";
import { LOCATION_REQUIRED_ART } from "../lib/stateArt";
import { MIN_TOUCH, type Theme, radius, space, typo } from "../lib/theme";

// "Ustaw lokalizację" (spec §7): onboarding (first run) and change (from Start / Settings) in
// one screen - ONE active location. Search = our own /places (ADR-029); with no query it lists
// the big cities from /areas, so the screen is useful even before places are imported.
// No "use my location" button: GPS (TASK-12.3) does not exist yet, and a dead CTA is forbidden.
export default function LocationScreen() {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const router = useRouter();
  const { settings, notice, choose, welcomeSeen } = useLocation();
  const [text, setText] = useState("");
  const [retry, setRetry] = useState(0);
  const search = usePlaceSearch(text, retry);
  const [cities, setCities] = useState<AreaOut[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const picking = useRef<AbortController | null>(null);
  // A ref, not state: two quick taps in one frame both see the old state value.
  const pending = useRef(false);
  const changing = settings.onboardingDone && router.canGoBack();

  useEffect(() => {
    const ctrl = new AbortController();
    apiGet<AreasResponse>("/api/v1/areas", ctrl.signal)
      .then((r) => !ctrl.signal.aborted && setCities(r.areas))
      .catch(() => undefined); // the list is a convenience; search still works
    return () => {
      ctrl.abort();
      picking.current?.abort();
    };
  }, []);

  const leave = () => (router.canGoBack() ? router.back() : router.replace("/"));

  const pickPlace = async (place: PlaceOut) => {
    if (pending.current) return;
    pending.current = true;
    setFailure(null);
    setBusyId(place.place_id);
    const ctrl = new AbortController();
    picking.current = ctrl;
    try {
      const result = await activatePlace(place.place_id, ctrl.signal);
      if (ctrl.signal.aborted) return;
      if (result.kind === "failed") {
        setFailure(result.message);
        setBusyId(null);
        pending.current = false;
        return;
      }
      choose(locationFromPlace(result.place, result.area, result.attribution));
      leave();
    } catch {
      // aborted (screen closed): nothing to do
      pending.current = false;
    }
  };

  const pickCity = (area: AreaOut) => {
    if (pending.current) return;
    pending.current = true;
    choose(locationFromArea(area));
    leave();
  };

  // A fresh install opened straight on this route (deep link) goes through Welcome first.
  const redirect = entryRedirect(settings, "location", welcomeSeen);
  if (redirect !== null) return <Redirect href={redirect} />;

  const busy = busyId !== null;
  return (
    <Screen padTop>
      {changing && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Wróć"
          onPress={() => router.back()}
          style={styles.back}
          hitSlop={8}
        >
          <Ionicons name="chevron-back" size={22} color={colors.accent} />
          <Text style={styles.backText}>Wróć</Text>
        </Pressable>
      )}
      {/* No location chosen yet (first run): the only state where this illustration is true. */}
      {settings.location === null && <StateIllustration art={LOCATION_REQUIRED_ART} height={120} />}
      <Text style={styles.title} accessibilityRole="header">
        {changing ? "Zmień lokalizację" : "Ustaw lokalizację"}
      </Text>
      <Text style={styles.supporting}>Wybierz lokalizację, żeby zobaczyć aktualne warunki w Twojej okolicy.</Text>
      {changing && settings.location && <Text style={styles.supporting}>Teraz: {settings.location.label}</Text>}
      {notice && <Notice tone="warning" text={notice} />}
      {failure && <Notice tone="danger" text={failure} />}

      <TextInput
        value={text}
        onChangeText={setText}
        placeholder="Wpisz miejscowość"
        placeholderTextColor={colors.dim}
        accessibilityLabel="Wpisz miejscowość"
        style={styles.input}
        autoCorrect={false}
        autoCapitalize="words"
        returnKeyType="search"
        clearButtonMode="while-editing"
        maxLength={100}
        editable={!busy}
      />

      {search.status === "idle" && (
        <>
          <Text style={styles.hint}>{SEARCH_HINT}</Text>
          {cities.length > 0 && (
            <>
              <Text style={styles.section} accessibilityRole="header">
                Większe miasta
              </Text>
              {cities.map((a) => (
                <LocationRow key={a.geo_area_id} title={a.name} disabled={busy} onPress={() => pickCity(a)} />
              ))}
            </>
          )}
        </>
      )}
      {search.status === "loading" && <LoadingState label="Szukam miejscowości" />}
      {search.status === "error" && (
        <View style={styles.message}>
          <Text style={styles.body}>{SEARCH_ERROR}</Text>
          <Button label="Spróbuj ponownie" onPress={() => setRetry((n) => n + 1)} />
        </View>
      )}
      {search.status === "ready" && search.places.length === 0 && (
        <View style={styles.message}>
          <Text style={styles.body} accessibilityRole="alert">
            {emptyResultMessage(search.query)}
          </Text>
          {__DEV__ && (
            <Text style={styles.dev}>
              Dev: pusta baza miejscowości? Zaimportuj GeoNames (README, sekcja Mobile → Miejscowości).
            </Text>
          )}
        </View>
      )}
      {search.status === "ready" &&
        search.places.map((p) => (
          <LocationRow
            key={p.place_id}
            title={p.label}
            busy={busyId === p.place_id}
            disabled={busy}
            onPress={() => pickPlace(p)}
          />
        ))}
      {search.status === "ready" && search.places.length > 0 && search.attribution && (
        <Text style={styles.micro}>Nazwy miejscowości: {search.attribution}</Text>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    back: { flexDirection: "row", alignItems: "center", minHeight: MIN_TOUCH, alignSelf: "flex-start" },
    backText: { ...typo.strong, color: t.colors.accent },
    title: { ...typo.display, color: t.colors.text },
    supporting: { ...typo.body, color: t.colors.textSecondary },
    input: {
      ...typo.body,
      minHeight: 48,
      paddingHorizontal: space.lg,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: t.colors.border,
      backgroundColor: t.colors.surface,
      color: t.colors.text,
    },
    hint: { ...typo.caption, color: t.colors.textSecondary },
    section: { ...typo.heading, color: t.colors.text, marginTop: space.sm },
    message: { gap: space.md, paddingVertical: space.sm },
    body: { ...typo.body, color: t.colors.text },
    dev: { ...typo.caption, color: t.colors.dim, fontStyle: "italic" },
    micro: { ...typo.micro, color: t.colors.textSecondary },
  });
