# ADR-017: Rejestracja urządzeń bez konta — `installation_id` + `device_secret`

**Status:** Accepted
**Data:** 2026-09-30

## Context

ADR-002 ustala, CO urządzenie zgłasza (`observed_area_code` TERYT, nie GPS), ale nie
mówi, JAK backend odróżnia właściciela rekordu `Device` od kogokolwiek innego. Rule #11
zabrania obowiązkowego konta, Master Plan §65-66 wymaga validation + rate limiting +
abuse protection dla `POST /api/v1/devices`, a TASK-10.2 (wysyłka push), 10.3a
(preferencje), 12.5 (aktualizacja obszaru) i 14.2 (retencja/usuwanie) będą operować na
tych rekordach.

## Problem

1. Bez konta każdy, kto zna `installation_id`, mógłby podmienić cudzy token push,
   zmienić obserwowany obszar albo wyrejestrować cudze urządzenie.
2. Jak ograniczyć masowe tworzenie rekordów/tokenów bez infrastruktury, której repo
   jeszcze nie ma (Redis wchodzi dopiero w TASK-15.4)?
3. Co wolno zapisać i zalogować (dane pseudonimowe, nie anonimowe — RODO)?

## Options

- **Uwierzytelnianie:** (a) sam `installation_id` jako „hasło” (przejęcie po wycieku
  identyfikatora, który pojawia się w ścieżkach/logach); (b) JWT/konto (łamie rule #11);
  (c) **`installation_id` = identyfikator, osobny losowy `device_secret` = dowód
  posiadania, generowany przez serwer i pokazany raz**.
- **Hash sekretu:** (a) bcrypt/argon2 (nowa zależność, zbędna — sekret ma 256 bitów
  entropii, nie da się go zgadywać słownikowo); (b) **SHA-256 + `hmac.compare_digest`**.
- **Rate limit:** (a) nic do TASK-14.2/15.4 (BACKLOG 10.1 wprost tego zabrania);
  (b) Redis (decyzja TASK-15.4); (c) **prosty limiter in-memory per IP w procesie API**
  (ten sam kierunek co BACKLOG TASK-6.2/14.2).

## Decision

1. **Tożsamość.** Klient generuje losowy `installation_id` (`[A-Za-z0-9_-]{32,64}`,
   np. UUIDv4, ≥128 bitów — nie do wyliczenia/enumeracji) i trzyma go oraz sekret w
   secure storage. `installation_id` NIE jest sekretem.
2. **Sekret.** Przy pierwszej rejestracji serwer generuje `secrets.token_urlsafe(32)`,
   zwraca go **jeden raz** (201, `Cache-Control: no-store`), w bazie trzyma wyłącznie
   SHA-256 (hex). Każda późniejsza operacja na istniejącym rekordzie wymaga nagłówka
   `X-Device-Secret` (nagłówek, nie query/path/body — nie trafia do logów URL);
   porównanie stałoczasowe.
3. **API.** `POST /api/v1/devices` = idempotentny upsert po `installation_id`
   (rejestracja, odświeżenie tokenu, zmiana `observed_area_code` — 12.5): nowy → 201 +
   sekret, istniejący → 200 (wymaga sekretu, inaczej 403; zmieniane są tylko pola
   obecne w body, `push_token: null` czyści token). `DELETE /api/v1/devices/{installation_id}`
   = dezaktywacja (`active=false`, token i obszar zerowane, wiersz zostaje, idempotentne);
   nieznany id i zły sekret dają identyczne 404. Brak `GET` (nic do czytania przez klienta).
4. **Ujawnianie istnienia.** `POST` na istniejący id bez poprawnego sekretu zwraca 403,
   więc teoretycznie ujawnia istnienie id — akceptowane: entropia ≥128 bitów czyni
   enumerację niewykonalną, a limiter dławi próby. `DELETE`/nieznany = zawsze 404.
5. **Jeden token = jedna instalacja** (unikalny indeks). Token już przypisany do innej
   instalacji (reinstalacja = nowy `installation_id`) jest jej odbierany, żeby nie
   wysłać push dwa razy. Do przejęcia cudzego tokenu trzeba go znać (nie jest
   wyliczalny), a ofiara i tak odzyska go przy następnym starcie appki.
6. **Walidacja.** `ExponentPushToken[...]`/`ExpoPushToken[...]` (format; ważność
   sprawdza dopiero wysyłka, TASK-10.2), `platform` ∈ {android, ios},
   `observed_area_code` = 4–7 cyfr (format; brak katalogu TERYT do sprawdzenia
   istnienia), limity długości wszystkich pól, `extra="forbid"` — współrzędne i
   nieznane pola są odrzucane (422), nigdy po cichu zapisywane (ADR-002).
7. **Rate limit.** Limiter in-memory (okno kroczące, 30 zapisów/min/IP) na `POST` i
   `DELETE`, 429 + `Retry-After`. IP tylko w pamięci procesu (TTL = okno, sweep przy
   >10k kluczy), nigdy w PostgreSQL ani logach.
8. **Logi.** Żadnego logowania tokenu push ani sekretu (nie ma ich w ścieżce/query;
   `RequestLoggingMiddleware` loguje tylko metodę, ścieżkę, status). Odpowiedzi nie
   zawierają tokenu ani hasha.
9. **Dane.** `devices`: `installation_id`, `secret_hash`, `platform`, `push_token`,
   `observed_area_code`, `app_version`, `active`, `created_at/updated_at/last_seen_at`.
   Brak współrzędnych, brak IP, brak PII. To dane pseudonimowe → inwentarz
   TASK-14.2, prawo do usunięcia = `DELETE` + retencja.

## Consequences

- Utrata sekretu (np. wyczyszczone secure storage przy tym samym id) = klient
  generuje nowy `installation_id`; stary rekord znika przez retencję (TASK-14.2).
  Brak odzyskiwania „po id” jest świadomy — to dokładnie ta dziura, którą zamykamy.
- Limiter działa per proces (N workerów = N× limit, reset po restarcie) i za proxy
  widzi IP proxy, dopóki uvicorn nie dostanie `--proxy-headers` +
  `FORWARDED_ALLOW_IPS` (follow-up TASK-15.x); współdzielony limiter = decyzja
  TASK-15.4, rozszerzenie na resztę API = TASK-14.2. Przy NAT operatora limit jest
  wspólny dla wielu telefonów (stąd 30/min, nie mniej).
- Nowe `installation_id` są tanie, więc limiter jest jedyną realną barierą przed
  masowym tworzeniem rekordów; twarde limity per gmina itp. należą do TASK-12.2/6.2.
- Nieaktywne rekordy (`active=false` lub stare `last_seen_at`) nie są jeszcze
  kasowane — job retencji/usuwania to zakres TASK-14.2; `last_seen_at` daje mu dane.
- Reakcja na `DeviceNotRegistered` od Expo (dezaktywacja tokenu) — TASK-10.2.
