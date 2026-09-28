# ADR-002: Obserwowany obszar do push notifications = TERYT, nie GPS w tle

**Status:** Accepted
**Data:** 2026-09-28

## Context

Master Plan wymaga push notifications w MVP (§10, PHASE 10), ale jednocześnie zakazuje
background location (Principle 8, §92, zasada 11 w CLAUDE.md) i nie definiuje, skąd
backend ma wiedzieć, dla jakiego obszaru wysłać alert do danego urządzenia, gdy
aplikacja jest zamknięta.

## Problem

Jak wysyłać trafne push notifications o alertach lokalnych bez background location i
bez logowania precyzyjnych współrzędnych użytkownika na serwerze?

## Options

**A. Background location.** Odrzucone — wprost zakazane w MVP (Principle 8).

**B. Push tylko gdy aplikacja otwarta (foreground), bez powiadomień "z zewnątrz".**
Nie spełnia realnego oczekiwania produktu (alert o burzy, gdy telefon leży na stole).

**C. Obserwowany obszar = kod TERYT gminy/powiatu, aktualizowany przy otwarciu
aplikacji (wybrana).** Urządzenie, przy foreground location lub ręcznym wyborze
lokalizacji, wysyła do backendu **kod TERYT** (nie surowe współrzędne) jako
"obszar do obserwowania". Backend kojarzy `device_id` z `geo_area_id` (TERYT) i
dopasowuje alerty przez point-in-polygon / przynależność administracyjną (§27).

## Decision

Wybieramy opcję **C**.

- Endpoint `POST /api/v1/devices` (§66) przyjmuje `observed_area_code` (TERYT gminy)
  zamiast lub obok surowych współrzędnych. Współrzędne, jeśli w ogóle są wysyłane do
  API w celu wyznaczenia TERYT, nie są trwale przechowywane w `devices` — zapisywany
  jest wynik dopasowania (`geo_area_id`), nie punkt GPS.
- Aktualizacja `observed_area_code` następuje przy każdym otwarciu aplikacji z
  aktywną lokalizacją (foreground) lub przy ręcznej zmianie lokalizacji w Settings —
  nigdy w tle.
- Alert Engine (§47) dopasowuje zdarzenia do `geo_area_id`, nie do punktu GPS
  urządzenia — spójne z Geo Engine i modelem Warning (§27).
- Logowanie: endpointy przyjmujące współrzędne (np. do wyznaczenia TERYT) nie logują
  pełnych query stringów z lat/lon w standardowych logach aplikacyjnych (Principle 7).
  Backend serwera (Caddy/FastAPI access log) ma wyłączone logowanie query string dla
  tych endpointów lub loguje zaokrąglone wartości.

## Consequences

- To musi zostać opisane w Privacy Policy i Google Play Data Safety jako "przybliżona
  lokalizacja administracyjna", nie "lokalizacja w czasie rzeczywistym".
- Push jest trafny na poziomie gminy/powiatu, nie punktowo — akceptowalne dla alertów
  meteo/hydro, które i tak są wydawane dla obszarów administracyjnych lub zlewni.
- Nie wymaga uprawnienia background location, więc nie zmienia listy uprawnień z §92.
- Wymaga tabeli `geo_areas` z TERYT jako częścią modelu (już przewidziane w §26/§28).
