import { StyleSheet, Text } from "react-native";

import { pollenView } from "../app/pollen";
import { type Theme, space, typo } from "../app/theme";
import Card from "./Card";
import useTheme, { useThemedStyles } from "./useTheme";

// TASK-8.8: one card per location. All wording/levels come from app/pollen.ts + the
// backend block; this only lays it out. Renders nothing when the backend sent no
// `pollen` (older backend). Always shows the attribution (ADR-020: CAMS + Open-Meteo).
// The level is spelled out in words ("sezon", "szczyt"), the colour only reinforces it.
const LEVEL_KEY = { BELOW_SEASON: "good", SEASON: "warning", PEAK: "danger" } as const;

// null for an unparsable timestamp: never render "Invalid Date".
function format(iso: string | null, opts: Intl.DateTimeFormatOptions): string | null {
  if (iso === null || Number.isNaN(new Date(iso).getTime())) return null;
  return new Date(iso).toLocaleString("pl-PL", opts);
}

export default function PollenCard({ pollen }: { pollen: unknown }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(createStyles);
  const view = pollenView(pollen);
  if (!view) return null;
  const fetched = format(view.fetchedAt, { dateStyle: "short", timeStyle: "short" });
  const validHour = format(view.validAt, { hour: "2-digit", minute: "2-digit" });
  return (
    <Card>
      <Text style={styles.title} accessibilityRole="header">
        {view.title}
      </Text>
      {view.status && (
        <Text style={view.state === "recent" ? styles.note : styles.status}>{view.status}</Text>
      )}
      {view.lines.map((line) => (
        <Text key={line.species} style={styles.line}>
          {line.name}:{" "}
          <Text style={line.level ? { color: colors[LEVEL_KEY[line.level]], fontWeight: "600" } : styles.note}>
            {line.text}
          </Text>
        </Text>
      ))}
      {view.lines.length > 0 && validHour && <Text style={styles.note}>wartości na godz. {validHour}</Text>}
      {fetched && <Text style={styles.note}>pobrano {fetched}</Text>}
      <Text style={styles.micro}>{view.note}</Text>
      <Text style={styles.micro}>{view.attribution}</Text>
    </Card>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    title: { ...typo.heading, color: t.colors.text, marginBottom: space.xs },
    line: { ...typo.body, color: t.colors.text },
    status: { ...typo.body, color: t.colors.warning },
    note: { ...typo.caption, color: t.colors.textSecondary },
    micro: { ...typo.micro, color: t.colors.textSecondary },
  });
