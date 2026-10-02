import { Image, type ImageSourcePropType, StyleSheet } from "react-native";

import type { StateArt } from "../lib/stateArt";

// Approved 1200x800 PNG fallbacks (no SVG renderer in the project, and none is added for this:
// asset-implementation-v2.md §6). `require` is lazy per illustration, so only the ones a
// screen actually shows are registered/decoded. Always decorative: the native text next to it
// carries the meaning, so it is hidden from TalkBack.
const SOURCES: Record<StateArt, () => ImageSourcePropType> = {
  good: () => require("../assets/za-oknem/illustrations/condition-good-1200x800.png"),
  caution: () => require("../assets/za-oknem/illustrations/condition-caution-1200x800.png"),
  bad: () => require("../assets/za-oknem/illustrations/condition-bad-1200x800.png"),
  noAlerts: () => require("../assets/za-oknem/illustrations/no-alerts-1200x800.png"),
  noData: () => require("../assets/za-oknem/illustrations/no-data-1200x800.png"),
  offline: () => require("../assets/za-oknem/illustrations/offline-1200x800.png"),
  locationRequired: () => require("../assets/za-oknem/illustrations/location-required-1200x800.png"),
};

export default function StateIllustration({ art, height = 140 }: { art: StateArt; height?: number }) {
  return (
    <Image
      source={SOURCES[art]()}
      style={[styles.image, { height }]}
      resizeMode="contain"
      accessible={false}
      importantForAccessibility="no-hide-descendants"
      accessibilityElementsHidden
    />
  );
}

const styles = StyleSheet.create({ image: { width: "100%" } });
