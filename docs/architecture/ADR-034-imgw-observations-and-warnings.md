# ADR-034 — IMGW observations, warnings and staged publication

Date: 2026-10-03. Status: Proposed, acceptance with this PR.

## Context and problem

The IMGW implementation pack requests IMGW-first selection for equivalent, fresh,
representative Polish weather parameters. The existing app uses Open-Meteo weather,
GIOŚ air and IMGW hydro; the active meteorological warning schema was previously missing.
The pack had not inspected this repository. Its API/table names are proposals, not migrations.

## Options

1. Replace weather provider globally: loses model-only variables and misrepresents station data.
2. Duplicate the weather stack: unnecessary tables/dependencies and incompatible Android DTOs.
3. Reuse measurements/provenance/status, add station metadata and an additive selection contract.

## Decision

Choose 3. Reuse `Measurement`, `SourceFetch`, `SourceStatus` and existing scheduler.
Migration 0020 adds only `imgw_weather_stations`, keyed by source and string station ID.
METEO coordinates/elevation come from the actual API record. SYNOP coordinates remain null;
its metadata is imported, but no measurement receives invented coordinates or a city centroid.

`/weather/selected?geo_area_id=` and optional `dashboard.areas[].selected_weather` expose
selected values with source/type/time/unit/station/distance and selection/fallback reason.
Legacy weather fields and the current outdoor engine stay on Open-Meteo until the approved
UI/insights migration consumes the same selection block. This is a deliberate compatibility
stage, not a completed switch of the user-facing weather provider.

Initially only temperature/humidity may replace equivalent model values. Other observation
variables have separate codes: mean/max wind, 10-minute gust, 10-minute rain, ground temperature,
unspecified-window SYNOP precipitation and unspecified-reference pressure. Never map these to
instantaneous precipitation, generic gust, sea-level pressure or apparent temperature.

Selection requires publication gate, verified source semantics/timezone, fresh per-field time,
correct unit, healthy source, distance ≤25 km and confirmed elevation difference ≤150 m.
No verified area elevation means model fallback. Elevation configuration must carry an operator
record of its source; no elevation guess. Thresholds are product decisions, not IMGW guarantees.
SYNOP data is not eligible until its geometry and equivalence are verified. Station hysteresis,
verified SYNOP catalogue and broader wind/precipitation selection remain follow-up tasks.

A PostgreSQL advisory lock on a dedicated connection covers national fetch+ingest per dataset.
Provenance survives rollback; observations/catalog commit atomically. Up to 2% malformed stations
are isolated (matching existing hydro's policy); above this, retain the previous batch. Duplicate
station IDs reject the whole batch rather than choose by input order. A malformed warning rejects
the entire warning snapshot; no update/withdrawal is visible partially. Exact empty-warning response
is a success. Withdrawals and revisions update atomically, with raw provenance retained.

Meteo county codes are four-character strings from the real active fixture. Match exactly against
a four-digit county or the extracted county of a verified seven-digit TERC code. Voivodeship-only
mapping cannot establish a county match: retain `unresolved`. Preserve leading zeros and original
warning text/degree. Future-start warnings remain visible with their validity times.

Weather/station freshness is per observation, never fetch time. Meteo warning source is trusted
for 15 minutes only, and a failed last attempt immediately invalidates a confirmed all-clear;
the mobile clock can only downgrade freshness. Hydro publication is default off per the pack;
ingest/storage are retained, so approval can enable publication later without rebuilding adapters.

## Consequences and activation

No new production dependency. New adapters/publication are default off; no guessed timezone.
The settings accept only valid IANA zones. Zone syntax validity does not prove source semantics.
Replay tests using UTC/Europe-Warsaw are hypotheses, not timezone approval.

Before activation: migrate 0020; confirm timezone/unit/level/statistic metadata on official API
material or IMGW response; update source registry with evidence; set flags; verify a controlled
national run and own API; migrate UI/insights to the shared selection. Rollback disables the
new flags and restores model selection without deleting data. Hydro stays unpublished until
its conditions are resolved. Build and device QA follow the new UI, per the owner.
