import { useRouter } from "expo-router";

import appConfig from "../../app.json";
import useLocation from "../../components/LocationProvider";
import { TabTitle } from "../../components/PageHeader";
import Screen from "../../components/Screen";
import SettingsRow, { SettingsGroup } from "../../components/SettingsRow";
import { THEME_LABEL } from "../../lib/theme";

// Ustawienia (production UI v1 §13): a clean navigation list; every long text lives on its own
// sub-page. No topic/profile settings: every available module is always shown.
export default function Settings() {
  const router = useRouter();
  const { settings } = useLocation();
  return (
    <Screen padTop gap={16}>
      <TabTitle title="Ustawienia" />
      <SettingsGroup>
        <SettingsRow icon="location-outline" title="Lokalizacja" value={settings.location?.label ?? "Nie wybrano"} onPress={() => router.push("/location")} hint="Otwiera wybór lokalizacji" />
        <SettingsRow icon="color-palette-outline" title="Wygląd" value={THEME_LABEL[settings.theme]} onPress={() => router.push("/appearance")} />
        <SettingsRow icon="accessibility-outline" title="Dostępność" onPress={() => router.push("/accessibility")} />
        <SettingsRow icon="shield-checkmark-outline" title="Prywatność" onPress={() => router.push("/privacy")} />
        <SettingsRow icon="server-outline" title="Źródła danych" onPress={() => router.push("/sources")} />
        <SettingsRow icon="information-circle-outline" title="O aplikacji" value={`Wersja ${appConfig.expo.version}`} onPress={() => router.push("/about")} last />
      </SettingsGroup>
    </Screen>
  );
}
