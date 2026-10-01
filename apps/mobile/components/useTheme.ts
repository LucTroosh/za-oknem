import { useMemo } from "react";
import { useColorScheme } from "react-native";

import { type Theme, paletteFor } from "../app/theme";

// Follows the system setting live (app.json: userInterfaceStyle "automatic").
export default function useTheme(): Theme {
  const scheme = useColorScheme();
  return useMemo(() => ({ scheme: scheme === "dark" ? "dark" : "light", colors: paletteFor(scheme) }), [scheme]);
}

// `factory` must be module-level (stable), so styles are rebuilt only when the theme flips.
export function useThemedStyles<T>(factory: (t: Theme) => T): T {
  const theme = useTheme();
  return useMemo(() => factory(theme), [factory, theme]);
}
