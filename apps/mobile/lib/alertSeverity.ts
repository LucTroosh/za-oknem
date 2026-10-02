import type { Tone } from "./theme";

// Severity of an alert as the SOURCE rates it (IMGW stopień 1–3), kept apart from relevance to the
// user's location (production UI v1 review). Only the documented degrees are mapped; anything else
// stays neutral rather than being guessed into a colour (rule #10: no own severity rating).
export function severityTone(severityRaw: string | null | undefined): Tone {
  const degree = String(severityRaw ?? "").trim();
  if (degree === "3") return "danger";
  if (degree === "1" || degree === "2") return "warning";
  return "neutral";
}
