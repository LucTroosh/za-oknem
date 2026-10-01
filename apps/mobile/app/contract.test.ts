import { describe, expect, it } from "vitest";

import type {
  AirIndex,
  DashboardAlerts,
  DashboardArea,
} from "../../../packages/api-contract/schema";
import type { AlertsBlock } from "./alerts";
import type { AirIndexBlock } from "./aqi";
import type { ForecastDay } from "./forecast";
import type { OutdoorBlock } from "./outdoor";
import type { PollenBlock } from "./pollen";

// TASK-2.1 / ADR-024: the UI modules keep their own view types (they tolerate an older
// backend), but everything the server's contract can send must be accepted by them.
// Checked by `tsc` (npm run typecheck) - a contract change the UI cannot handle fails there.
const accept = <T>(value: T): T => value;

function uiAcceptsContract(area: DashboardArea, alerts: DashboardAlerts, index: AirIndex) {
  accept<PollenBlock>(area.pollen);
  accept<OutdoorBlock>(area.outdoor);
  accept<AlertsBlock>(alerts);
  accept<AirIndexBlock>(index);
  accept<ForecastDay[] | undefined>(area.forecast?.days);
}

describe("api-contract", () => {
  it("is checked at compile time against the UI types", () => {
    expect(uiAcceptsContract).toBeTypeOf("function");
  });
});
