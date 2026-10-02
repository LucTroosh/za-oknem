import Ionicons from "@expo/vector-icons/Ionicons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MIN_TOUCH, type Theme, space, typo } from "../lib/theme";
import Skeleton from "./Skeleton";
import useTheme, { useThemedStyles } from "./useTheme";

// Spec §10: location, date, current temperature. Always on screen; only the name and the
// temperature wait for data (`name` null = still loading).
// The location name is a button (chevron) that opens the picker (spec §10); ONE location.
export default function HomeHeader({
  name,
  loading,
  dateText,
  temperature,
  onChangeLocation,
}: {
  name: string | null;
  loading: boolean;
  dateText: string;
  temperature: string | null;
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
            <Text style={styles.name} importantForAccessibility="no">
              {name ?? "Za Oknem"}
            </Text>
            <Ionicons name="chevron-down" size={24} color={colors.textSecondary} />
          </Pressable>
        )}
        <Text style={styles.date}>{dateText}</Text>
      </View>
      {temperature !== null && (
        <Text style={styles.temp} accessibilityLabel={`Teraz ${temperature}`}>
          {temperature}
        </Text>
      )}
    </View>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: space.md },
    left: { flex: 1, gap: space.xs },
    nameRow: { flexDirection: "row", alignItems: "center", gap: space.xs, minHeight: MIN_TOUCH, alignSelf: "flex-start" },
    name: { ...typo.display, color: t.colors.text, flexShrink: 1 },
    date: { ...typo.body, color: t.colors.textSecondary },
    temp: { ...typo.title, color: t.colors.text },
  });
