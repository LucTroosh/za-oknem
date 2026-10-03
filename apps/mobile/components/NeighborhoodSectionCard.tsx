import { Linking, Pressable, StyleSheet, Text, View } from "react-native";

import type { SectionView } from "../lib/neighborhood";
import { MIN_TOUCH, type Theme, space, typo } from "../lib/theme";
import Card from "./Card";
import InfoBanner from "./InfoBanner";
import useTheme, { useThemedStyles } from "./useTheme";

// One section of "Twoja okolica": calm answer first (what applies to this place, from which period,
// what it means), technical detail (purpose, source, licence, limits) below. Historical data: no
// freshness badge, no alert styling (rule #7). `failed` and `empty` read differently on purpose.
export default function NeighborhoodSectionCard({ view }: { view: SectionView }) {
  const styles = useThemedStyles(createStyles);
  const { colors } = useTheme();
  const link = (label: string, url: string) => (
    <Pressable accessibilityRole="link" accessibilityLabel={label} onPress={() => void Linking.openURL(url)} style={styles.link}>
      <Text style={[styles.meta, { color: colors.accent }]}>{label}</Text>
    </Pressable>
  );
  return (
    <Card>
      <Text style={styles.kicker} accessibilityRole="header">
        {view.title}
      </Text>
      <Text style={styles.headline}>{view.headline}</Text>
      {view.body ? <Text style={styles.body}>{view.body}</Text> : null}
      {view.retrievalNotice ? <InfoBanner tone="warning" text={view.retrievalNotice} /> : null}

      {view.items.map((item) => (
        <View
          key={item.key}
          style={styles.item}
          accessible
          accessibilityLabel={[item.title, item.place, item.distance, item.period ? `okres ${item.period}` : null, ...item.rows.map((r) => `${r.label}: ${r.value}${r.note ? `, ${r.note}` : ""}`)]
            .filter(Boolean)
            .join(". ")}
        >
          <Text style={styles.itemTitle}>{item.title}</Text>
          <Text style={styles.body}>
            {item.place} · {item.distance}
          </Text>
          {item.period ? <Text style={styles.meta}>Okres pomiaru: {item.period}</Text> : null}
          {item.rows.map((r) => (
            <View key={r.label} style={styles.row}>
              <Text style={styles.body}>{r.label}</Text>
              <Text style={styles.value}>{r.value}</Text>
              {r.note ? <Text style={styles.meta}>{r.note}</Text> : null}
            </View>
          ))}
          {item.purpose ? <Text style={styles.meta}>Cel pomiaru: {item.purpose}</Text> : null}
        </View>
      ))}

      {view.limitations.map((l) => (
        <Text key={l} style={styles.meta}>
          {l}
        </Text>
      ))}
      <Text style={styles.meta}>{view.attribution}</Text>
      <View style={styles.links}>
        {link("Źródło: dane.gios.gov.pl", view.sourceUrl)}
        {link("Licencja CC BY 4.0", view.licenseUrl)}
      </View>
    </Card>
  );
}

const createStyles = (t: Theme) =>
  StyleSheet.create({
    kicker: { ...typo.caption, color: t.colors.textSecondary, fontWeight: "700", textTransform: "uppercase" },
    headline: { ...typo.title, color: t.colors.text },
    body: { ...typo.body, color: t.colors.text },
    meta: { ...typo.meta, color: t.colors.textSecondary },
    value: { ...typo.title, color: t.colors.text },
    item: { gap: space.xs, paddingTop: space.sm },
    itemTitle: { ...typo.body, color: t.colors.text, fontWeight: "700" },
    row: { gap: 2, paddingTop: space.xs },
    links: { flexDirection: "row", flexWrap: "wrap", columnGap: space.lg },
    link: { minHeight: MIN_TOUCH, justifyContent: "center" },
  });
