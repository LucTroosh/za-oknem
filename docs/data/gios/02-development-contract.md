# Kontrakt implementacyjny

Status: proponowane rozszerzenie architektury, do utrwalenia w ADR przed implementacją. Nie zmienia istniejących ADR milcząco.

## Repo i komponenty

Stack zachować: Python/FastAPI/Pydantic/SQLAlchemy/Alembic, PostgreSQL/PostGIS, Redis, worker/scheduler; React Native/Expo/TypeScript. Modularny monolit. Istniejący `connectors/gios` obsługuje bieżące powietrze. Nowe izolowane connectory: `gios_air_assessments`, `gios_noise`, `gios_surface_water_programs`, `gios_groundwater`, `gios_prtr`, `gios_major_accidents`, `gios_nec`.

Wspólne narzędzia HTTP/parsers tylko dla faktycznie powtarzalnych mechanizmów. Każdy connector: `fetch → parse → validate → normalize → upsert`, CLI `--validate-only` i import próbki `--file`. Nie używać nowego API historycznego jako zastępstwa JPOAT. Mobile czyta wyłącznie własną bazę.

## Warstwy dowodu i statusy

`SPEC_VERIFIED`: pobrany poprawny OpenAPI; `LIVE_PARTIAL`: przetestowano wybrane żądanie, nie wszystkie operacje; `LIVE_VERIFIED`: konkretna operacja ma udokumentowane pole, próbkę, paginację i jednostki; `APPROVED`: gate źródła zaliczony; `IMPLEMENTED`: kod/testy; `PRODUCTION`: włączone i sprawdzone. Zachować istniejące statusy Source Registry; te etykiety można dodać jako pole evidence, nie zastępować całego workflow.

## HTTP i opakowanie nowych API

Zwykle JSON `dane.strona[]`, `dane.liczbaRekordow`, `wynik.{idZdarzenia,status,data,blad}`. Hałas/zasięgi: `features[]` i `liczbaRekordow` na głównym poziomie. Dokumenty: format PDF/JSON i response zgodny z daną operacją.

1. Timeout połączenia 5 s, odpowiedzi 20 s (nasz budżet, nie obietnica GIOŚ).
2. Maksymalnie 2 ponowienia po pierwszej próbie dla timeout/429/502/503/504; respektować Retry-After, dodać jitter. Nie ponawiać walidacyjnego BLAD/400.
3. Sprawdzić status HTTP ORAZ `wynik.status`. `BLAD` przy HTTP 200 to błąd. Logować kod, opis, id zdarzenia i endpoint bez sekretów.
4. `SUKCES` z `liczbaRekordow=0` i bez `strona` jest zaobserwowanym pustym wynikiem; brak całego opakowania przy niepustym wyniku to błąd kontraktu. Pusta strona nie oznacza globalnego braku danych.
5. Nie mylić `wynik.data` z datą pomiaru. Spec opisuje UTC, próby zwracają czas bez offsetu. Nie lokalizować go automatycznie do UTC bez potwierdzenia. Własny `fetched_at` zawsze aware UTC.
6. Unknown fields zachować w raw; nieznane enumy/zmiany schematu mają wejść do kwarantanny i metryk, nie zniszczyć całego batcha. Jawne adaptery tylko dla zaobserwowanych wariantów.
7. Klucze/API URL wyłącznie config/env. Nie instalować klienta wygenerowanego z OpenAPI bez testu rzeczywistych typów.

### Paginacja

Nowe API: `numerStrony` od 0; `liczbaElementowNaStronie` domyślnie 10, maksymalnie 50 według specyfikacji (sprawdzać per operacja). Bieżące powietrze: `page`, `size`, maksimum deklarowane 500. Nie mieszać parametrów.

Nowe API nie deklaruje jednoznacznego globalnego total dla wszystkich operacji. W próbkach `liczbaRekordow` równa się rozmiarowi strony. Testować strony 0/1/ostatnią, powtarzalność, filtry i kolejność. Do weryfikacji: kończyć po potwierdzonej pustej stronie, chronić się przed powtarzaną stroną przez hash i limitem max_pages (operacyjny bezpiecznik, nie limit dostawcy). Krótka strona może być optymalizacją dopiero po potwierdzeniu zachowania. Wykrywać zmiany danych podczas przejścia; snapshot tylko po kompletnym przebiegu.

### Limity i cykl aktualizacji

JPOAT ma oficjalnie różne limity: 2/min dla części katalogów/metadanych/statystyk/map i 1500/min dla bieżących pomiarów oraz indeksu; dokładne mapowanie operacji utrwalić w Registry. Istniejący client konserwatywnie ogranicza listy, co może być bardziej restrykcyjne. Nie zwiększać limitów na podstawie samego skróconego opisu. Limiter musi działać wspólnie dla workerów (Redis), retry również zużywa token.

Dla nowych siedmiu API specyfikacje nie deklarują rate limit, SLA ani dokładnej częstotliwości publikacji. UNKNOWN jest poprawnym wpisem. Proponowany limiter discovery 1 request/5 s na usługę, równoległość 1 per usługa, jest własnym ograniczeniem, nie rzekomym limitem GIOŚ. Ustawienia konfigurowalne. Discovery może testować różne usługi niezależnie.

Nie włączać cyklicznego pollingu, dopóki Registry nie ma zweryfikowanego cyklu publikacji albo udokumentowanego wyjątku z ADR-004. Dane roczne/wieloletnie: import jednorazowy/manualny i odświeżenie po publikacji. Bieżące pomiary: zachować istniejący godzinowy scheduler. Nie wykonywać pełnego krajowego skanu co godzinę.

## Normalizacja i model danych

Poniższe tabele są propozycją migracji, nie opisem istniejącej bazy. Dopasować do Master Planu i reuse tabel provenance/Measurement/SourceFetch zamiast duplikowania.

| Encja | Klucz / najważniejsze pola | Reguła |
|---|---|---|
| dataset_snapshot | source_id, operation, canonical_filters, source_period, fetched_at, completed_at, status, checksum, schema_hash | osobny snapshot per operacja+filtry; promować atomowo po pełnym ingest |
| source_record | snapshot_id, source_record_id?, natural_key, raw_json, payload_hash, revision | brak ID → wersjonowana deterministyczna kombinacja pól; hash payload nie zastępuje klucza biznesowego |
| monitoring_site | provider, external_code, name, geometry?, crs_original?, administrative_area?, measurement_context | współrzędne tylko z potwierdzonym CRS; nie scalać kodów z różnych namespace |
| observation | site, parameter, numeric_value?, raw_value, qualifier?, unit?, observed_from/to, averaging_period, verification_status | wykorzystać istniejący Measurement dla pomiarów; nie wrzucać planu/klasy do stężenia |
| environmental_assessment | subject_code, subject_geometry?, parameter?, year/period, purpose, source_class, methodology | ocena roczna/wieloletnia osobno od indeksu bieżącego |
| monitoring_program | JCWP/JCWPd/PPK, period, indicator, document_id? | plan bez wartości pomiaru |
| noise_zone | provider_id, mapping_round, source_type, indicator, band, geometry, geometry_verified | GIST; Point nie służy do point-in-polygon |
| industrial_facility | source, source_id?, regon?, name, address/admin, geometry?, geo_quality | REGON+adres/nazwa zakładu, nie sam REGON |
| industrial_release | facility, report_year, pollutant_code, medium, raw_amount, amount?, unit? | brak jednostki blokuje agregację, nie pokazuje zmyślonego kg |
| industrial_waste_transfer | facility, year, transfer_type, process_R_D, raw_mass, mass?, unit? | nie mieszać z emisją do powietrza |
| industrial_event | event_date, place, type, description, facility?, provenance | historia Event, nie aktywny Alert |

Wszystkie rekordy: source_id, operation URL, source_record_id/natural_key, fetched_at, source period/observed_at, licencja, attribution i raw hash. Dla daty samego dnia zachować precision=date, dla roku precision=year; nie wymyślać godziny 00:00 jako czasu pomiaru.

Liczby: używać Decimal dla mas/stężeń wymagających precyzji, preserve raw, separatory dziesiętne akceptować tylko jawnie; `null`, „<0.1”, „TAK”, „NIE” i brak pola nie są zerem. Kod NACE/REGON jest identyfikatorem; rzeczywisty `kodNace=19.10` był liczbą JSON, co traci końcowe zero. Nie odtwarzać go bez słownika. NEC kod stacji bywa liczbą mimo string w spec — kanoniczny string plus raw. Wody podziemne współrzędne są obiektem x/y mimo string w spec, flagi są „TAK” mimo boolean: jawnie mapować TAK/NIE/true/false, inne wartości unknown.

## Geo matching

- Bieżące powietrze: zachować ADR-006/025, odległość 50 km i ujawnić źródłową stację. Aktualizacja doboru per pollutant lub typ tła wymaga ADR; nie składać indeksu ze stacji o różnych godzinach.
- Hałas/pomiar: nearest point + odległość od wybranej miejscowości, wyłącznie opis pomiaru. Nie przyjmować 50 km jako zasięgu reprezentatywności hałasu.
- Hałas/zasięg: ST_Covers dla zweryfikowanej geometrii Polygon/MultiPolygon WGS84, jawny rok/źródło/indikator; overlapping bands obsłużyć deterministycznie per źródło i runda, bez sumowania dB.
- PRTR/PA: dopasowanie administracyjne po uzgodnionym rejestrze i nazwach+hierarchii; identyczna nazwa miejscowości w różnych powiatach nie jest tym samym miejscem. UI „w miejscowości”, nigdy „w promieniu 10 km” bez geometrii zakładu.
- Wody powierzchniowe: wymagana geometria JCWP/PPK z zatwierdzonego źródła. Samo województwo lub nazwa rzeki nie identyfikuje najbliższego odcinka.
- Wody podziemne: rzeczywiste x≈185897, y≈678641 nie są stopniami WGS84. CRS UNKNOWN; potwierdzić, transformować server-side, potem testy znanych punktów. Nie zakładać EPSG:2180 tylko z zakresu liczb. Ocena JCWPd wymaga polygonu JCWPd, nie najbliższego punktu badań.
- NEC: nazwy pól długość/szerokość sugerują lon/lat; próbka odpowiada Polsce. Formalnie potwierdzić CRS, zachować site match zamiast oceny całej okolicy.

## API Za Oknem — propozycja kontraktu

`GET /api/v1/neighborhood?place_id={existing_place_id}` czyta bazę i zwraca sekcje. Reuse istniejącego identyfikatora miejsca; nie dodawać kont ani surowego śledzenia lokalizacji. Finalne nazwy typów uzgodnić z `packages/api-contract`.

```json
{
  "place_id": "existing-place-id",
  "sections": [
    {
      "id": "noise",
      "data_kind": "historical_measurement",
      "availability": "available",
      "freshness": "RECENT",
      "source_period": "2024",
      "observed_from": null,
      "observed_to": null,
      "last_successful_fetch_at": null,
      "spatial_match": "nearby_site",
      "distance_km": null,
      "source_id": "gios_noise",
      "attribution": "Źródło danych: GIOŚ",
      "license_url": "https://creativecommons.org/licenses/by/4.0/",
      "limitations": ["historical_not_live"],
      "items": []
    }
  ]
}
```

To przykład kształtu, nie fixture żywego wyniku. `freshness` w przykładzie jest placeholderem zależnym od polityki źródła, nie oceną danych 2024. `availability`: available/no_coverage/no_records/unavailable/pending_verification (nowe enumy zatwierdzić w ADR). Odróżniać zero rekordów w sprawdzonym zapytaniu od braku pokrycia i awarii. `no_records` wolno zwrócić dopiero po poprawnie zakończonym query/snapshot. Jedna awaria nie zmienia dostępności innych sekcji. Szczegóły i pagination wyników z naszej bazy osobnym endpointem; kliencki API nie ujawnia całego raw.

Freshness nie może oznaczać „świeży pomiar” po ponownym pobraniu historycznego pliku. Zachować istniejące FRESH/RECENT/STALE/UNAVAILABLE i dodać source_period/data_kind; polityka per dataset po potwierdzeniu cyklu. Fresh fetch + assessment z 2022 = aktualnie pobrane historyczne dane. Brak znanego cyklu: pending_verification, nie FRESH.

## Eksploatacja

Każda usługa osobno feature flag, job lock, cursor/checkpoint, liczba stron/odrzuceń/duplikatów, snapshot aktywny i ostatni sukces. Dashboard nie czeka na job. Nie usuwać zakładów/stacji na podstawie niekompletnego snapshotu. Zachować poprzedni dobry snapshot podczas błędu i oznaczyć degraded. Dokumenty PDF/JSON pobierać z allowlist hostów, z limitem rozmiaru, walidacją MIME, bez wykonywania zawartości; nie przekazywać dowolnego URL z użytkownika do fetcha.

Rollback: wyłączyć flagę źródła/UI i jobs, zachować dane i poprzedni kontrakt; migracje addytywne. Rollback bazy tylko przetestowanym Alembic. Nie wykonywać automatycznych DDL/produkcji z promptu.
