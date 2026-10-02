import { StyleSheet, Text } from "react-native";

import Card from "../../components/Card";
import InfoPage from "../../components/InfoPage";
import useLocation from "../../components/LocationProvider";
import SegmentedControl from "../../components/SegmentedControl";
import { useThemedStyles } from "../../components/useTheme";
import { THEME_LABEL, THEME_PREFS, type Theme, typo } from "../../lib/theme";

const OPTIONS = THEME_PREFS.map((value) => ({ value, label: THEME_LABEL[value] }));

// Wygląd: Systemowy | Jasny | Ciemny. "Systemowy" follows the phone live (the default).
export default function Appearance() {
  const { settings, setTheme } = useLocation();
  const styles = useThemedStyles(createStyles);
  return (
    <InfoPage title="Wygląd">
      <Card>
        <SegmentedControl label="Motyw" options={OPTIONS} value={settings.theme} onChange={setTheme} />
        <Text style={styles.note}>„Systemowy” podąża za ustawieniem telefonu. Rozmiar tekstu zależy od ustawień czcionki w telefonie.</Text>
      </Card>
    </InfoPage>
  );
}

const createStyles = (t: Theme) => StyleSheet.create({ note: { ...typo.supporting, color: t.colors.textSecondary } });
