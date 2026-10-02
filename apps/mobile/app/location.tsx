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
import { SEARCH_ERROR, SEARCH_HINT, activatePlace, emptyResultMessage } from "../lib/places";
import { LOCATION_REQUIRED_ART } from "../lib/stateArt";
import { type Theme, space, typo } from "../lib/theme";

// "Ustaw lokalizację" (spec §7): onboarding (first run) and change (from Start / Settings) in
// one screen - ONE active location. Search = our own /places (ADR-029); with no query it lists
// the big cities from /areas, so the screen is useful even before places are imported.
// No "use my location" button: GPS (TASK-12.3) does not exist yet, and a dead CTA is forbidden.
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
  // Production UI v1: Welcome -> Location -> Start. The first pick goes straight to Start.
  const done = () => (changing ? leave() : router.replace("/"));

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
      {changing && <PageHeader title="Gdzie jesteś?" subtitle="Wybierz lokalizację, aby pokazać aktualne warunki w Twojej okolicy." />}
      {!changing && (
        <>
          {/* No location chosen yet (first run): the only state where this illustration is true. */}
          {settings.location === null && <StateIllustration art={LOCATION_REQUIRED_ART} height={112} />}
          <Text style={styles.title} accessibilityRole="header">
            Gdzie jesteś?
          </Text>
          <Text style={styles.supporting}>Wybierz lokalizację, aby pokazać aktualne warunki w Twojej okolicy.</Text>
        </>
      )}
      {notice && <Notice tone="warning" text={notice} />}
      {failure && <Notice tone="danger" text={failure} />}

      <SearchField value={text} onChangeText={setText} placeholder="Wpisz miejscowość" editable={!busy} />

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
    title: { ...typo.display, color: t.colors.text },
    supporting: { ...typo.supporting, color: t.colors.textSecondary },
    hint: { ...typo.caption, color: t.colors.textSecondary },
    message: { gap: space.md, paddingVertical: space.sm },
    body: { ...typo.body, color: t.colors.text },
    dev: { ...typo.caption, color: t.colors.dim, fontStyle: "italic" },
    micro: { ...typo.meta, color: t.colors.textSecondary },
  });
