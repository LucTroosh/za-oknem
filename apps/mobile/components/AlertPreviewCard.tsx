import { useRouter } from "expo-router";

import type { AlertPreview } from "../lib/start";
import InfoBanner from "./InfoBanner";

// Start's one concise alert card (production UI v1 §7E): a relevant local warning, an
// Neutral info styling only: the source's degree is shown as text, never turned into our own
// red/yellow (ADR-009, rule #10). An uncertainty that matters, or a confirmed all-clear. Always leads to Alerty, never a national wall.
export default function AlertPreviewCard({ preview }: { preview: AlertPreview }) {
  const router = useRouter();
  const go = () => router.navigate("/alerts");
  switch (preview.kind) {
    case "local":
      return <InfoBanner tone="info" text={preview.title} detail={preview.detail} actionLabel="Zobacz w Alertach" onAction={go} />;
    case "unresolved":
      return <InfoBanner tone="info" text={preview.title} detail={preview.detail} actionLabel="Zobacz w Alertach" onAction={go} />;
    case "unknown":
      return <InfoBanner tone="neutral" text={preview.title} detail={preview.detail} actionLabel="Zobacz w Alertach" onAction={go} />;
    default:
      return <InfoBanner tone="good" text={preview.title} />;
  }
}
