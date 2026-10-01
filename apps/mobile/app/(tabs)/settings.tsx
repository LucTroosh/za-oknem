import { StyleSheet, Text } from "react-native";

import appConfig from "../../app.json";
import Card from "../../components/Card";
import useDashboard from "../../components/DashboardProvider";
import Screen from "../../components/Screen";
import { useThemedStyles } from "../../components/useTheme";
import { collectAttributions } from "../../lib/sources";
import { type Theme, space, typo } from "../../lib/theme";

// Placeholder (TASK-12.1): about + data sources. Location, profile, allergies and
// notifications arrive with TASK-12.2-12.4; the privacy policy page with TASK-12.6.
// Sources = the attribution strings the backend sent with the data (shown verbatim).
export default function Settings() {
  const styles = useThemedStyles(createStyles);
  const { dashboard, hydro, calendar } = useDashboard();
  const sources = collectAttributions(dashboard, hydro, calendar);
  return (
    <Screen>
      <Card>
        <Text style={styles.heading} accessibilityRole="header">
          O aplikacji
        </Text>
        <Text style={styles.body}>
          {appConfig.expo.name} pokazuje, co dzieje się wokół Ciebie: powietrze, pogodę, pyłki, wodę i ostrzeżenia.
        </Text>
        <Text style={styles.meta}>Wersja {appConfig.expo.version}</Text>
      </Card>
      <Card>
        <Text style={styles.heading} accessibilityRole="header">
          Źródła danych
        </Text>
        {sources.length === 0 ? (
          <Text style={styles.body}>Lista źródeł pojawi się po załadowaniu danych. Odśwież widok Home.</Text>
        ) : (
          sources.map((s) => (
            <Text key={s} style={styles.body}>
              • {s}
            </Text>
          ))
        )}
        <Text style={styles.meta}>Dane mają swoje licencje. Wartości z modeli (prognozy) nie są pomiarami.</Text>
      </Card>
      <Card>
        <Text style={styles.heading} accessibilityRole="header">
          Prywatność
        </Text>
        <Text style={styles.body}>
          Aplikacja nie wymaga konta i nie korzysta z lokalizacji urządzenia. Obszary pokazywane na Home są stałą listą.
        </Text>
      </Card>
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    heading: { ...typo.heading, color: t.colors.text, marginBottom: space.xs },
    body: { ...typo.body, color: t.colors.text },
    meta: { ...typo.caption, color: t.colors.textSecondary, marginTop: space.xs },
  });
