import { StyleSheet, Text } from "react-native";

import Card from "../../components/Card";
import useDashboard from "../../components/DashboardProvider";
import InfoPage from "../../components/InfoPage";
import useLocation from "../../components/LocationProvider";
import { useThemedStyles } from "../../components/useTheme";
import { collectAttributions, withPlaceSource } from "../../lib/sources";
import { type Theme, typo } from "../../lib/theme";

// Źródła danych: attribution strings exactly as the backend sent them with the data (licences
// require them verbatim). The list appears once data has loaded.
export default function Sources() {
  const styles = useThemedStyles(createStyles);
  const { settings } = useLocation();
  const { dashboard, hydro, calendar } = useDashboard();
  const sources = withPlaceSource(collectAttributions(dashboard, hydro, calendar), settings.location?.attribution);
  return (
    <InfoPage title="Źródła danych">
      <Card>
        {sources.length === 0 ? (
          <Text style={styles.body}>Lista źródeł pojawi się po załadowaniu danych. Odśwież ekran Start.</Text>
        ) : (
          sources.map((s) => (
            <Text key={s} style={styles.body}>
              • {s}
            </Text>
          ))
        )}
      </Card>
      <Text style={styles.meta}>Dane mają swoje licencje. Wartości z modeli (prognozy) nie są pomiarami.</Text>
    </InfoPage>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    body: { ...typo.body, color: t.colors.text },
    meta: { ...typo.meta, color: t.colors.textSecondary },
  });
