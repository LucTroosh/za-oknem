import InfoBanner from "./InfoBanner";

// Inline notice (e.g. a failed refresh while older data is still on screen).
export default function Notice({ tone, text }: { tone: "warning" | "danger" | "info" | "neutral"; text: string }) {
  return <InfoBanner tone={tone} text={text} />;
}
