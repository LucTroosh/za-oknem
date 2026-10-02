import Ionicons from "@expo/vector-icons/Ionicons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { WeatherIcon } from "../lib/weatherIcon";
import { MIN_TOUCH, type Theme, space, typo } from "../lib/theme";
import Skeleton from "./Skeleton";
import useTheme, { useThemedStyles } from "./useTheme";

// Compact header (production UI v1 §3): location + chevron + date on the left, current
// temperature (+ glyph, + today's range) on the right. No card, no border. The temperature
// waits for data; the name is a button that opens the location picker (ONE location).
export default function HomeHeader({
  name,
  loading,
  dateText,
  temperature,
  range,
  icon,
  onChangeLocation,
}: {
  name: string | null;
  loading: boolean;
  dateText: string;
  temperature: string | null;
  range?: string | null;
  icon?: WeatherIcon | null;
  onChangeLocation: () => void;
}) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.row}>
      <View style={styles.left}>
        {loading && name === null ? (
          <Skeleton width="60%" height={28} />
        ) : (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Lokalizacja: ${name ?? "Za Oknem"}. Zmień`}
            accessibilityHint="Otwiera wybór lokalizacji"
            onPress={onChangeLocation}
            style={styles.nameRow}
          >
            <Ionicons name="location" size={20} color={colors.accent} importantForAccessibility="no" />
            <Text style={styles.name} importantForAccessibility="no" numberOfLines={2}>
              {name ?? "Za Oknem"}
            </Text>
            <Ionicons name="chevron-down" size={20} color={colors.textSecondary} importantForAccessibility="no" />
          </Pressable>
        )}
        <Text style={styles.date}>{dateText}</Text>
      </View>
      {(temperature !== null || range) && (
        <View style={styles.right} accessible accessibilityLabel={[temperature ? `Teraz ${temperature}` : null, range].filter(Boolean).join(", ")}>
          {temperature !== null && (
            <View style={styles.tempRow}>
              {icon ? <Ionicons name={icon} size={22} color={colors.weatherFg} importantForAccessibility="no" /> : null}
              <Text style={styles.temp}>{temperature}</Text>
            </View>
          )}
          {range ? <Text style={styles.range}>{range}</Text> : null}
        </View>
      )}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    // Wraps instead of colliding: at large system font the temperature block drops below the name.
    row: { flexDirection: "row", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", columnGap: space.md },
    left: { flexGrow: 1, flexShrink: 1, flexBasis: "55%", minWidth: 150 },
    nameRow: { flexDirection: "row", alignItems: "center", gap: space.xs, minHeight: MIN_TOUCH, alignSelf: "flex-start" },
    name: { ...typo.display, fontSize: 24, lineHeight: 30, color: t.colors.text, flexShrink: 1 },
    date: { ...typo.caption, color: t.colors.textSecondary, marginTop: -space.sm },
    right: { alignItems: "flex-end", flexGrow: 0, paddingTop: space.sm },
    tempRow: { flexDirection: "row", alignItems: "center", gap: space.xs },
    temp: { ...typo.title, fontSize: 24, lineHeight: 30, fontWeight: "800", color: t.colors.text },
    range: { ...typo.meta, color: t.colors.textSecondary },
  });
