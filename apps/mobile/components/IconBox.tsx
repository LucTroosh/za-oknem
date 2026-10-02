import Ionicons from "@expo/vector-icons/Ionicons";
import type { ComponentProps } from "react";
import { View } from "react-native";

export type IconName = ComponentProps<typeof Ionicons>["name"];

// Tinted icon container (production UI v1 §1): 36 dp / radius 12 by default; hero 56 / radius 18.
// Always decorative: the label or headline next to it carries the meaning.
export default function IconBox({
  name,
  fg,
  bg,
  size = 36,
  iconSize,
  rounded,
}: {
  name: IconName;
  fg: string;
  bg: string;
  size?: number;
  iconSize?: number;
  rounded?: number;
}) {
  return (
    <View
      importantForAccessibility="no-hide-descendants"
      accessibilityElementsHidden
      style={{ width: size, height: size, borderRadius: rounded ?? Math.round(size / 3), backgroundColor: bg, alignItems: "center", justifyContent: "center" }}
    >
      <Ionicons name={name} size={iconSize ?? Math.round(size * 0.56)} color={fg} />
    </View>
  );
}
