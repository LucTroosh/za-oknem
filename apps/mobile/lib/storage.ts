// The only AsyncStorage touchpoint (a native module, so kept out of the unit-tested logic in
// lib/location.ts). Any failure -> defaults / a silent no-op: the app must always start and
// keep working with the choice held in memory (rule #1).
import AsyncStorage from "@react-native-async-storage/async-storage";

import { SETTINGS_KEY, type Settings, readSettings, serializeSettings } from "./location";

export const loadSettings = (): Promise<{ settings: Settings; ok: boolean }> =>
  readSettings(() => AsyncStorage.getItem(SETTINGS_KEY), 4000);

export async function saveSettings(s: Settings): Promise<void> {
  try {
    await AsyncStorage.setItem(SETTINGS_KEY, serializeSettings(s));
  } catch {
    // not persisted: the choice still works until the app is closed
  }
}
