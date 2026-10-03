import useDashboard from "../../components/DashboardProvider";
import PageHeader from "../../components/PageHeader";
import PollenCalendarDetail from "../../components/PollenCalendarDetail";
import Screen from "../../components/Screen";
import { SkeletonCard } from "../../components/Skeleton";

// Details of the typical pollen season (ADR-023), opened from the "Typowy sezon" card on Pyłki:
// periods per allergen, what is coming, how the calendar works, its limits and source.
// Data = the same shared calendar request as the card (DashboardProvider); nothing new is fetched.
export default function PollenCalendarScreen() {
  const d = useDashboard();
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh} gap={16}>
      <PageHeader title="Kalendarz sezonów" backLabel="Pyłki" />
      {d.calendar === null && !d.calendarError ? (
        <SkeletonCard label="Ładowanie kalendarza sezonów" lines={3} />
      ) : (
        <PollenCalendarDetail calendar={d.calendar} error={d.calendarError} />
      )}
    </Screen>
  );
}
