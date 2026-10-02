import { StyleSheet, Text, View } from "react-native";

import useDashboard from "../../components/DashboardProvider";
import EmptyState, { LoadingState } from "../../components/EmptyState";
import HeroSurface from "../../components/HeroSurface";
import IconBox from "../../components/IconBox";
import InfoBanner from "../../components/InfoBanner";
import PageHeader from "../../components/PageHeader";
import PollenCalendarCard from "../../components/PollenCalendarCard";
import PollenCard from "../../components/PollenCard";
import Screen from "../../components/Screen";
import SectionHeader from "../../components/SectionHeader";
import { SkeletonCard } from "../../components/Skeleton";
import useArea from "../../components/useArea";
import useNow from "../../components/useNow";
import useTheme, { useThemedStyles } from "../../components/useTheme";
import { statusCards } from "../../lib/home";
import { type Theme, space, typo } from "../../lib/theme";

// Pollen (production UI v1 §11): risk headline -> taxa rows (CAMS MODEL forecast, never a trap
// measurement, rule #7) -> the seasonal calendar as a visibly separate section ("outside typical
// season" is never "no pollen"). Hero wording comes from the same status model as the Start tile.
export default function PollenDetails() {
  const d = useDashboard();
  const area = useArea();
  const now = useNow();
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const card = area ? statusCards(area, d.sourceStatus, now, d.loadedAt).find((c) => c.key === "pollen") : undefined;
  const unavailable = !card || card.state === "unavailable";
  const known = card && !unavailable && ["Niskie", "Sezon pylenia", "Szczyt pylenia"].includes(card.headline);
  const headline = unavailable
    ? "Prognoza pyłków chwilowo niedostępna"
    : known
      ? `Pylenie: ${card.headline === "Niskie" ? "niskie" : card.headline.toLowerCase()}`
      : card.headline;
  return (
    <Screen padTop refreshing={d.refreshing} onRefresh={d.refresh} gap={16}>
      <PageHeader title="Pyłki" />
      {d.state === "error" && area && <InfoBanner tone="warning" text="Nie udało się odświeżyć danych." detail="Pokazane informacje mogą być nieaktualne." />}
      {area === null ? (
        d.state === "loading" ? (
          <LoadingState label="Ładowanie danych o pyłkach…" />
        ) : (
          <EmptyState art="noData" title="Brak danych do pokazania" message="Dane dla Twojej lokalizacji nie są jeszcze dostępne." actionLabel="Odśwież" onAction={d.refresh} />
        )
      ) : (
        <>
          <HeroSurface tint={unavailable ? colors.neutralBg : colors.pollenBg} minHeight={120}>
            <View style={styles.heroRow} accessible accessibilityRole="header" accessibilityLabel={`${headline}. Prognoza modelu CAMS dla Twojego obszaru`}>
              <IconBox name="flower" fg={unavailable ? colors.textSecondary : colors.pollenFg} bg={colors.surface} size={56} iconSize={30} rounded={18} />
              <View style={styles.heroTexts}>
                <Text style={styles.headline}>{headline}</Text>
                <Text style={styles.supporting}>Prognoza modelu CAMS dla Twojego obszaru, nie pomiar.</Text>
              </View>
            </View>
          </HeroSurface>

          {area.pollen ? (
            <View style={styles.block}>
              <SectionHeader title="Gatunki" />
              <PollenCard pollen={area.pollen} />
            </View>
          ) : null}

          <View style={styles.block}>
            <SectionHeader title="Typowy sezon" />
            {d.calendar === null && !d.calendarError ? (
              <SkeletonCard label="Ładowanie kalendarza pylenia" lines={2} />
            ) : (
              <PollenCalendarCard calendar={d.calendar} error={d.calendarError} />
            )}
          </View>
        </>
      )}
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    block: { gap: space.md },
    heroRow: { flexDirection: "row", alignItems: "center", gap: space.lg },
    heroTexts: { flex: 1, gap: space.xs },
    headline: { ...typo.title, fontSize: 22, lineHeight: 28, fontWeight: "800", color: t.colors.text },
    supporting: { ...typo.supporting, color: t.colors.textSecondary },
  });
