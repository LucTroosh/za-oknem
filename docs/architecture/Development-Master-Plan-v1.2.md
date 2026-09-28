# ZA OKNEM

## Engineering Master Plan & App Store Release Specification

**Wersja:** 1.2
**Status:** FINAL / SOURCE OF TRUTH
**Typ produktu:** aplikacja mobilna iOS + Android (Android jako pierwszy release)
**Nazwa:** Za Oknem
**Rynek początkowy:** Polska
**Data:** 28.09.2026

---

# HISTORIA ZMIAN

## v1.2 (28.09.2026)

1. **Architektura danych pogodowych i pyłkowych** — dodano ADR-001: mobile API nigdy
   nie woła Open-Meteo/CAMS bezpośrednio; dane są pobierane przez scheduler jako
   snapshot per gmina i czytane z PostgreSQL. Patrz §35, §55, §106.
2. **Push i obserwowany obszar** — dodano ADR-002: `devices` przechowuje
   `observed_area_code` (TERYT), nie surowe współrzędne GPS. Patrz §50, §66.
3. **Dostawca pogody i licencja** — dodano ADR-003: Open-Meteo na darmowym,
   niekomercyjnym tierze, dopóki aplikacja jest bezpłatna, bez reklam, subskrypcji i
   bez Patronite/innego stałego wsparcia finansowego. Rewizja ADR-003 wymagana PRZED
   włączeniem którejkolwiek z tych rzeczy. Patrz §106, §109, §38.
4. **Pyłki / CAMS jako osobne źródło** — doprecyzowano: pyłki i CAMS Air pobierane
   bezpośrednio z Copernicus Atmosphere Data Store (ADS), nie przez Open-Meteo. Patrz §106.
5. **Google Play account** — przesądzono: **Personal**, nie Organization (publikacja
   na razie jako osoba prywatna / projekt social-impact). Patrz §88.
6. **Kolejność platform** — doprecyzowano: Android pierwszy w praktyce (kod pisany
   iOS-safe od początku), iOS równolegle do lub po rozpoczęciu closed testingu na
   Androidzie, nie wcześniej. Bez zmiany docelowych platform w §123. Patrz §107, §123.

Pełne uzasadnienia decyzji 1–4 są w `docs/architecture/ADR-001/002/003`, nie powtarzamy
ich tutaj — ten dokument odwołuje się do ADR-ów w miejscach, których dotyczą.

---

# 0. STATUS DOKUMENTU

Ten dokument jest nadrzędną specyfikacją techniczną, produktową i release'ową projektu **Za Oknem**.

Dokument powinien być traktowany jako:

* Product Specification
* Engineering Specification
* Architecture Specification
* Data Architecture Specification
* Development Roadmap
* QA Specification
* Privacy / Security baseline
* App Store Release Specification
* Governance dla Claude Code

Jeżeli podczas implementacji pojawi się potrzeba zmiany decyzji opisanej tutaj, zmiana nie powinna być wykonywana „przy okazji”.

Należy:

1. zidentyfikować problem,
2. opisać proponowaną zmianę,
3. określić wpływ na architekturę,
4. przygotować lub zaktualizować ADR,
5. zatwierdzić zmianę,
6. dopiero następnie implementować.

---

# 1. DEFINICJA PRODUKTU

## 1.1. Czym jest Za Oknem

Za Oknem odpowiada na jedno proste pytanie:

> **„Co dzieje się wokół mnie?”**

Aplikacja zbiera rozproszone dane z wielu źródeł i prezentuje je użytkownikowi w jednym lokalnym kontekście.

Nie jest to wyłącznie:

* aplikacja pogodowa,
* aplikacja smogowa,
* aplikacja alergiczna,
* aplikacja kryzysowa,
* aplikacja do oceny nieruchomości,
* ranking miejsc do życia,
* uniwersalny „Green Index”.

Podstawowa definicja produktu:

> **Za Oknem to lokalny agregator informacji o tym, co aktualnie dzieje się wokół użytkownika.**

---

# 2. GŁÓWNA WARTOŚĆ PRODUKTU

Obecnie dane są rozproszone pomiędzy:

* GIOŚ,
* IMGW,
* CAMS,
* Open-Meteo,
* źródła pyłkowe,
* Sanepid/GIS,
* źródła hydrologiczne,
* systemy ostrzegania,
* źródła społecznościowe,
* przyszłe źródła środowiskowe.

Użytkownik nie powinien wiedzieć:

* z jakiego API pochodzi dana wartość,
* gdzie znajduje się stacja,
* jak działa model CAMS,
* jak działa PostGIS,
* jak działa pipeline,
* jak pobierane są dane.

Powinien otworzyć:

**Za Oknem**

i zobaczyć:

> **Co dzieje się wokół mnie?**

---

# 3. PRODUCT PRINCIPLES

## Principle 1 — Data first, interpretation second

Najpierw pokazujemy dane.

Dopiero potem możemy je interpretować.

---

## Principle 2 — Source transparency

Istotne dane powinny mieć:

* źródło,
* timestamp,
* informację o świeżości,
* opcjonalnie link do źródła.

---

## Principle 3 — Freshness matters

Nie pokazujemy starego pomiaru jako aktualnego.

Każdy rekord ma status świeżości.

---

## Principle 4 — Measurement ≠ Forecast ≠ Alert

Musimy jednoznacznie rozróżniać:

* pomiar,
* prognozę,
* zdarzenie,
* alert,
* dane wyliczone.

---

## Principle 5 — Safety-critical data requires deterministic sources

LLM nie może być źródłem prawdy dla:

* ostrzeżeń,
* zagrożeń,
* zamknięć kąpielisk,
* jakości wody,
* komunikatów bezpieczeństwa,
* oficjalnych alertów.

---

## Principle 6 — One broken source must not break the product

Awaria pojedynczego źródła nie może spowodować awarii całego dashboardu.

---

## Principle 7 — Don't collect data without a reason

Nie zbieramy lokalizacji, identyfikatorów, analytics ani innych danych „na wszelki wypadek”.

---

## Principle 8 — No unnecessary permissions

MVP używa wyłącznie niezbędnych uprawnień.

W szczególności:

**brak background location w MVP.**

---

## Principle 9 — Mobile first

Podstawowym produktem jest aplikacja mobilna.

PWA może pojawić się później.

---

## Principle 10 — Build for expansion, not overengineering

Architektura ma pozwalać dodawać kolejne źródła bez przebudowy całego systemu.

Jednocześnie MVP nie może zostać obciążone niepotrzebną złożonością.

---

# 4. ZAKRES INFORMACYJNY

## 4.1. Powietrze

MVP:

* PM2.5
* PM10
* NO2
* SO2
* O3
* CO
* C6H6
* indeks jakości powietrza
* indeksy cząstkowe
* dane ze stacji oficjalnych

MVP+:

* Sensor.Community
* CAMS Air
* dodatkowe modelowe dane jakości powietrza

Future:

* pyły transportowane,
* dust/smoke,
* AOD,
* emisje,
* dodatkowe składniki CAMS.

---

# 5. POGODA

MVP:

* temperatura,
* temperatura odczuwalna,
* wilgotność,
* punkt rosy,
* ciśnienie,
* zachmurzenie,
* opady,
* deszcz,
* śnieg,
* wiatr,
* porywy,
* kierunek wiatru,
* widoczność,
* UV,
* kod warunków pogodowych,
* prognoza.

Future:

* solar radiation,
* CAPE,
* freezing level,
* soil moisture,
* soil temperature,
* VPD,
* wet bulb,
* lightning potential,
* dodatkowe parametry modelowe.

---

# 6. PYLENIE

MVP:

* olcha,
* brzoza,
* trawy,
* bylica,
* ambrozja.

Dodatkowe gatunki mogą zostać dodane, jeżeli:

* dane są dostępne,
* źródło jest zatwierdzone,
* mają znaczenie dla użytkowników w Polsce.

---

# 7. WODA

MVP:

* status kąpieliska,
* przydatność do kąpieli,
* E. coli,
* enterokoki,
* sinice,
* zamknięcie,
* powód zamknięcia,
* data ostatniego badania,
* data kolejnego badania,
* sezon kąpielowy,
* lokalizacja kąpieliska.

Future:

* dodatkowe dane jakości wód powierzchniowych,
* inne parametry biologiczne i chemiczne.

---

# 8. HYDROLOGIA

MVP:

* poziom rzek,
* stan ostrzegawczy,
* stan alarmowy,
* ostrzeżenia hydrologiczne.

Future:

* dodatkowe dane hydrologiczne,
* rozszerzone dane rzeczne,
* dane modelowe.

---

# 9. ALERTY I ZDARZENIA

MVP:

* ostrzeżenia meteorologiczne,
* ostrzeżenia hydrologiczne,
* zamknięcia kąpielisk,
* istotne lokalne zagrożenia,
* zweryfikowane zdarzenia środowiskowe.

Future:

* pożary,
* zagrożenie pożarowe,
* osuwiska,
* promieniowanie,
* sejsmologia,
* incydenty przemysłowe,
* inne źródła bezpieczeństwa.

---

# 10. MVP — DEFINICJA

## Mobile

MVP zawiera:

* Home / Dashboard,
* Alerts,
* Settings,
* foreground location,
* ręczny wybór lokalizacji,
* push notifications,
* profile użytkownika,
* podstawowe preferencje,
* source transparency,
* freshness,
* loading states,
* error states,
* stale states,
* no-data states.

## Backend

MVP zawiera:

* FastAPI,
* PostgreSQL,
* PostGIS,
* Redis,
* connector framework,
* scheduler,
* workers,
* normalization,
* validation,
* freshness,
* geo matching,
* alert engine,
* notification engine,
* REST API,
* logging,
* monitoring,
* backup.

---

# 11. POZA MVP

Nie implementujemy w pierwszym release:

* mapy,
* universal Green Index,
* background location,
* obowiązkowego konta,
* PWA,
* rozbudowanego social/community,
* zaawansowanej monetyzacji,
* pełnej historii danych,
* rozbudowanych funkcji premium.

Architektura może być przygotowana pod przyszłe rozszerzenia.

---

# 12. ARCHITEKTURA SYSTEMU

```text
DATA SOURCES
GIOŚ / IMGW / CAMS / Open-Meteo / Sanepid / Hydrology / etc.
        ↓
CONNECTORS
        ↓
RAW INGESTION
        ↓
PARSE / NORMALIZE
        ↓
VALIDATE
        ↓
GEO PROCESSING
        ↓
PostgreSQL + PostGIS
        ↕
      Redis
        ↓
ALERT ENGINE
        ↓
NOTIFICATION DECISION
        ↓
PUSH ENGINE
        ↓
FastAPI REST API
        ↓ HTTPS
React Native + Expo
```

---

# 13. ARCHITECTURAL STYLE

MVP wykorzystuje:

> **modular monolith + workers**

Nie budujemy mikroserwisów.

Backend ma mieć wyraźnie rozdzielone moduły logiczne.

Mikroserwisy mogą być rozważone dopiero, jeśli rzeczywiste obciążenie lub wymagania produktu będą tego wymagały.

---

# 14. SYSTEM BOUNDARIES

Główne bounded contexts:

1. Source Management
2. Data Ingestion
3. Normalization
4. Validation
5. Geo Engine
6. Measurements
7. Forecasts
8. Events
9. Alerts
10. Notifications
11. User Location
12. User Preferences
13. Mobile API
14. Observability
15. Release / Store

---

# 15. STACK

## Mobile

* React Native
* Expo
* TypeScript
* Expo Router
* NativeWind
* expo-location
* expo-notifications
* EAS Build
* EAS Submit

## Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* REST API
* workers/scheduler

## Database

* PostgreSQL
* PostGIS

## Cache / State

* Redis

## Infrastructure

* Ubuntu 24.04 LTS
* Docker Engine
* Docker Compose
* Caddy
* HTTPS
* VPS

## Development

* GitHub
* GitHub Actions
* Claude Code
* EAS

## Observability

* Sentry
* structured logging
* minimal analytics
* source health monitoring

---

# 16. REPOSITORY STRUCTURE

```text
za-oknem/
├── CLAUDE.md
├── README.md
├── docker-compose.yml
│
├── apps/
│   ├── mobile/
│   └── api/
│
├── packages/
│   ├── api-contract/
│   └── config/
│
├── infrastructure/
│   ├── docker/
│   ├── caddy/
│   └── scripts/
│
├── docs/
│   ├── architecture/
│   │   └── ADR-xxx.md
│   ├── api/
│   ├── data/
│   │   ├── data-dictionary.md
│   │   └── source-registry.md
│   ├── privacy/
│   ├── release/
│   └── tasks/
│
└── .github/
    └── workflows/
```

---

# 17. API CONTRACT

Backend jest źródłem OpenAPI.

Flow:

```text
FastAPI
   ↓
Pydantic
   ↓
OpenAPI
   ↓
generated TypeScript types/client
   ↓
React Native
```

Nie współdzielimy bezpośrednio modeli Pythona z aplikacją mobilną.

---

# 18. CLAUDE CODE GOVERNANCE

W root projektu musi znajdować się:

```text
CLAUDE.md
```

Dokument definiuje:

* produkt,
* architekturę,
* stack,
* strukturę repozytorium,
* zasady danych,
* security,
* testing,
* Git,
* dependencies,
* connector rules,
* privacy,
* release rules.

Claude Code:

* czyta CLAUDE.md przed rozpoczęciem pracy,
* nie dodaje dependency bez uzasadnienia,
* nie zmienia architektury bez ADR,
* nie przechowuje sekretów w repo,
* nie omija testów,
* nie używa LLM jako źródła danych bezpieczeństwa,
* nie tworzy connectorów poza standardową strukturą,
* nie wykonuje nieuzgodnionego scope creep.

---

# 19. ADR

Decyzje architektoniczne przechowujemy w:

```text
docs/architecture/
```

Format:

```text
ADR-001-title.md
ADR-002-title.md
ADR-003-title.md
```

Każdy ADR:

* Context
* Problem
* Options
* Decision
* Consequences
* Date
* Status

---

# 20. ENVIRONMENTS

System ma trzy środowiska:

```text
development
staging
production
```

Każde ma:

* własną konfigurację,
* własne secrets,
* własną bazę,
* własny Redis,
* własne API.

Nigdy nie testujemy na production DB.

---

# 21. VPS / DOCKER

```text
VPS
└── Ubuntu 24.04 LTS
    └── Docker Engine
        ├── Caddy
        ├── API
        ├── Worker
        ├── PostgreSQL
        └── Redis
```

Docker Engine działa bezpośrednio na Ubuntu.

Nie używamy Docker-in-Docker.

---

# 22. VPS — OGRANICZENIA

Jeden VPS jest akceptowalny dla MVP.

Jednocześnie oznacza:

> single point of failure.

Dlatego:

* backup PostgreSQL musi być poza VPS,
* restore musi być okresowo testowany,
* dane nie mogą istnieć wyłącznie na VPS.

---

# 23. DOMENA

Domena nie jest potrzebna do developmentu.

Przed publicznym release potrzebujemy:

* publicznego HTTPS,
* Privacy Policy URL,
* Support / Contact URL,
* ewentualnie Terms,
* ewentualnie Account Deletion URL, jeśli kiedyś pojawią się konta.

---

# 24. LOCATION

MVP:

> **foreground location only**

Flow:

```text
OPEN APP
   ↓
Explain why location is needed
   ↓
Permission
   ↓
Location
   ↓
Geo Matching
   ↓
Local Context
```

---

# 25. LOCATION FALLBACK

Jeżeli użytkownik odrzuci lokalizację:

```text
LOCATION DENIED
       ↓
MANUAL LOCATION
       ↓
LOCAL CONTEXT
```

Aplikacja musi być użyteczna również bez automatycznego GPS.

---

# 26. GEO MODEL

Rozdzielamy trzy pojęcia:

## 1. User Location

Aktualna lokalizacja użytkownika.

## 2. Administrative Context

Np.:

* województwo,
* powiat,
* gmina,
* TERYT,
* miejscowość.

## 3. Data Geography

Geografia konkretnego źródła.

Może być:

* punkt,
* stacja,
* polygon,
* radius,
* administrative area,
* river segment,
* bathing site,
* forecast grid.

---

# 27. GEO ENGINE

Geo Engine odpowiada za deterministyczne dopasowanie danych.

Przykłady:

### Air station

```text
USER LOCATION
      ↓
NEAREST VALID STATION
      ↓
DISTANCE
      ↓
AIR DATA
```

### Weather

```text
USER LOCATION
      ↓
FORECAST GRID / MODEL
      ↓
LOCAL FORECAST
```

### Warning

```text
USER LOCATION
      ↓
POINT-IN-POLYGON
      ↓
WARNING AREA
```

### Bathing site

```text
USER LOCATION
      ↓
NEAREST RELEVANT SITE
      ↓
WATER STATUS
```

Reguły muszą być jawne i testowalne.

---

# 28. DATA MODEL

Nie tworzymy jednej gigantycznej tabeli `measurements`.

Logiczne encje:

```text
sources
source_connectors
source_fetches
stations
geo_areas
locations
measurements
forecasts
events
alerts
devices
notification_preferences
```

---

# 29. MEASUREMENT

Measurement powinien posiadać co najmniej:

```text
id
metric_code
category
value
unit
data_type
source_id
source_record_id
observed_at
latitude
longitude
geo_area_id
freshness_status
validation_status
created_at
updated_at
```

---

# 30. FORECAST

Forecast dodatkowo:

```text
forecast_reference_time
valid_from
valid_until
model
source
```

Measurement i Forecast nie mogą być mylone.

---

# 31. EVENT

Event:

```text
id
event_type
title
description
severity
source
source_url
affected_area
valid_from
valid_until
source_timestamp
validation_status
fingerprint
created_at
updated_at
```

`confidence` stosujemy tylko wtedy, gdy ma rzeczywiste znaczenie — np. przy ekstrakcji lub danych pochodnych.

---

# 32. ALERT

Alert jest reprezentacją zdarzenia istotnego dla użytkownika.

Alert:

> **nie jest tym samym co notification.**

Alert może istnieć bez wysłania push.

---

# 33. RAW INGESTION / PROVENANCE

Każde źródło przechodzi przez:

```text
SOURCE
   ↓
RAW FETCH
   ↓
RAW PAYLOAD
   ↓
PARSER
   ↓
NORMALIZED DATA
   ↓
VALIDATION
```

Raw payload powinien być przechowywany przez ograniczony czas, np.:

> 7–30 dni

w zależności od charakteru źródła, kosztu i potrzeb audytowych.

Celem jest możliwość odpowiedzi na pytanie:

> **„Co dokładnie zwróciło źródło w momencie, gdy zapisaliśmy tę wartość?”**

---

# 34. SOURCE PROVENANCE

Każdy rekord powinien pozwalać ustalić:

* źródło,
* endpoint,
* timestamp pobrania,
* timestamp danych źródłowych,
* source record ID,
* parser,
* wersję normalizacji,
* status walidacji.

---

# 35. CONNECTOR CONTRACT

Każde źródło jest osobnym connector module.

Przykład:

```text
connectors/
├── gios/
├── imgw/
├── open_meteo/
├── cams/
├── sanepid/
├── hydrology/
└── sensor_community/
```

Logiczny kontrakt:

```python
class DataConnector:
    source_code: str

    async def fetch(self):
        ...

    def parse(self, payload):
        ...

    def validate(self, records):
        ...

    def normalize(self, records):
        ...
```

**Uwaga (ADR-001):** connectory `open_meteo` i `cams` nie są wołane per żądanie
użytkownika. Scheduler pobiera dla nich dane jako snapshot per gmina (nie per punkt
GPS użytkownika), zapisuje do bazy, a mobile API czyta wyłącznie z bazy. `cams` ma
inny kształt fetch/parse niż connectory "zapytanie per stacja/punkt" — pobiera wycinek
NetCDF/GRIB dla Polski raz dziennie z Copernicus ADS, nie przez Open-Meteo.

---

# 36. CONNECTOR REQUIREMENTS

Każdy connector musi posiadać:

* timeout,
* retry,
* logging,
* validation,
* normalization,
* source metadata,
* timestamps,
* geographic data,
* error handling,
* testy.

Connector nie może wpływać negatywnie na działanie pozostałych connectorów.

---

# 37. SOURCE REGISTRY

Każde źródło posiada:

```text
source_code
owner
connector
endpoint
frequency
coverage
license
commercial_use
redistribution
caching
rate_limit
attribution
status
last_verified_at
```

Status:

```text
DISCOVERY
↓
VERIFIED
↓
APPROVED
↓
IMPLEMENTED
↓
PRODUCTION
```

Alternatywnie:

```text
BLOCKED
```

---

# 38. SOURCE APPROVAL GATE

Przed użyciem produkcyjnym sprawdzamy:

1. API availability
2. stability
3. terms
4. license
5. commercial use
6. redistribution
7. caching
8. rate limits
9. attribution
10. reliability
11. mobile usage
12. dane osobowe, jeśli występują

---

# 39. DATA PIPELINE

Standard:

```text
FETCH
 ↓
PARSE
 ↓
NORMALIZE
 ↓
VALIDATE
 ↓
GEO MATCH
 ↓
STORE
 ↓
CACHE
```

Awaria źródła:

```text
SOURCE ERROR
 ↓
LOG
 ↓
MARK STALE
 ↓
RETRY
 ↓
KEEP OTHER SOURCES WORKING
```

---

# 40. IDEMPOTENCY

Ponowny fetch tego samego rekordu nie może powodować niekontrolowanego tworzenia duplikatów.

Wykorzystujemy:

* source record ID,
* composite key,
* deterministic fingerprint

w zależności od charakterystyki źródła.

---

# 41. RETRY / TIMEOUT

Każdy request do zewnętrznego źródła ma:

* timeout,
* kontrolowany retry,
* maksymalną liczbę prób,
* opcjonalny exponential backoff.

Nie stosujemy nieskończonych retry.

---

# 42. FRESHNESS

Standardowe statusy:

```text
FRESH
RECENT
STALE
UNAVAILABLE
```

Progi zależą od rodzaju danych.

Przykładowo:

```text
Updated 5 min ago
Updated 2 h ago
Updated 18 h ago
No current data
```

Stare dane nie mogą wyglądać jak aktualne.

---

# 43. DATA VALIDATION

Walidujemy:

* typ,
* jednostkę,
* zakres,
* timestamp,
* geometrię,
* kompletność,
* wartości null,
* zgodność schematu.

Brak danych:

> nie oznacza zero.

---

# 44. DATA QUALITY MONITORING

Monitorujemy:

* last attempted fetch,
* last successful fetch,
* duration,
* records fetched,
* records processed,
* validation errors,
* duplicate rate,
* stale rate,
* source availability.

---

# 45. REDIS

Redis jest używany jako:

* cache,
* short-lived state,
* rate limiting,
* wsparcie jobów/queue,
* krótkotrwałe dane operacyjne.

PostgreSQL pozostaje:

> **source of truth**

---

# 46. SCHEDULER / WORKERS

System powinien posiadać jawny mechanizm:

```text
SCHEDULER
    ↓
JOB
    ↓
QUEUE
    ↓
WORKER
    ↓
CONNECTOR
```

Job przechowuje:

* name,
* schedule,
* timeout,
* retry policy,
* last run,
* last success,
* last failure,
* duration,
* records fetched,
* records processed,
* error count.

---

# 47. ALERT ENGINE

Przepływ:

```text
RAW EVENT
 ↓
NORMALIZED EVENT
 ↓
VALIDATION
 ↓
DEDUPLICATION
 ↓
GEO RELEVANCE
 ↓
SEVERITY
 ↓
USER RELEVANCE
 ↓
ALERT
 ↓
NOTIFICATION DECISION
```

---

# 48. ALERT SEVERITY

Standard:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

Severity:

* pochodzi ze źródła, jeśli źródło ją definiuje,
* albo jest obliczana deterministycznie.

Nie jest generowana arbitralnie przez LLM.

---

# 49. ALERT DEDUPLICATION

Każde zdarzenie powinno mieć fingerprint umożliwiający rozpoznanie:

* tego samego alertu,
* aktualizacji,
* zakończenia,
* zmiany severity,
* zmiany obszaru.

---

# 50. NOTIFICATION ENGINE

Notification Engine decyduje:

> czy użytkownik powinien dostać powiadomienie?

Uwzględnia:

* preferences,
* category,
* severity,
* geo relevance,
* cooldown,
* deduplication,
* quiet hours,
* notification history.

**Uwaga (ADR-002):** "geo relevance" jest liczona względem `observed_area_code`
(TERYT) przypisanego do urządzenia, nie względem punktu GPS — patrz §66.

---

# 51. PUSH ANTI-SPAM

System musi posiadać:

* cooldown,
* per-user rate limit,
* event fingerprint,
* deduplication,
* agregację,
* priorytety,
* quiet hours.

---

# 52. OUTDOOR INTERPRETATION ENGINE

Interpretacja typu:

> „Dobre warunki do biegania”

jest wartością DERIVED.

Przykład:

```text
temperature
+
precipitation
+
wind
+
air quality
+
UV
      ↓
DETERMINISTIC RULES
      ↓
GOOD / MODERATE / POOR
      ↓
REASONS[]
```

Nie używamy LLM do generowania samej klasyfikacji.

---

# 53. LLM POLICY

LLM może być używany do:

* ekstrakcji danych z nieustrukturyzowanych źródeł,
* klasyfikacji tekstu,
* normalizacji komunikatów,
* pomocniczego przetwarzania.

Pipeline:

```text
SOURCE
 ↓
LLM EXTRACTION
 ↓
STRUCTURED EVENT
 ↓
VALIDATION
 ↓
CONFIDENCE
 ↓
PRESENTATION
```

Oryginalne źródło, timestamp, obszar i URL muszą zostać zachowane.

LLM nie jest source of truth dla safety-critical data.

---

# 54. API

Wszystkie endpointy używają wersjonowania:

```text
/api/v1/
```

Przykłady:

```text
GET /api/v1/health
GET /api/v1/dashboard
GET /api/v1/location
GET /api/v1/air
GET /api/v1/weather
GET /api/v1/pollen
GET /api/v1/water
GET /api/v1/hydrology
GET /api/v1/alerts
GET /api/v1/alerts/{id}
POST /api/v1/devices
POST /api/v1/push-tokens
GET /api/v1/settings
```

---

# 55. DASHBOARD API

Podstawowym endpointem jest:

```text
GET /api/v1/dashboard
```

Ma zwracać zagregowany lokalny kontekst:

```text
location
alerts
air
weather
pollen
outdoor
water
```

Pozostałe endpointy szczegółowe mogą istnieć równolegle.

Celem jest ograniczenie liczby niezależnych requestów wykonywanych przez mobile.

**Uwaga (ADR-001):** `weather` i `pollen` w tej odpowiedzi są zawsze czytane z lokalnego
snapshotu w PostgreSQL (per gmina), nigdy nie są wynikiem zapytania do Open-Meteo/CAMS
wykonanego na żądanie tego konkretnego requestu.

---

# 56. MOBILE UX

Dashboard ma odpowiedzieć na pytanie:

> **„Co dzieje się wokół mnie?”**

w około:

> **5–10 sekund**

Priorytet:

1. aktywne ważne alerty,
2. powietrze,
3. pogoda,
4. pollen,
5. outdoor,
6. dodatkowe lokalne informacje.

---

# 57. NAVIGATION

MVP:

```text
Home
Alerts
Settings
```

Bottom navigation.

Mapa:

> poza MVP.

---

# 58. DASHBOARD COMPONENTS

Komponenty:

```text
Header
LocationSelector
SectionHeader
Card
Metric
Status
StatusBadge
AlertCard
AlertSeverity
SourceBadge
DataFreshness
WeatherCard
AirCard
PollenCard
OutdoorCard
EmptyState
ErrorState
Skeleton
BottomNavigation
Toggle
SettingRow
SettingSection
```

Nie stosujemy historycznych prefixów typu:

```text
GPHeader
GPCard
GPWeatherCard
```

Kod powinien być zgodny z nazwą produktu:

> Za Oknem

albo używać neutralnych nazw komponentów.

---

# 59. UI STATES

Każdy moduł powinien obsługiwać:

* loading,
* loaded,
* stale,
* unavailable,
* empty,
* error.

---

# 60. SETTINGS

Settings obejmuje:

* location,
* profile,
* allergies,
* outdoor preferences,
* notifications,
* data & privacy,
* sources,
* about.

---

# 61. PROFILE LOGIC

Profile wpływa na:

* kolejność informacji,
* istotność,
* preferencje,
* notification settings.

Profile nie może zmieniać faktów źródłowych.

---

# 62. ACCOUNT STRATEGY

MVP:

> **brak obowiązkowego konta.**

Preferencje mogą być przechowywane lokalnie / device-based.

---

# 63. KIEDY WPROWADZAMY KONTO

Dopiero gdy pojawi się rzeczywista potrzeba:

* synchronizacji,
* saved locations,
* premium,
* historii,
* cloud preferences,
* multi-device.

Jeżeli konta zostaną dodane, od początku należy zaprojektować:

> account deletion.

---

# 64. SECURITY BASELINE

Minimum:

* HTTPS,
* secrets poza repo,
* environment variables,
* input validation,
* rate limiting,
* payload limits,
* request timeouts,
* CORS,
* security headers,
* firewall,
* osobne credentials,
* backup,
* monitoring,
* dependency updates,
* Docker security.

---

# 65. AUTHENTICATION

MVP nie wymaga pełnego systemu JWT/account authentication.

Public read endpoints mogą być dostępne bez konta.

Operacyjne endpointy, np. device registration, muszą mieć:

* validation,
* rate limiting,
* abuse protection.

---

# 66. DEVICE REGISTRATION

Device może przechowywać:

```text
device_id
platform
push_token
observed_area_code
app_version
created_at
last_seen
notification_status
```

**Uwaga (ADR-002):** `observed_area_code` to kod TERYT gminy/powiatu, nie surowe
współrzędne GPS. Aktualizowany tylko przy otwarciu aplikacji z foreground location lub
przy ręcznej zmianie lokalizacji w Settings — nigdy w tle. Jeśli endpoint w ogóle
przyjmuje współrzędne (do wyznaczenia TERYT po stronie backendu), nie są one trwale
zapisywane w tej tabeli ani logowane w pełnej precyzji w standardowych logach.

Endpoint rejestracji musi mieć:

* validation,
* rate limiting,
* abuse protection.

---

# 67. DATABASE MIGRATIONS

Każda zmiana schematu:

```text
MODEL
 ↓
ALEMBIC MIGRATION
 ↓
LOCAL
 ↓
STAGING
 ↓
PRODUCTION
```

Nigdy:

> manual production schema changes.

---

# 68. BACKUPS

Backup obejmuje:

* PostgreSQL,
* konfigurację,
* kluczowe dane.

Backup musi być przechowywany poza VPS.

Początkowa polityka:

* daily backup,
* retention zależny od kosztu i potrzeb,
* regularny restore test.

Sam backup bez testu odtworzenia:

> nie jest wystarczający.

---

# 69. OBSERVABILITY

Sentry:

* crashes,
* mobile exceptions,
* API errors.

Backend:

* connector errors,
* API errors,
* DB errors,
* push errors,
* source health.

Metrics:

* API latency,
* error rate,
* connector success,
* stale data,
* push delivery.

---

# 70. ANALYTICS

Minimalne eventy:

```text
app_open
location_selected
dashboard_view
alert_open
notification_open
settings_open
```

Nie zbieramy więcej danych niż potrzebujemy.

---

# 71. PRIVACY / RODO

Przed release wykonujemy:

```text
DATA INVENTORY
 ↓
PURPOSE
 ↓
LEGAL BASIS
 ↓
RETENTION
 ↓
PROCESSORS / PROVIDERS
 ↓
USER RIGHTS
 ↓
PRIVACY POLICY
```

Uwzględniamy:

* location,
* push token,
* device identifiers,
* diagnostics,
* analytics,
* logs,
* Sentry,
* ewentualne account data.

---

# 72. SDK INVENTORY

Tworzymy:

```text
docs/privacy/sdk-inventory.md
```

Dla każdego SDK:

* nazwa,
* dane,
* cel,
* Android,
* iOS,
* processor/provider,
* transfer,
* retention.

Nie zostawiamy wartości TBD przed release.

---

# 73. APPLE PRIVACY

Privacy Policy URL musi odpowiadać rzeczywistemu produktowi.

App Privacy musi odpowiadać:

* kodowi,
* SDK,
* backendowi,
* analytics,
* Sentry,
* location,
* push.

Location:

* tylko gdy potrzebna,
* minimalny zakres,
* brak background location w MVP.

Po odmowie lokalizacji:

> manual location.

---

# 74. GOOGLE PLAY DATA SAFETY

Data Safety musi odpowiadać rzeczywistemu zachowaniu:

* aplikacji,
* backendu,
* SDK,
* analytics,
* crash reporting.

Nie deklarujemy niczego „na oko”.

---

# 75. TESTING STRATEGY

## Backend

* unit tests,
* integration tests,
* connector tests,
* API tests,
* validation tests,
* geo tests,
* alert tests,
* notification tests.

## Mobile

* navigation,
* location,
* dashboard,
* alerts,
* settings,
* push,
* lifecycle,
* error states.

## Data

Testujemy:

* malformed response,
* missing values,
* stale data,
* duplicate records,
* wrong coordinates,
* invalid timestamp,
* unavailable source,
* partial failure.

---

# 76. END-TO-END TEST

Najważniejszy test systemowy:

```text
SOURCE
 ↓
CONNECTOR
 ↓
DATABASE
 ↓
API
 ↓
MOBILE
 ↓
USER
```

---

# 77. LOCATION TEST MATRIX

Testujemy:

* permission granted,
* permission denied,
* approximate location,
* precise location,
* manual location,
* location unavailable,
* poor accuracy,
* changed location.

---

# 78. PUSH TEST MATRIX

Testujemy:

* permission,
* token registration,
* delivery,
* deep link,
* preferences,
* duplicate event,
* expired event,
* quiet hours,
* foreground,
* background,
* killed app.

---

# 79. NETWORK TEST MATRIX

Testujemy:

* WiFi,
* mobile,
* offline,
* slow connection,
* API timeout,
* source timeout,
* partial backend failure.

---

# 80. ERROR HANDLING

### Loading

Skeleton.

### No data

Clear no-data state.

### Source unavailable

Unavailable state.

### Stale

Timestamp + stale indicator.

### Location denied

Manual location.

### Backend unavailable

Clear error.

Najważniejsza zasada:

> pojedynczy connector nie może crashować aplikacji.

---

# 81. CLAUDE CODE WORKFLOW

Claude Code nie dostaje polecenia:

> „Zbuduj całą aplikację.”

Workflow:

```text
PROJECT SPEC
 ↓
ARCHITECTURE
 ↓
PHASE
 ↓
TASK
 ↓
IMPLEMENT
 ↓
TEST
 ↓
REVIEW
 ↓
COMMIT
 ↓
NEXT TASK
```

---

# 82. TASK TEMPLATE

Każdy task musi zawierać:

## Goal

Co budujemy?

## Scope

Co obejmuje zadanie?

## Acceptance Criteria

Po czym poznajemy, że działa?

## Tests

Jak sprawdzamy?

## Non-goals

Czego nie implementujemy?

## Dependencies

Od czego zależy?

## Data Contract

Jakie dane są wejściem/wyjściem?

## Security

Jakie ryzyka bezpieczeństwa występują?

## Architecture Impact

Czy zmieniamy architekturę?

---

# 83. DEFINITION OF READY

Task jest Ready, jeżeli posiada:

* Goal,
* Scope,
* Acceptance Criteria,
* Tests,
* Non-goals,
* Dependencies,
* Data Contract,
* Security Considerations,
* Architecture Impact.

---

# 84. DEFINITION OF DONE

Task jest Done, jeżeli:

* implementacja działa,
* acceptance criteria są spełnione,
* testy przechodzą,
* lint/typecheck przechodzą,
* dokumentacja jest aktualna,
* nie ma scope creep,
* kod jest gotowy do review,
* commit jest logiczny.

---

# 85. GIT STRATEGY

```text
main
```

oznacza:

> production-ready.

Pracujemy na feature branches.

Zmiany trafiają przez PR.

Commit powinien być:

* mały,
* logiczny,
* opisowy.

---

# 86. CI/CD

## CI

Na Pull Request:

* lint,
* typecheck,
* unit tests,
* integration checks,
* build checks.

## CD

```text
main
 ↓
staging
 ↓
manual approval
 ↓
production
```

Na początku production deployment pozostaje kontrolowany ręcznie.

---

# 87. EAS PROFILES

Potrzebujemy:

```text
development
preview
production
```

### development

Codzienna praca.

### preview

Build dla testerów.

### production

Build do sklepów.

---

# 88. GOOGLE PLAY ACCOUNT

Potrzebujemy:

> Google Play Developer Account.

**Decyzja (v1.2):** **Personal**, nie Organization.

Powód: na tym etapie aplikacja jest publikowana jako projekt social-impact / osoba
prywatna, bez monetyzacji (patrz ADR-003) — nie jako komercyjny produkt JDG.
Konsekwencja: obowiązuje wymóg zamkniętego testu (§89) — min. 12 testerów przez min. 14
kolejnych dni przed dostępem do produkcji.

**Do sprawdzenia później (nie blokuje developmentu):** jeśli w przyszłości konto
zostanie przeniesione na Organization/JDG, sprawdzić warunki transferu package name i
aplikacji między kontami Play.

---

# 89. GOOGLE PLAY TESTING

Dla nowych personal developer accounts utworzonych po 13 listopada 2023 obowiązuje wymaganie zamkniętego testu:

> minimum 12 testerów
> przez minimum 14 kolejnych dni

przed uzyskaniem dostępu do produkcji.

Dlatego decyzję Personal vs Organization należy podjąć przed rozpoczęciem finalnego release process.

---

# 90. GOOGLE PLAY TARGET API

Na dzień:

> **28.09.2026**

nowe aplikacje i aktualizacje przesyłane do Google Play muszą targetować:

> **Android 16 / API 36 lub wyższe.**

Projekt powinien od początku być przygotowany pod target SDK 36+.

---

# 91. GOOGLE PLAY CONFIGURATION

Potrzebujemy:

* package name,
* app name,
* icon,
* splash,
* version,
* versionCode,
* permissions,
* signing,
* notification configuration,
* target SDK.

---

# 92. ANDROID PERMISSIONS

Potencjalnie:

```text
LOCATION
NOTIFICATIONS
INTERNET
```

Nie dodajemy niepotrzebnych permissions.

W szczególności:

> brak background location w MVP.

---

# 93. GOOGLE PLAY LISTING

Potrzebujemy:

* app name,
* default language,
* category,
* short description,
* full description,
* icon,
* screenshots,
* privacy policy,
* Data Safety,
* content rating,
* target audience,
* app access,
* permissions,
* countries,
* pricing.

---

# 94. GOOGLE PLAY BUILD

Produkujemy:

```text
.aab
```

Przykład:

```text
eas build --platform android --profile production
```

---

# 95. GOOGLE PLAY SUBMISSION

Możemy używać:

```text
eas submit --platform android
```

Pierwsze wdrożenie wymaga konfiguracji:

* Play Developer Account,
* credentials,
* signing,
* odpowiednich uprawnień.

---

# 96. APPLE DEVELOPER

Potrzebujemy:

* Apple Developer Program,
* Team,
* Bundle ID,
* signing,
* App Store Connect.

---

# 97. APP STORE CONNECT

Potrzebujemy:

* name,
* subtitle,
* description,
* keywords,
* category,
* screenshots,
* privacy policy,
* App Privacy,
* age rating,
* support URL,
* review information.

---

# 98. TESTFLIGHT

Proces:

```text
Code
 ↓
EAS Build
 ↓
App Store Connect
 ↓
TestFlight
 ↓
QA
 ↓
App Review
 ↓
App Store
```

---

# 99. APP REVIEW NOTES

Reviewer powinien otrzymać informacje dotyczące:

* uruchomienia,
* location flow,
* braku obowiązkowego konta,
* alertów,
* ograniczeń,
* danych testowych,
* ewentualnych specjalnych kroków.

---

# 100. STORE ASSETS

Przygotowujemy screenshots:

* dashboard,
* air,
* weather,
* pollen,
* alerts,
* settings.

Screenshots muszą przedstawiać rzeczywiste funkcje.

Nie pokazujemy funkcji, których aplikacja nie posiada.

---

# 101. PRIVACY POLICY

Privacy Policy musi opisywać:

* administratora danych,
* dane zbierane przez aplikację,
* location,
* push token,
* analytics,
* diagnostics,
* Sentry,
* dane techniczne,
* zewnętrznych dostawców,
* źródła danych,
* podstawę przetwarzania,
* retencję,
* prawa użytkownika,
* usuwanie danych,
* kontakt.

Dokument musi odpowiadać rzeczywistemu produktowi.

---

# 102. PUBLIC WEBSITE

Minimalny zakres:

```text
/
 /privacy
 /terms
 /support
 /contact
 /about
```

Nie potrzebujemy pełnego serwisu marketingowego przed MVP.

---

# 103. RELEASE CANDIDATE

Przed release:

```text
[ ] Backend production
[ ] PostgreSQL
[ ] Redis
[ ] HTTPS
[ ] External backup
[ ] Restore test
[ ] Monitoring
[ ] Sentry
[ ] Analytics
[ ] Location
[ ] Manual location
[ ] Push
[ ] Dashboard
[ ] Alerts
[ ] Settings
[ ] Profiles
[ ] Data connectors
[ ] Geo matching
[ ] Freshness
[ ] Error states
[ ] Loading states
[ ] Stale states
[ ] Privacy Policy
[ ] Data Safety
[ ] App Privacy
[ ] Store listing
[ ] App icon
[ ] Screenshots
[ ] Android build
[ ] iOS build
[ ] Google testing
[ ] TestFlight
[ ] App Review notes
```

---

# 104. RELEASE ROLLBACK

Musimy móc:

* wyłączyć connector,
* wyłączyć kategorię alertów,
* zmienić konfigurację,
* rollbackować backend,
* ograniczyć źródło powodujące problemy.

Nie powinno być konieczności przebudowy całej aplikacji w przypadku awarii jednego źródła.

---

# 105. POST-RELEASE

Monitorujemy:

* crashes,
* API,
* connector health,
* data freshness,
* push success,
* DAU/WAU,
* retention,
* dashboard usage,
* alert usage,
* source reliability.

---

# 106. SOURCE ROADMAP

## MVP

* GIOŚ,
* IMGW,
* Open-Meteo (pogoda; darmowy, niekomercyjny tier — patrz ADR-003),
* CAMS pollen — bezpośrednio z Copernicus Atmosphere Data Store, nie przez Open-Meteo
  (patrz ADR-001, Source Registry),
* Sanepid/GIS,
* hydrology,
* GUGiK/TERYT/PRG.

## MVP+

* Sensor.Community,
* CAMS Air,
* SYNGEOS,
* additional hydrology,
* additional water,
* additional alerts.

## Future

* noise,
* fires,
* fire danger,
* drought,
* soil,
* lightning,
* CAPE,
* solar radiation,
* AOD,
* dust/smoke,
* traffic,
* accidents,
* radiation,
* seismology,
* industrial incidents,
* surface water quality.

Każde źródło przed produkcją przechodzi Source Approval Gate.

**Uwaga (ADR-003):** status licencyjny Open-Meteo (darmowy = niekomercyjny) musi być
rewidowany PRZED włączeniem reklam, subskrypcji, Patronite lub innej formy stałego
wsparcia finansowego — nie po. Patrz §109.

---

# 107. MASTER DEVELOPMENT ROADMAP

## PHASE 0 — Foundation

* GitHub,
* monorepo,
* mobile,
* backend,
* Docker,
* environments,
* CI,
* CLAUDE.md.

## PHASE 1 — Infrastructure

* VPS,
* Ubuntu,
* Docker,
* Caddy,
* HTTPS,
* PostgreSQL,
* PostGIS,
* Redis,
* backup,
* monitoring.

## PHASE 2 — Backend Core

* FastAPI,
* models,
* Alembic,
* API structure,
* common data model,
* logging,
* error handling.

## PHASE 3 — Data Architecture

* Source Registry,
* raw ingestion,
* provenance,
* connector contract,
* validation,
* freshness.

## PHASE 4 — First Vertical Slice

```text
GIOŚ
 ↓
Connector
 ↓
Database
 ↓
API
 ↓
Mobile
 ↓
PM2.5
```

To jest najważniejszy pierwszy end-to-end proof.

## PHASE 5 — Weather

* Open-Meteo (ADR-001: snapshot per gmina w bazie, ADR-003: licencja niekomercyjna),
* CAMS pollen/Air z Copernicus ADS jako osobny connector,
* forecast,
* current conditions.

## PHASE 6 — Geo Engine

* location,
* TERYT,
* station matching,
* geographic relevance.

## PHASE 7 — Dashboard

* Home,
* Air,
* Weather,
* source,
* freshness,
* states.

## PHASE 8 — Pollen

* pollen connector,
* pollen card,
* allergy profile.

## PHASE 9 — Alerts

* event model,
* alert engine,
* severity,
* deduplication,
* geo relevance.

## PHASE 10 — Push

* device registration,
* push tokens,
* notification preferences,
* Expo notifications,
* FCM,
* APNs,
* deep links,
* anti-spam.

## PHASE 11 — Water / Hydrology

* Sanepid/GIS,
* hydrology,
* bathing status.

## PHASE 12 — Settings / Profiles

* settings,
* allergy,
* family,
* outdoor.

## PHASE 13 — Data Quality / Observability

* source health,
* stale monitoring,
* Sentry,
* analytics.

## PHASE 14 — Security / Privacy

* security review,
* RODO,
* SDK inventory,
* Privacy Policy,
* Data Safety,
* App Privacy.

## PHASE 15 — Production Infrastructure

* staging,
* production,
* backup,
* restore,
* monitoring.

## PHASE 16 — Store Preparation

* Google Play,
* Apple,
* EAS,
* metadata,
* screenshots.

## PHASE 17 — Testing

* QA,
* E2E,
* location,
* push,
* network,
* resilience.

## PHASE 18 — Public Release

* Google Play,
* App Store.

## PHASE 19 — Operations

* monitoring,
* connector maintenance,
* incident response,
* product analytics.

---

# 108. VERTICAL SLICE PRIORITY

Najważniejszy cel techniczny na początku:

> **udowodnić pełny przepływ rzeczywistych danych.**

Nie budujemy najpierw całego UI.

Nie budujemy najpierw wszystkich connectorów.

Nie budujemy najpierw mapy.

Budujemy:

```text
GIOŚ
 ↓
Connector
 ↓
Normalize
 ↓
Validate
 ↓
PostgreSQL
 ↓
FastAPI
 ↓
React Native
 ↓
PM2.5
```

Jeżeli ten przepływ działa, dokładanie kolejnych źródeł jest znacznie bezpieczniejsze.

---

# 109. MONETYZACJA

Architektura może później obsłużyć:

* premium,
* dodatkowe alerty,
* advanced data,
* saved locations,
* historię,
* advanced analytics.

Jednak:

> **monetyzacja nie może blokować MVP.**

**Uwaga (ADR-003):** odwrotny kierunek też obowiązuje — **monetyzacja nie może zostać
włączona bez rewizji ADR-003**. Reklamy, subskrypcje, Patronite lub inna forma stałego
wsparcia finansowego wymagają wcześniej albo pisemnego potwierdzenia od Open-Meteo, że
dany model mieści się w "non-commercial use", albo przejścia na płatny plan API, albo
zmiany dostawcy pogody na taki z licencją jawnie dopuszczającą użycie komercyjne.

---

# 110. PWA

PWA:

> poza MVP.

Może być późniejszym web companionem.

Potencjalne zastosowania:

* SEO,
* publiczne informacje,
* landing page,
* publiczne dashboardy,
* web access.

---

# 111. MAPA

Mapa:

> poza MVP.

Najpierw budujemy dobry dashboard lokalny.

Mapa może zostać dodana później bez zmiany podstawowego modelu danych.

---

# 112. GREEN INDEX

Universal Green Index:

> poza MVP.

Jeżeli kiedyś powstanie:

* metodologia musi być transparentna,
* składowe muszą być widoczne,
* użytkownik powinien wiedzieć, skąd bierze się wynik,
* nie może być arbitralnym black boxem.

---

# 113. VERSIONING

Używamy:

```text
MAJOR.MINOR.PATCH
```

Przykład:

```text
1.0.0
1.0.1
1.1.0
2.0.0
```

Android dodatkowo:

```text
versionCode
```

Każdy build produkcyjny musi mieć unikalny version code.

---

# 114. CI/CD

Docelowo:

```text
GitHub
 ↓
GitHub Actions
 ↓
Tests
 ↓
Build
 ↓
EAS
 ↓
Preview / Production
```

Na początku:

> production release pozostaje kontrolowany ręcznie.

Automatyzacja submission może zostać dodana później.

---

# 115. PR STRATEGY

Pull Request powinien zawierać:

* summary,
* scope,
* tests,
* architecture impact,
* screenshots, jeśli dotyczy UI,
* migration information,
* risk,
* rollback information.

---

# 116. EXAMPLE CLAUDE CODE TASK

## TASK

Implement GIOŚ connector.

## GOAL

Retrieve official air quality measurements.

## SCOPE

* PM2.5
* PM10
* NO2
* SO2
* O3
* CO
* C6H6
* AQI
* partial indices

## REQUIREMENTS

* isolated connector,
* timeout,
* retry,
* validation,
* logging,
* source metadata,
* timestamp,
* station geo,
* normalization,
* provenance,
* tests.

## NON-GOALS

* UI redesign,
* push notifications,
* pollen,
* weather,
* dashboard redesign.

## ACCEPTANCE CRITERIA

* connector retrieves data,
* malformed data is rejected,
* source failure does not crash API,
* records are normalized,
* duplicates are prevented,
* provenance is preserved,
* tests pass.

---

# 117. STORE RELEASE FLOW — ANDROID

```text
Code
 ↓
GitHub
 ↓
CI
 ↓
EAS Build
 ↓
AAB
 ↓
Google Play Console
 ↓
Internal Testing
 ↓
Closed Testing
 ↓
Production
```

---

# 118. STORE RELEASE FLOW — IOS

```text
Code
 ↓
GitHub
 ↓
CI
 ↓
EAS Build
 ↓
App Store Connect
 ↓
TestFlight
 ↓
QA
 ↓
App Review
 ↓
App Store
```

---

# 119. RELEASE GATES

Public release wymaga przejścia przez:

```text
ARCHITECTURE
 ↓
DATA
 ↓
PRODUCT
 ↓
RELIABILITY
 ↓
SECURITY
 ↓
PRIVACY
 ↓
STORE
 ↓
QA
 ↓
LAUNCH
```

Nie publikujemy, jeśli któryś krytyczny gate nie został spełniony.

---

# 120. FINAL MVP DEFINITION OF DONE

## Product

* Dashboard,
* Alerts,
* Settings,
* location,
* manual location,
* profiles.

## Data

* GIOŚ,
* weather,
* pollen,
* alerts,
* water,
* hydrology,
* geo matching.

## Backend

* API,
* validation,
* freshness,
* cache,
* logging,
* error handling,
* connector isolation.

## Push

* Android,
* iOS,
* preferences,
* deep links,
* deduplication,
* anti-spam.

## Infrastructure

* VPS,
* Docker,
* HTTPS,
* PostgreSQL,
* Redis,
* backup,
* restore test,
* monitoring.

## Security

* secrets,
* HTTPS,
* rate limiting,
* validation,
* protected operational endpoints.

## Stores

* developer accounts,
* EAS,
* builds,
* Privacy Policy,
* Data Safety,
* App Privacy,
* listing,
* screenshots,
* testing.

---

# 121. FINAL PROJECT STRUCTURE

```text
ZA OKNEM
│
├── PRODUCT
│   ├── Vision
│   ├── UX
│   ├── Profiles
│   └── Notifications
│
├── MOBILE
│   ├── React Native
│   ├── Expo
│   ├── TypeScript
│   └── NativeWind
│
├── BACKEND
│   ├── FastAPI
│   ├── Workers
│   ├── API
│   └── Alert Engine
│
├── DATA HUB
│   ├── GIOŚ
│   ├── IMGW
│   ├── CAMS
│   ├── Open-Meteo
│   ├── Sanepid
│   ├── Hydrology
│   └── Future Connectors
│
├── DATABASE
│   ├── PostgreSQL
│   └── PostGIS
│
├── CACHE
│   └── Redis
│
├── INFRA
│   ├── Ubuntu
│   ├── Docker
│   ├── Caddy
│   └── VPS
│
├── OBSERVABILITY
│   ├── Sentry
│   └── Analytics
│
├── PUSH
│   ├── Expo
│   ├── FCM
│   └── APNs
│
├── STORE
│   ├── Google Play
│   ├── App Store
│   ├── TestFlight
│   └── EAS
│
└── LEGAL
    ├── Privacy Policy
    ├── Terms
    ├── Data Sources
    └── Support
```

---

# 122. MASTER ROADMAP — SHORT VERSION

```text
0 Foundation
↓
1 Skeleton
↓
2 Infrastructure
↓
3 Data Model
↓
4 GIOŚ Vertical Slice
↓
5 Weather
↓
6 Geo Engine
↓
7 Dashboard
↓
8 Pollen
↓
9 Alerts
↓
10 Push
↓
11 Water / Hydrology
↓
12 Profiles
↓
13 Observability
↓
14 Security / Privacy
↓
15 Production
↓
16 Stores
↓
17 Testing
↓
18 Release
↓
19 Operations
```

---

# 123. FINAL ARCHITECTURAL DECISIONS

| Decyzja              | Wartość                                      |
| -------------------- | -------------------------------------------- |
| Produkt              | Za Oknem                                     |
| Platformy            | Android + iOS (Android pierwszy, iOS równolegle od closed testingu Androida) |
| Google Play account  | Personal (v1.2 — patrz §88)                  |
| Weather/pollen read path | Zawsze z DB snapshot, nigdy on-demand (ADR-001) |
| Push geo targeting   | `observed_area_code` (TERYT), nie GPS (ADR-002) |
| Weather provider     | Open-Meteo, darmowy/niekomercyjny tier do rewizji ADR-003 |
| Mobile               | React Native + Expo                          |
| Language             | TypeScript                                   |
| Navigation           | Expo Router                                  |
| Styling              | NativeWind                                   |
| Backend              | Python + FastAPI                             |
| Validation           | Pydantic                                     |
| ORM                  | SQLAlchemy                                   |
| Migrations           | Alembic                                      |
| Database             | PostgreSQL                                   |
| Geo                  | PostGIS                                      |
| Cache                | Redis                                        |
| Infrastructure       | Ubuntu 24.04 + Docker                        |
| Reverse proxy        | Caddy                                        |
| Deployment           | VPS                                          |
| Push                 | Expo Notifications + FCM/APNs                |
| Build                | EAS                                          |
| Location MVP         | Foreground                                   |
| Account MVP          | None required                                |
| Map MVP              | No                                           |
| PWA MVP              | No                                           |
| Green Index MVP      | No                                           |
| LLM                  | Extraction / processing only where justified |
| Source of Truth      | Deterministic / official source data         |
| API                  | `/api/v1/`                                   |
| Environments         | Development / Staging / Production           |
| Architecture changes | ADR required                                 |
| Database changes     | Alembic only                                 |
| Production secrets   | Never in repo                                |
| Backup               | External + restore test                      |
| Architecture style   | Modular monolith + workers                   |

---

# 124. KLUCZOWE ZASADY TECHNICZNE

1. One broken source must not break the product.
2. PostgreSQL = durable source of truth.
3. Redis = cache / short-lived state.
4. No production secrets in repository.
5. No manual production schema changes.
6. Every external request has timeout and controlled retry.
7. Every connector is isolated.
8. Every source has provenance.
9. Measurements, forecasts and alerts are distinct.
10. Stale data is visibly stale.
11. Geo matching is deterministic.
12. Alert and notification are separate.
13. LLM is not a safety source.
14. No unnecessary permissions.
15. No mandatory account in MVP.
16. No background location in MVP.
17. No architecture change without ADR.
18. No task without acceptance criteria.
19. No release without privacy/store consistency review.
20. No launch without restore test.

---

# 125. SENIOR TECH LEAD SIGN-OFF

```text
[ ] Product scope approved
[ ] MVP scope frozen
[ ] Stack approved
[ ] Repository created
[ ] CLAUDE.md created
[ ] ADR directory created
[ ] Data Dictionary available
[ ] Source Registry started
[ ] Environment strategy approved
[ ] Data model approved
[ ] Connector contract approved
[ ] Geo model approved
[ ] Alert model approved
[ ] Notification model approved
[ ] API versioning approved
[ ] Privacy workstream created
[ ] Store workstream created
[ ] Backup strategy approved
[ ] Testing strategy approved
[ ] Definition of Ready approved
[ ] Definition of Done approved
[ ] First vertical slice defined
```

---

# 126. FINAL PRODUCT DEFINITION

> **Za Oknem to prosta, wiarygodna aplikacja mobilna pokazująca użytkownikowi, co aktualnie dzieje się wokół niego.**

Jej przewaga:

```text
MANY SOURCES
      ↓
NORMALIZATION
      ↓
GEO CONTEXT
      ↓
ONE LOCAL CONTEXT
      ↓
ONE SIMPLE APP
```

---

# 127. RELEASE GOAL

Pierwszy publiczny release nie ma udowodnić, że potrafimy zbudować „superapp”.

Ma odpowiedzieć na jedno pytanie:

> **Czy użytkownik rzeczywiście chce mieć jedno miejsce, które regularnie pokazuje mu najważniejsze informacje o jego najbliższym otoczeniu?**

Jeżeli odpowiedź będzie pozytywna, kolejne:

* źródła,
* profile,
* historia,
* mapa,
* premium,
* PWA,
* kolejne platformy

mogą być dodawane bez przebudowy podstawowej architektury.

---

# 128. FINALNA ZASADA PROJEKTU

Nie optymalizujemy na tym etapie pod maksymalną liczbę funkcji.

Optymalizujemy pod:

1. wiarygodne dane,
2. prosty lokalny kontekst,
3. odporność na awarie źródeł,
4. prywatność,
5. bezpieczeństwo,
6. łatwe dodawanie źródeł,
7. szybki feedback od pierwszych użytkowników.

> **Za Oknem v1.0 ma być małym, stabilnym i użytecznym produktem — nie niedokończonym superappem.**

---

# 129. NEXT STEP AFTER THIS DOCUMENT

Po zatwierdzeniu tego dokumentu nie tworzymy kolejnego ogólnego „master planu”.

Przechodzimy do:

```text
CLAUDE.md
        ↓
PHASE 0
        ↓
TASK 0.1
        ↓
Repository Foundation
```

Pierwszym rzeczywistym celem technicznym jest przygotowanie repozytorium i fundamentów projektu, a następnie możliwie szybko dojście do pierwszego vertical slice:

```text
GIOŚ
 ↓
Connector
 ↓
PostgreSQL
 ↓
FastAPI
 ↓
React Native
 ↓
PM2.5
```

To jest punkt, w którym projekt przestaje być wyłącznie dokumentacją i zaczyna być działającym systemem.
