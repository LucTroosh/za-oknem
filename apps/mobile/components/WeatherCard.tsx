import { weatherView } from "../app/weather";
import ReadingsList from "./ReadingsList";
import useNow from "./useNow";

// TASK-5.4 / 7.3: the weather fields the backend stores, with units and staleness.
export default function WeatherCard({
  weather,
  sourceStatus,
}: {
  weather: unknown;
  sourceStatus: unknown;
}) {
  const view = weatherView(weather, useNow(), sourceStatus);
  return (
    <ReadingsList
      title="Pogoda"
      view={view}
      emptyText="pogoda: brak danych"
      unavailableText="Dane pogodowe niedostępne."
    />
  );
}
