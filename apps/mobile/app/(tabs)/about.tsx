import { StyleSheet, Text } from "react-native";

import appConfig from "../../app.json";
import Card from "../../components/Card";
import InfoPage from "../../components/InfoPage";
import { useThemedStyles } from "../../components/useTheme";
import { type Theme, typo } from "../../lib/theme";

export default function About() {
  const styles = useThemedStyles(createStyles);
  return (
    <InfoPage title="O aplikacji">
      <Card>
        <Text style={styles.title}>{appConfig.expo.name}</Text>
        <Text style={styles.body}>Pokazuje, co dzieje się wokół Ciebie: powietrze, pogodę, pyłki i ostrzeżenia.</Text>
        <Text style={styles.meta}>Wersja {appConfig.expo.version}</Text>
      </Card>
    </InfoPage>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.heading, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    meta: { ...typo.meta, color: t.colors.textSecondary },
  });
