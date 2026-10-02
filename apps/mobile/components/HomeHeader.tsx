import { StyleSheet, Text, View } from "react-native";

import { type Theme, space, typo } from "../lib/theme";
import Skeleton from "./Skeleton";
import { useThemedStyles } from "./useTheme";

// Spec §10: location, date, current temperature. Always on screen; only the name and the
// temperature wait for data (`name` null = still loading).
// TODO(TASK-12.7): the location becomes a control (chevron + picker) once location selection
// exists; until then it is plain text - no dead affordance.
export default function HomeHeader({
  name,
  loading,
  dateText,
  temperature,
}: {
  name: string | null;
  loading: boolean;
  dateText: string;
  temperature: string | null;
}) {
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.row}>
      <View style={styles.left}>
        {loading && name === null ? (
          <Skeleton width="60%" height={28} />
        ) : (
          <Text style={styles.name} accessibilityRole="header">
            {name ?? "Za Oknem"}
          </Text>
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
    name: { ...typo.display, color: t.colors.text },
    date: { ...typo.body, color: t.colors.textSecondary },
    temp: { ...typo.title, color: t.colors.text },
  });
