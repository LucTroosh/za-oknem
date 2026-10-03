import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { AIR_PARAMS, type AirHistory, formatHistoryTime, historyBars } from "../lib/airHistory";
import { apiGet } from "../lib/api";
import { airCoverage } from "../lib/coverage";
import { formatObservedAt } from "../lib/dashboardTypes";
import { ageFreshness, asFreshness, FRESHNESS_LABEL, worstFreshness } from "../lib/freshness";
import { AIR_AGE } from "../lib/readings";
import { MIN_TOUCH, type Theme, typo } from "../lib/theme";
import Card from "./Card";
import { LoadingState } from "./EmptyState";
import FreshnessBadge from "./FreshnessBadge";
import SectionHeader from "./SectionHeader";
import useNow from "./useNow";
import { useThemedStyles } from "./useTheme";

export default function AirHistoryCard({ geoAreaId, refreshTick }: { geoAreaId: number; refreshTick: number }) {
  const [param, setParam] = useState<AirHistory["param"]>("PM2.5");
  const [hours, setHours] = useState<24 | 48>(24);
  const [retry, setRetry] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [state, setState] = useState<{ key: string; data: AirHistory | null; error: boolean; loading: boolean } | null>(null);
  const key = `${geoAreaId}:${param}:${hours}`;
  const styles = useThemedStyles(createStyles);
  const now = useNow();
  useEffect(() => {
    const ctrl = new AbortController();
    setState((old) => ({ key, data: old?.key === key ? old.data : null, error: false, loading: true }));
    apiGet<AirHistory>(`/api/v1/air/history?geo_area_id=${geoAreaId}&param=${encodeURIComponent(param)}&hours=${hours}`, ctrl.signal)
      .then((data) => {
        historyBars(data);
        if (data.param !== param || data.hours !== hours || !["available", "no_station", "no_data"].includes(data.availability) ||
          (data.points.length > 0 && (typeof data.unit !== "string" || !data.unit.trim() || data.availability !== "available")) ||
          (data.availability === "available" && data.points.length === 0) ||
          typeof data.attribution !== "string" || !Array.isArray(data.gaps) ||
          (data.station !== null && (typeof data.station.station_name !== "string" || !Number.isFinite(data.station.distance_km)))) {
          throw new Error("Invalid air history response");
        }
        if (!ctrl.signal.aborted) setState({ key, data, error: false, loading: false });
      })
      .catch(() => {
        if (!ctrl.signal.aborted) setState((old) => ({ key, data: old?.key === key ? old.data : null, error: true, loading: false }));
      });
    return () => ctrl.abort();
  }, [geoAreaId, param, hours, key, refreshTick, retry]);
  const current = state?.key === key ? state : null;
  const data = current?.data;
  const chart = data ? historyBars(data) : null;
  const freshness = data ? worstFreshness(asFreshness(data.latest_freshness), ageFreshness(data.latest_observed_at, now, AIR_AGE)) : "UNAVAILABLE";
  const station = data?.station;
  const coverageNote = station ? airCoverage(null, station).note : null;
  return (
    <Card>
      <SectionHeader title="Historia pomiarów" actionLabel="Odśwież" onAction={() => setRetry((n) => n + 1)} />
      <View style={styles.choices}>
        {AIR_PARAMS.map((p) => (
          <Pressable key={p} accessibilityRole="button" accessibilityState={{ selected: p === param }} onPress={() => setParam(p)} style={[styles.choice, p === param && styles.selected]}>
            <Text style={styles.text}>{p}</Text>
          </Pressable>
        ))}
      </View>
      <View style={styles.choices}>
        {([24, 48] as const).map((h) => (
          <Pressable key={h} accessibilityRole="button" accessibilityLabel={`Ostatnie ${h} godzin`} accessibilityState={{ selected: h === hours }} onPress={() => setHours(h)} style={[styles.choice, h === hours && styles.selected]}>
            <Text style={styles.text}>{h} h</Text>
          </Pressable>
        ))}
      </View>
      {(!current || current.loading) && <LoadingState label="Ładowanie historii pomiarów…" />}
      {current?.error && <Text style={styles.text}>Nie udało się odświeżyć historii.{data ? " Poniżej ostatnio pobrane pomiary." : " Spróbuj ponownie."}</Text>}
      {data && chart && (
        <>
          {station && <Text style={styles.note}>{station.station_name} · {station.distance_km.toLocaleString("pl-PL")} km od wybranego miejsca.{coverageNote ? ` ${coverageNote}` : ""}</Text>}
          {data.availability !== "available" ? (
            <Text style={styles.text}>{data.availability === "no_station" ? "Brak stacji pomiarowej w okolicy." : `Brak pomiarów ${param} w wybranym okresie. Stacja może nie mierzyć tego parametru.`}</Text>
          ) : (
            <>
              <Text style={styles.note}>Stężenie {param} ({data.unit}) · skala od 0 do {chart.max.toLocaleString("pl-PL")}</Text>
              <View style={styles.plot} accessible accessibilityLabel={`${chart.points.length} pomiarów ${param}. Skala od zera do ${chart.max} ${data.unit}. Dokładne wartości pod przyciskiem Pokaż pomiary.`}>
                {chart.points.map((p) => (
                  <View key={p.observed_at} style={[styles.bar, { left: `${p.x * 100}%`, height: p.value === 0 ? 2 : `${p.height * 100}%`, width: `${70 / hours}%` }]} />
                ))}
              </View>
              <View style={styles.axis}><Text style={styles.note}>{formatObservedAt(data.window_start)}</Text><Text style={styles.note}>{formatObservedAt(data.window_end)}</Text></View>
              <Text style={styles.note}>Puste miejsca oznaczają brak pomiaru, nie zero. Kreska na osi oznacza zmierzone zero.{data.gaps.length > 0 ? ` Przerwy między pomiarami: ${data.gaps.length}.` : ""}</Text>
              <FreshnessBadge state={freshness} label={`Ostatni pomiar: ${freshness === "UNAVAILABLE" ? "brak aktualności" : FRESHNESS_LABEL[freshness]} · ${formatObservedAt(data.latest_observed_at ?? "")}`} />
              <Pressable accessibilityRole="button" accessibilityState={{ expanded }} onPress={() => setExpanded((v) => !v)} style={styles.choice}>
                <Text style={styles.text}>{expanded ? "Ukryj pomiary" : "Pokaż pomiary"}</Text>
              </Pressable>
              {expanded && data.points.map((p) => <Text key={p.observed_at} style={styles.text}>{formatHistoryTime(p.observed_at)} · {p.value.toLocaleString("pl-PL")} {data.unit}</Text>)}
            </>
          )}
          <Text style={styles.note}>{data.attribution}</Text>
        </>
      )}
    </Card>
  );
}

const createStyles = (t: Theme) => StyleSheet.create({
  choices: { flexDirection: "row", flexWrap: "wrap", gap: 4 },
  choice: { minHeight: MIN_TOUCH, minWidth: MIN_TOUCH, paddingHorizontal: 12, justifyContent: "center", borderRadius: 8 },
  selected: { backgroundColor: t.colors.elevated, borderWidth: 1, borderColor: t.colors.accent },
  text: { ...typo.body, color: t.colors.text },
  note: { ...typo.caption, color: t.colors.textSecondary, flexShrink: 1 },
  plot: { height: 120, marginHorizontal: 4, borderBottomWidth: 1, borderColor: t.colors.textSecondary },
  bar: { position: "absolute", bottom: 0, backgroundColor: t.colors.accent, transform: [{ translateX: -2 }] },
  axis: { flexDirection: "row", justifyContent: "space-between", gap: 12 },
});
