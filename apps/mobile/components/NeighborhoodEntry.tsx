import { useRouter } from "expo-router";

import { ENTRY_TITLE, ENTRY_VALUE, entryVisible } from "../lib/neighborhood";
import useNeighborhood from "./useNeighborhood";
import SettingsRow, { SettingsGroup } from "./SettingsRow";

// Secondary row on Start (ADR-032): a way into "Twoja okolica", not part of the dashboard answer.
// Rendered only when the API reports a switched-on section; while loading, on error or on a backend
// without the module it renders nothing, so Start never shows a dead entry.
export default function NeighborhoodEntry({ geoAreaId, refreshTick }: { geoAreaId: number; refreshTick: number }) {
  const router = useRouter();
  const { block } = useNeighborhood(geoAreaId, refreshTick);
  if (!entryVisible(block)) return null;
  return (
    <SettingsGroup>
      <SettingsRow
        icon="home-outline"
        title={ENTRY_TITLE}
        value={ENTRY_VALUE}
        hint="Otwiera dane historyczne o wybranej lokalizacji"
        onPress={() => router.push("/neighborhood")}
        last
      />
    </SettingsGroup>
  );
}
