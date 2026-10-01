import { airView } from "../app/readings";
import ReadingsList from "./ReadingsList";
import useNow from "./useNow";

// TASK-7.3: air params of the nearest station, with per-param age/staleness.
export default function AirParams({ air }: { air: unknown }) {
  const view = airView(air, useNow());
  return (
    <ReadingsList
      title="Powietrze"
      view={view}
      emptyText="Powietrze: brak stacji w pobliżu"
      unavailableText="Dane o powietrzu niedostępne."
    />
  );
}
