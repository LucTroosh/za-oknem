import { StyleSheet, Text } from "react-native";

import { airCoverage, showAirIndex } from "../lib/coverage";
import { airView } from "../lib/readings";
import { space, typo } from "../lib/theme";
import AirIndexBadge from "./AirIndexBadge";
import Card from "./Card";
import ReadingsList from "./ReadingsList";
import useNow from "./useNow";
import useTheme from "./useTheme";

// TASK-7.3: air params of the nearest station, with per-param age/staleness. The AQI
// badge is derived from the same readings, so it is dropped whenever the source is
// unavailable/silent (never "dobra" beside "dane niedostępne"). The badge sits right under the
// title: it is the summary, the readings below are the detail.
export default function AirParams({
  air,
  coverage,
  sourceStatus,
  receivedAt,
}: {
  air: unknown;
  coverage?: unknown;
  sourceStatus: unknown;
  receivedAt: number;
}) {
  const { colors } = useTheme();
  const view = airView(air, useNow(), sourceStatus);
  const note = airCoverage(coverage, air).note;
  const index = air && typeof air === "object" ? (air as { index?: unknown }).index : undefined;
  return (
    <Card>
      <ReadingsList
        title="Powietrze"
        view={view}
        emptyText="Brak stacji pomiarowej w pobliżu."
        unavailableText="Dane o powietrzu są chwilowo niedostępne."
        lead={
          view?.suppressDerived ? null : showAirIndex(coverage, air) ? (
            <AirIndexBadge index={index} receivedAt={receivedAt} />
          ) : note ? (
            <Text style={[styles.note, { color: colors.textSecondary }]}>{note}</Text>
          ) : null
        }
      />
    </Card>
  );
}

const styles = StyleSheet.create({ note: { ...typo.body, marginBottom: space.xs } });
