import * as ExpoLocation from "expo-location";
import { Redirect, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import type { AreaOut, AreasResponse, PlaceOut } from "../../../packages/api-contract/schema";
import Button from "../components/Button";
import { LoadingState } from "../components/EmptyState";
import useLocation from "../components/LocationProvider";
import LocationRow from "../components/LocationRow";
import Notice from "../components/Notice";
import Screen from "../components/Screen";
import StateIllustration from "../components/StateIllustration";
import PageHeader from "../components/PageHeader";
import SearchField from "../components/SearchField";
import SectionHeader from "../components/SectionHeader";
import { SettingsGroup } from "../components/SettingsRow";
import usePlaceSearch from "../components/usePlaceSearch";
import { useThemedStyles } from "../components/useTheme";
import { apiGet } from "../lib/api";
import { entryRedirect, locationFromArea, locationFromPlace } from "../lib/location";
import { applyNavStep, backFromLocation, finishLocation, locationMode, showLocationBack } from "../lib/navigation";
import { NEAREST_PRIVACY, type NearestState, distanceText, findNearestPlace, lookupNearest, nearestMessage } from "../lib/nearest";
import { SEARCH_ERROR, SEARCH_HINT, activatePlace, emptyResultMessage } from "../lib/places";
import { LOCATION_REQUIRED_ART } from "../lib/stateArt";
import { type Theme, space, typo } from "../lib/theme";

// "Ustaw lokalizację" (spec §7): onboarding (first run) and change (from Start / Settings) in
// one screen - ONE active location. Search = our own /places (ADR-029); with no query it lists
// the big cities from /areas, so the screen is useful even before places are imported.
// "Użyj mojej lokalizacji": one foreground read -> nearest place of our registry, shown for the
// user to confirm (never auto-selected). No background location, nothing stored (rule #11).
export default function LocationScreen() {
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
  const mode = locationMode(settings);
  const [nearest, setNearest] = useState<NearestState>({ kind: "idle" });
  const locating = useRef<AbortController | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    apiGet<AreasResponse>("/api/v1/areas", ctrl.signal)
      .then((r) => !ctrl.signal.aborted && setCities(r.areas))
      .catch(() => undefined); // the list is a convenience; search still works
    return () => {
      ctrl.abort();
      picking.current?.abort();
      locating.current?.abort();
    };
  }, []);

  // Welcome -> Location -> Start (lib/navigation.ts): first run can go Back to Welcome and finishing
  // resets the history; a later change returns to the screen it was opened from.
  const goBack = () => applyNavStep(router, backFromLocation(mode, router.canGoBack()));
  const done = () => applyNavStep(router, finishLocation(mode, router.canGoBack()));

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
      done();
    } catch {
      // aborted (screen closed): nothing to do
      pending.current = false;
    }
  };

  const useMyLocation = async () => {
    if (pending.current || nearest.kind === "locating") return;
    locating.current?.abort();
    const ctrl = new AbortController();
    locating.current = ctrl;
    setNearest({ kind: "locating" });
    const result = await findNearestPlace({
      requestPermission: async () => {
        const r = await ExpoLocation.requestForegroundPermissionsAsync();
        return { granted: r.granted, canAskAgain: r.canAskAgain };
      },
      getPosition: async () => {
        // Balanced accuracy = coarse is enough for a town; one read, no watching.
        const p = await ExpoLocation.getCurrentPositionAsync({ accuracy: ExpoLocation.Accuracy.Balanced });
        return { latitude: p.coords.latitude, longitude: p.coords.longitude };
      },
      lookup: (position) => lookupNearest(position, ctrl.signal),
    });
    if (!ctrl.signal.aborted) setNearest(result);
  };

  const pickCity = (area: AreaOut) => {
    if (pending.current) return;
    pending.current = true;
    choose(locationFromArea(area));
    done();
  };

  // A fresh install opened straight on this route (deep link) goes through Welcome first.
  const redirect = entryRedirect(settings, "location", welcomeSeen);
  if (redirect !== null) return <Redirect href={redirect} />;

  const busy = busyId !== null;
  const activeAreaId = settings.location?.geoAreaId ?? null;
  return (
    <Screen padTop gap={12}>
      <PageHeader
        title="Gdzie jesteś?"
        subtitle="Wybierz lokalizację, aby pokazać aktualne warunki w Twojej okolicy."
        onBack={goBack}
        hideBack={!showLocationBack(mode, router.canGoBack())}
      />
      {/* No location chosen yet (first run): the only state where this illustration is true. */}
      {settings.location === null && <StateIllustration art={LOCATION_REQUIRED_ART} height={112} />}
      {notice && <Notice tone="warning" text={notice} />}
      {failure && <Notice tone="danger" text={failure} />}

      <SearchField value={text} onChangeText={setText} placeholder="Wpisz miejscowość" editable={!busy} />

      {search.status === "idle" && (
        <View style={styles.gps}>
          <Button
            label={nearest.kind === "locating" ? "Szukam…" : "Użyj mojej lokalizacji"}
            variant="secondary"
            disabled={busy || nearest.kind === "locating"}
            hint="Jednorazowo sprawdza, jaka miejscowość jest najbliżej Ciebie"
            onPress={useMyLocation}
          />
          {nearest.kind === "found" && (
            <>
              <SectionHeader title="Najbliższa miejscowość" />
              <SettingsGroup>
                <LocationRow title={nearest.place.label} busy={busyId === nearest.place.place_id} disabled={busy} last onPress={() => pickPlace(nearest.place)} />
              </SettingsGroup>
              <Text style={styles.hint}>{distanceText(nearest.distanceKm)}. Dotknij, aby ją wybrać.</Text>
              <Text style={styles.micro}>Nazwy miejscowości: {nearest.attribution}</Text>
            </>
          )}
          {nearestMessage(nearest) && (
            <Text style={styles.body} accessibilityRole="alert">
              {nearestMessage(nearest)}
            </Text>
          )}
          <Text style={styles.micro}>{NEAREST_PRIVACY}</Text>
        </View>
      )}

      {search.status === "idle" && (
        <>
          <Text style={styles.hint}>{SEARCH_HINT}</Text>
          {cities.length > 0 && (
            <>
              <SectionHeader title="Większe miasta" />
              <SettingsGroup>
                {cities.map((a, i) => (
                  <LocationRow
                    key={a.geo_area_id}
                    title={a.name}
                    active={a.geo_area_id === activeAreaId}
                    last={i === cities.length - 1}
                    disabled={busy}
                    onPress={() => pickCity(a)}
                  />
                ))}
              </SettingsGroup>
            </>
          )}
        </>
      )}
      {search.status === "loading" && <LoadingState label="Szukam miejscowości" />}
      {search.status === "error" && (
        <View style={styles.message}>
          <Text style={styles.body}>{SEARCH_ERROR}</Text>
          <Button label="Spróbuj ponownie" variant="secondary" onPress={() => setRetry((n) => n + 1)} />
        </View>
      )}
      {search.status === "ready" && search.places.length === 0 && (
        <View style={styles.message}>
          <Text style={styles.body} accessibilityRole="alert">
            {emptyResultMessage(search.query)}
          </Text>
          {__DEV__ && (
            <Text style={styles.dev}>Dev: pusta baza miejscowości? Zaimportuj GeoNames (README, sekcja Mobile → Miejscowości).</Text>
          )}
        </View>
      )}
      {search.status === "ready" && search.places.length > 0 && (
        <SettingsGroup>
          {search.places.map((p, i) => (
            <LocationRow
              key={p.place_id}
              title={p.label}
              busy={busyId === p.place_id}
              disabled={busy}
              last={i === search.places.length - 1}
              onPress={() => pickPlace(p)}
            />
          ))}
        </SettingsGroup>
      )}
      {search.status === "ready" && search.places.length > 0 && search.attribution && (
        <Text style={styles.micro}>Nazwy miejscowości: {search.attribution}</Text>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    hint: { ...typo.caption, color: t.colors.textSecondary },
    gps: { gap: space.sm },
    message: { gap: space.md, paddingVertical: space.sm },
    body: { ...typo.body, color: t.colors.text },
    dev: { ...typo.caption, color: t.colors.dim, fontStyle: "italic" },
    micro: { ...typo.meta, color: t.colors.textSecondary },
  });
