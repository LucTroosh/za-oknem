import { describe, expect, it } from "vitest";

import type {
  AirIndex,
  DashboardAlerts,
  DashboardResponse,
} from "../../../packages/api-contract/schema";
import type { AlertsBlock } from "./alerts";
import type { AirIndexBlock } from "./aqi";
import type { ForecastDay } from "./forecast";
import type { DashboardArea as ScreenArea, DashboardSourceStatus } from "./index";
import type { OutdoorBlock } from "./outdoor";
import type { PollenBlock } from "./pollen";

// TASK-2.1 / ADR-024: the UI modules keep their own view types (they tolerate an older
// backend), but everything the server's contract can send must be accepted by them.
// Checked by `tsc` (npm run typecheck) - a contract change the UI cannot handle fails there.
const accept = <T>(value: T): T => value;

function uiAcceptsContract(response: DashboardResponse, index: AirIndex) {
  // The exact type index.tsx fetches the dashboard as (air/weather/forecast included).
  accept<{ areas: ScreenArea[]; alerts: AlertsBlock; source_status?: DashboardSourceStatus }>(response);
  const area = response.areas[0];
  const alerts: DashboardAlerts = response.alerts;
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
