# ADR-014: Raw ingestion i provenance (`source_fetches`)

- **Date:** 2026-09-30
- **Status:** Accepted

## Context

Master Plan §33-34: każde źródło przechodzi SOURCE → RAW FETCH → RAW PAYLOAD →
PARSER → NORMALIZED → VALIDATION, a raw payload jest trzymany 7-30 dni, żeby
dało się odpowiedzieć „co dokładnie zwróciło źródło w momencie, gdy zapisaliśmy
tę wartość?”. Dziś connectory zapisują wyłącznie znormalizowane rekordy
(`Measurement`, `WeatherSnapshot`, `Forecast`, `Alert`). Nie wiemy więc, jaki
payload i jaka wersja parsera dały daną wartość, a po zmianie kształtu API
źródła nie ma czego debugować. Numer ADR-013 jest zarezerwowany dla `Event`.

## Problem

1. Gdzie trzymać surowy payload i metadane pobrania (rule #6: źródło, endpoint,
   timestampy, wersja parsera, status walidacji)?
2. Jak jednoznacznie powiązać rekord z payloadem, gdy ten sam
   `source_record_id` pojawia się w kolejnych pobraniach?
3. Co z rozmiarem (payload IMGW hydro = wszystkie stacje, setki KB na godzinę) i
   z retencją?
4. Co, gdy zapis provenance się nie uda (rule #1)?

## Options

1. **Plik/S3 z payloadem, w bazie tylko ścieżka.** Drugi system do backupu
   (TASK-1.1 obejmuje tylko PostgreSQL), brak transakcyjności.
2. **Kolumna `raw_payload` na każdym znormalizowanym rekordzie.** Ten sam
   payload powielony N razy (jedno pobranie Open-Meteo = kilkadziesiąt wierszy).
3. **Osobna tabela `source_fetches` + nullable FK `source_fetch_id` na
   rekordach.** Jeden payload na pobranie, link jednoznaczny.

## Decision

Opcja 3.

- **Tabela `source_fetches`** (PostgreSQL, rule #2): `id`, `source_id`,
  `endpoint`, `fetched_at`, `parser_version`, `validation_status`, `payload`
  (JSONB w Postgresie; `JSON().with_variant(JSONB, "postgresql")`, więc SQLite w
  testach działa tym samym modelem). Migracja Alembic 0009 (rule #4).
- **`source_fetch_id`** (nullable, indeksowane FK) na `measurements`, `alerts`,
  `weather_snapshots`, `forecasts`. NULL = rekord sprzed TASK-3.1 (bez
  backfillu — payloadów już nie ma) albo nieudany zapis provenance.
- **Granularność pobrania = jedno żądanie HTTP, którego odpowiedź daje rekordy:**
  GIOŚ — jedno `getData/{sensorId}` na parametr (jeden rekord ↔ jeden payload);
  Open-Meteo — jedna odpowiedź na `geo_area` (snapshoty + godzinowe + forecast);
  IMGW hydro i ostrzeżenia hydro — cała odpowiedź. Listy stacji/sensorów GIOŚ
  nie są zapisywane: dają tylko metadane (nazwa, współrzędne), nie wartość.
  Payload = zdekodowany JSON odpowiedzi (nie bajty HTTP).
- **Zapis przed parsowaniem.** Payload jest zapisywany także wtedy, gdy parser
  go odrzuca (status `invalid`) — to jest przypadek, dla którego raw payload
  istnieje (zmiana kształtu API). `validation_status`: `pending` (zapisany,
  parsowanie niedokończone — widoczne po crashu w trakcie), `valid`, `partial`
  (część rekordów/bloków odrzucona), `invalid` (payload nieużyteczny).
  Każdy connector zapisuje `pending` zaraz po
  otrzymaniu odpowiedzi i ustawia status po przetworzeniu (`set_validation_status`).
- **`parser_version`** = stała `PARSER_VERSION` w `parser.py` connectora; ręczny
  bump przy zmianie wyniku parse/normalize (także zbioru żądanych pól).
- **Best-effort, bez blokowania ingestu (rule #1).** Nieudany zapis
  `source_fetches` jest logowany i zwraca `None`; znormalizowane rekordy
  zapisują się z `source_fetch_id = NULL`. Świadomy wybór: alert powodziowy lub
  odczyt PM2.5 ważniejsze dla użytkownika niż kompletność śladu audytowego, a
  NULL jest wykrywalny zapytaniem. Odwrotnie: awaria zapisu rekordów
  znormalizowanych nie kasuje payloadu (zapisany wcześniej, osobnym commitem).
  Przy odświeżeniu istniejącego rekordu (`Alert`, próg hydro) FK jest nadpisywany
  także wartością NULL — brak linku jest uczciwszy niż link do starszego
  payloadu, który nie dał bieżących wartości. Rekord pominięty jako duplikat
  zachowuje link do pobrania, które go wytworzyło.
- **Retencja** (`app/provenance.py`, `RETENTION_DAYS`; Master Plan §33 7-30
  dni): `open_meteo` 7 (nie dane bezpieczeństwa, prognoza do ponownego
  pobrania), `imgw_hydro` 7 (payload wszystkich stacji, najcięższy),
  `gios` 14, `imgw_warningshydro` 30 (dane bezpieczeństwa, rule #10 — najdłuższe
  okno audytowe). Źródło spoza listy dostaje najkrótsze okno (7) — nowy
  connector musi świadomie wybrać dłuższe. Retencja **zeruje `payload`
  (SQL NULL), nie kasuje wiersza**: endpoint, `parser_version`, status i
  `fetched_at` zostają, FK nigdy nie wisi, a czyszczenie to jeden idempotentny
  `UPDATE` bez obsługi FK. Wiersz to ok. 200 B; rośnie proporcjonalnie do
  liczby pobrań (mniej niż same rekordy znormalizowane, które też nie mają
  retencji). `# ponytail:` jeśli rozmiar tabeli zacznie przeszkadzać — kasować
  wiersze starsze niż N miesięcy i zerować FK.
- **Job czyszczący** `run_raw_retention` w schedulerze (raz na dobę, ADR-007),
  przez `_run_job_safely(..., track_status=False)` — izolacja błędów (rule #1) i
  brak wiersza w `source_status` (to nie źródło danych, ADR-012).
- **Bez zmian w API.** Mobile API dalej czyta tylko znormalizowane tabele
  (rule #14); `source_fetches` jest dla audytu/debugowania (zapytanie SQL).

## Consequences

- Odpowiedź na pytanie audytowe §33: `rekord.source_fetch_id → source_fetches`
  (endpoint, czas, wersja parsera, status, payload w oknie retencji).
- Koszt miejsca: szacunkowo hydro ≤ ~80 MB w oknie 7 dni (TOAST kompresuje
  JSONB), reszta pomijalna; do zweryfikowania na produkcji (TASK-15.2).
- Dodatkowy INSERT + UPDATE statusu (2 commity) na pobranie.
- Każdy nowy connector (CAMS, `Event`, kąpieliska) woła
  `provenance.record_fetch()` tym samym kontraktem i ustala okno retencji.
- Rekordy sprzed 0009 mają NULL — pytanie audytowe o nie pozostaje bez
  odpowiedzi.
- Nie ma deduplikacji identycznych payloadów (np. godzinowy hydro bez zmian);
  dodać hash, jeśli retencja okaże się za droga.
