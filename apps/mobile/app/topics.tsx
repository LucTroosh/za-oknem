import { Redirect, useRouter } from "expo-router";
import { StyleSheet, Text } from "react-native";

import Button from "../components/Button";
import useLocation from "../components/LocationProvider";
import Screen from "../components/Screen";
import TopicsPicker from "../components/TopicsPicker";
import { useThemedStyles } from "../components/useTheme";
import { entryRedirect } from "../lib/location";
import { type Theme, space, typo } from "../lib/theme";

// Last onboarding step (TASK-12.13): "Co chcesz śledzić?". Skippable by just continuing (all
// modules stay on), changeable later in Settings. Reached right after the first location pick.
export default function Topics() {
  const styles = useThemedStyles(createStyles);
  const router = useRouter();
  const { settings, setTopics } = useLocation();
  const redirect = entryRedirect(settings, "tabs");
  if (redirect !== null) return <Redirect href={redirect} />;
  return (
    <Screen padTop>
      <Text style={styles.title} accessibilityRole="header">
        Co chcesz śledzić?
      </Text>
      <Text style={styles.supporting}>
        Wybierz, co pokazywać na ekranie Start. To tylko ustawienie na tym telefonie, nie profil. Bez wyboru pokazujemy wszystko.
      </Text>
      <TopicsPicker value={settings.topics} onChange={setTopics} />
      <Text style={styles.supporting}>Ostrzeżenia o zagrożeniu zawsze pokażemy na Start, niezależnie od wyboru.</Text>
      <Button label="Dalej" hint="Przechodzi do ekranu Start" onPress={() => router.replace("/")} />
    </Screen>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.display, color: t.colors.text },
    supporting: { ...typo.body, color: t.colors.textSecondary, marginVertical: space.xs },
  });
