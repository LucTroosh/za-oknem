import Ionicons from "@expo/vector-icons/Ionicons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import appConfig from "../../app.json";
import Card from "../../components/Card";
import useDashboard from "../../components/DashboardProvider";
import useLocation from "../../components/LocationProvider";
import Screen from "../../components/Screen";
import ThemePicker from "../../components/ThemePicker";
import useTheme, { useThemedStyles } from "../../components/useTheme";
import { collectAttributions, withPlaceSource } from "../../lib/sources";
import { MIN_TOUCH, type Theme, space, typo } from "../../lib/theme";

// Location (one, local to the device) + appearance (TASK-12.19) + about + data sources. Topics
// and the privacy policy page arrive with TASK-12.13 / 12.6.
// Sources = the attribution strings the backend sent with the data (shown verbatim).
export default function Settings() {
  const styles = useThemedStyles(createStyles);
  const { colors } = useTheme();
  const router = useRouter();
  const { settings, setTheme } = useLocation();
  const { dashboard, hydro, calendar } = useDashboard();
  const sources = withPlaceSource(collectAttributions(dashboard, hydro, calendar), settings.location?.attribution);
  return (
    <Screen>
      <Card>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Lokalizacja: ${settings.location?.label ?? "nie wybrano"}`}
          accessibilityHint="Otwiera wybór lokalizacji"
          onPress={() => router.push("/location")}
          style={styles.row}
        >
          <View style={styles.rowText}>
            <Text style={styles.heading}>Lokalizacja</Text>
            <Text style={styles.body}>{settings.location?.label ?? "Nie wybrano"}</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
        </Pressable>
      </Card>
      <Card>
        <Text style={styles.heading} accessibilityRole="header">
          Wygląd
        </Text>
        <ThemePicker value={settings.theme} onChange={setTheme} />
        <Text style={styles.meta}>„Systemowy” podąża za ustawieniem telefonu. Rozmiar tekstu zależy od ustawień czcionki w telefonie.</Text>
      </Card>
      <Card>
        <Text style={styles.heading} accessibilityRole="header">
          O aplikacji
        </Text>
        <Text style={styles.body}>
          {appConfig.expo.name} pokazuje, co dzieje się wokół Ciebie: powietrze, pogodę, pyłki i ostrzeżenia.
        </Text>
        <Text style={styles.meta}>Wersja {appConfig.expo.version}</Text>
      </Card>
      <Card>
        <Text style={styles.heading} accessibilityRole="header">
          Źródła danych
        </Text>
        {sources.length === 0 ? (
          <Text style={styles.body}>Lista źródeł pojawi się po załadowaniu danych. Odśwież ekran Start.</Text>
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
          Aplikacja nie wymaga konta i nie tworzy profilu. Nie korzysta z lokalizacji urządzenia. Wybrana miejscowość jest zapamiętana tylko na tym telefonie.
        </Text>
      </Card>
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    heading: { ...typo.heading, color: t.colors.text, marginBottom: space.xs },
    body: { ...typo.body, color: t.colors.text },
    row: { flexDirection: "row", alignItems: "center", gap: space.md, minHeight: MIN_TOUCH },
    rowText: { flex: 1, gap: space.xs },
    meta: { ...typo.caption, color: t.colors.textSecondary, marginTop: space.xs },
  });
