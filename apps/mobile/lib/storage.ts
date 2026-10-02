// The only AsyncStorage touchpoint (a native module, so kept out of the unit-tested logic in
// lib/location.ts). Any failure -> defaults / a silent no-op: the app must always start and
// keep working with the choice held in memory (rule #1).
import AsyncStorage from "@react-native-async-storage/async-storage";

import { DEFAULT_SETTINGS, SETTINGS_KEY, type Settings, parseSettings, serializeSettings } from "./location";

export async function loadSettings(): Promise<Settings> {
  try {
    return parseSettings(await AsyncStorage.getItem(SETTINGS_KEY));
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export async function saveSettings(s: Settings): Promise<void> {
  try {
    await AsyncStorage.setItem(SETTINGS_KEY, serializeSettings(s));
  } catch {
    // not persisted: the choice still works until the app is closed
  }
}
