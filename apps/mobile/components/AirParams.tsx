import { airView } from "../app/readings";
import AirIndexBadge from "./AirIndexBadge";
import ReadingsList from "./ReadingsList";
import useNow from "./useNow";

// TASK-7.3: air params of the nearest station, with per-param age/staleness. The AQI
// badge is derived from the same readings, so it is dropped whenever the source is
// unavailable/silent (never "dobra" beside "dane niedostępne").
export default function AirParams({
  air,
  sourceStatus,
  receivedAt,
}: {
  air: unknown;
  sourceStatus: unknown;
  receivedAt: number;
}) {
  const view = airView(air, useNow(), sourceStatus);
  const index = air && typeof air === "object" ? (air as { index?: unknown }).index : undefined;
  return (
    <>
      <ReadingsList
        title="Powietrze"
        view={view}
        emptyText="Powietrze: brak stacji w pobliżu"
        unavailableText="Dane o powietrzu niedostępne."
      />
      {view?.suppressDerived ? null : <AirIndexBadge index={index} receivedAt={receivedAt} />}
    </>
  );
}
