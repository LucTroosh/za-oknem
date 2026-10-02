import { StyleSheet, Text } from "react-native";

import Card from "../../components/Card";
import InfoPage from "../../components/InfoPage";
import { useThemedStyles } from "../../components/useTheme";
import { type Theme, typo } from "../../lib/theme";

// Prywatność: plain statements that match what the app really does (no account, no profile, no
// device location, one place stored on the phone).
export default function Privacy() {
  const styles = useThemedStyles(createStyles);
  return (
    <InfoPage title="Prywatność">
      <Card>
        <Text style={styles.title} accessibilityRole="header">
          Bez konta i bez profilowania
        </Text>
        <Text style={styles.body}>Aplikacja nie wymaga konta i nie tworzy profilu użytkownika.</Text>
      </Card>
      <Card>
        <Text style={styles.title} accessibilityRole="header">
          Lokalizacja
        </Text>
        <Text style={styles.body}>Lokalizację urządzenia odczytujemy tylko wtedy, gdy dotkniesz „Użyj mojej lokalizacji”: jednorazowo, bez śledzenia w tle, a wynik (najbliższa miejscowość) nie jest zapisywany na serwerze. Wybraną miejscowość zapamiętujemy tylko na tym telefonie.</Text>
        <Text style={styles.body}>Do naszego serwera trafia identyfikator wybranej miejscowości, żeby pobrać dla niej dane.</Text>
      </Card>
    </InfoPage>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.cardTitle, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
  });
