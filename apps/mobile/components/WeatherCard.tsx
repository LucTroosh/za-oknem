import { weatherView } from "../lib/weather";
import Card from "./Card";
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
    <Card>
      <ReadingsList
        title="Pogoda"
        view={view}
        emptyText="Brak danych pogodowych dla tej lokalizacji."
        unavailableText="Dane pogodowe są chwilowo niedostępne."
      />
    </Card>
  );
}
