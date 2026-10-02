import { StyleSheet, Text } from "react-native";

import Card from "../../components/Card";
import InfoPage from "../../components/InfoPage";
import { useThemedStyles } from "../../components/useTheme";
import { type Theme, typo } from "../../lib/theme";

// Dostępność: the app follows the phone's own accessibility settings (no extra switches of ours,
// so nothing here can contradict the system). Real behaviour only.
export default function Accessibility() {
  const styles = useThemedStyles(createStyles);
  return (
    <InfoPage title="Dostępność">
      <Card>
        <Text style={styles.title} accessibilityRole="header">
          Ustawienia telefonu
        </Text>
        <Text style={styles.body}>Aplikacja respektuje ustawienia dostępności Twojego telefonu:</Text>
        <Text style={styles.body}>• rozmiar czcionki (Ustawienia → Ekran → Rozmiar czcionki),</Text>
        <Text style={styles.body}>• czytnik ekranu TalkBack,</Text>
        <Text style={styles.body}>• ograniczenie animacji (aplikacja nie używa własnych animacji),</Text>
        <Text style={styles.body}>• jasny i ciemny motyw (zakładka Wygląd).</Text>
      </Card>
      <Card>
        <Text style={styles.title} accessibilityRole="header">
          Jak oznaczamy stany
        </Text>
        <Text style={styles.body}>Stan nigdy nie jest przekazywany samym kolorem: zawsze towarzyszy mu ikona i opis słowny.</Text>
      </Card>
    </InfoPage>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.cardTitle, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
  });
