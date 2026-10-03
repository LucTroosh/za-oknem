# IMGW — current implementation scope

Basis: [original research pack](implementation-pack-v1.md), read in full 2026-10-03;
[ADR-034](../../architecture/ADR-034-imgw-observations-and-warnings.md).

## First implementation increment and acceptance criteria

| Task | Actual result | Acceptance/status |
|---|---|---|
| IMGW-01 audit | reuse existing hydro, warnings transport, measurements/provenance, scheduler, alert UI | no duplicate forecast/weather stack |
| IMGW-02 evidence | live SYNOP 62 stations, METEO 788, nonempty warnings, catalogue 42 products; actual COSMO manifest | payload+URL+hash retained; time/unit semantics still pending |
| IMGW-03 flags/source gates | weather activation, publication, semantics, timezone; meteo warnings switch; hydro publication false | default off; disabled warnings cannot become all-clear |
| IMGW-04 ingestion | per-param METEO time, null/zero, finite/range/future validation, atomic batches, raw rejected payloads, dedup, retention | replay full fixture; one invalid coordinate station isolated; massive damage retained without replacing good data |
| IMGW-05 stations | source namespaces, METEO coords/elevation from API, SYNOP metadata with null coords | no SYNOP city-centroid substitution; verified SYNOP geometry pending |
| IMGW-06 resolver | additive `/weather/selected`, per-param temp/humidity priority and model fallback | freshness, distance, unit, altitude, outage tests; verified location elevations required; no station hysteresis yet |
| IMGW-07 warnings | real active schema, complete snapshot transaction, revisions/withdrawals, exact county matching, source failure invalidates all-clear | fixture, malformed/empty/reconciliation and county tests; timezone approval pending |
| IMGW-08 Android/insights | existing neutral warning UI accepts county matches, provider labels, device ageing at 15min | final new weather UI and insight migration remain after Design Lead |
| IMGW-09 discovery | actual `COSMO_HVD_00_00` returns a file manifest | no GRIB decoding/parameters/horizon approval yet |
| IMGW-10–12 NWP/radar/benchmark | not implemented in this increment | separate PRs after real file inventory and validation |
| IMGW-13 hydro/history | hydro adapter retained, public results and hydro warnings disabled by default | pending conditions; not a new river-quality feature |

This increment is implementation under gates, not production activation or completion of all
IMGW-01–13. Source metadata gaps do not permit fabricated values. Legacy weather/Outdoor remain
unchanged until new UI consumes the selected block; forecast remains Open-Meteo.

## Evidence

`evidence/manifest.json`: captured time, official response URLs and SHA256. The nonempty
meteo warning concerns fog and contains actual four-digit county codes. `COSMO_HVD_00_00.json`
contains URLs returned by the official product endpoint, not guessed filename templates.
The SRI product request failed; no working radar decoder or mm/h product is claimed.

The full METEO fixture contains one station with invalid/missing geography; 787 catalog rows
and over 2600 measurements parse in a diagnostic replay with UTC as a test hypothesis.
Neither a matching clock nor a successful replay confirms the provider timezone or all units.

## Own API

`GET /api/v1/weather/selected?geo_area_id=...`: known area required (404 otherwise).
`params`: model fallback plus eligible observations for equivalent parameters only.
Each value has value/unit, observed_at/fetched_at, freshness, source/source_type,
station/distance, selection_reason/fallback_reason. `observations`: nearby stations with
all distinct observation variables and retrieval_status. `publication_enabled`: gate outcome.
Attribution and transformation notice follow the pack. Existing weather DTO remains compatible.

`GET /api/v1/alerts/latest?geo_area_id=...`: meteo joins existing alert contract only after
activation. `geo_match=county` or `unresolved`; source degree stays neutral. Start/end distinguish
upcoming from ongoing; no invented safety classes. Disabled all sources means UNAVAILABLE.

## Operator sequence

1. Migration 0020 after 0019; verify PostgreSQL schema/lock behavior in CI/controlled environment.
2. Confirm timezones separately for observations and warnings; field units and measurement levels.
3. Record evidence in source registry; verify METEO and area elevation provenance. No guessing.
4. Configure `IMGW_WEATHER_TIMEZONE`, `IMGW_WEATHER_SEMANTICS_VERIFIED`,
   `IMGW_OBSERVATIONS_ENABLED`, `IMGW_OBSERVATIONS_PUBLICATION_ENABLED`,
   `IMGW_AREA_ELEVATIONS_M` as verified JSON. Empty elevations cause model fallback.
5. `python -m app.connectors.imgw_weather.ingest --dataset meteo`; SYNOP metadata separately.
6. Configure verified `IMGW_WARNINGS_TIMEZONE`, then `IMGW_WARNINGS_ENABLED` and
   `python -m app.connectors.imgw_warningsmeteo.ingest`.
7. Own API smoke: source, time, station, mixed fields, null/zero, withdrawal, failure and matching.
8. Final UI/insights -> build/device QA. No deploy performed by this implementation PR.

Polling starts at 10min for observations and 5min for warnings per research/product decision;
these are not claimed IMGW guarantees. Circuit-breaker policy, comprehensive benchmark and
complete station-selection hysteresis remain follow-up work; retries/locks are bounded now.
