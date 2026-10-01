# TASK 10.1 — Device registration + push tokens (Expo), backend

## Goal

Backend potrafi zarejestrować instalację appki do push **bez konta** (rule #11):
przechować token Expo i obserwowany obszar (TERYT, ADR-002), a operacje na rekordzie
zabezpieczyć tak, by nie dało się przejąć/wyrejestrować cudzego urządzenia (ADR-017).

## Scope

- Model `Device` + migracja Alembic `0010_devices.py` (`installation_id` unikalny,
  `secret_hash`, `platform`, `push_token` unikalny/nullable, `observed_area_code`,
  `app_version`, `active`, `created_at/updated_at/last_seen_at`).
- `POST /api/v1/devices` — idempotentny upsert po `installation_id` (rejestracja,
  odświeżenie tokenu, zmiana obszaru — klient 12.5/10.5 używa tego samego endpointu).
- `DELETE /api/v1/devices/{installation_id}` — dezaktywacja (czyści token i obszar).
- `app/rate_limit.py` — limiter in-memory per IP (30/min) na oba endpointy.
- `docs/architecture/ADR-017-device-registration.md`.
- Zgodność z BACKLOG: tylko 10.1. Preferencje powiadomień (10.3a), wysyłka i
  reakcja na `DeviceNotRegistered` (10.2), klient mobilny (10.5) — NIE tutaj.

## Acceptance Criteria

- [ ] Pierwsze `POST` → 201 + `device_secret` (jednorazowo), w bazie tylko SHA-256.
- [ ] Powtórne `POST` z poprawnym `X-Device-Secret` → 200, bez duplikatu wiersza;
      zmieniane tylko pola obecne w body; `push_token: null` czyści token.
- [ ] `POST` na istniejące id bez/ze złym sekretem → 403, rekord bez zmian.
- [ ] `DELETE` z poprawnym sekretem → 204, `active=false`, token i obszar wyczyszczone,
      idempotentne; zły sekret / nieznany id → identyczne 404.
- [ ] Zły format tokenu, `platform`, `installation_id`, `observed_area_code`, zbyt długie
      pola oraz współrzędne / nieznane pola → 422.
- [ ] Ten sam token na nowym `installation_id` odbierany staremu.
- [ ] Token push i sekret nie pojawiają się w odpowiedziach (poza jednorazowym sekretem)
      ani w logach.
- [ ] Przekroczenie limitu → 429 + `Retry-After`.
- [ ] Migracja 0010 zgodna z modelem (`alembic upgrade head`, `alembic check`), ruff,
      mypy, pytest zielone w CI.

## Tests

`apps/api/tests/test_devices.py` (SQLite, `StaticPool`): rejestracja i hash sekretu,
idempotencja, częściowy update, 403/404 bez ujawniania, przenoszenie tokenu,
parametryzowana walidacja 422 (w tym współrzędne), rejestracja bez tokenu,
dezaktywacja + reaktywacja, brak sekretu/tokenu w logach, 429 i okno limitera.

## Non-goals

Wysyłka push i obsługa `DeviceNotRegistered` (10.2); preferencje (10.3a); klient
mobilny (10.5, 12.5); resolver GPS → TERYT i sprawdzanie istnienia kodu w katalogu
(6.2); kasowanie/retencja rekordów (14.2); współdzielony limiter/Redis (15.4);
konfiguracja proxy-headers (15.x); endpoint `/push-tokens` z §Master Planu (zbędny,
token jest polem `devices`).

## Dependencies

ADR-002, ADR-017. Brak zależności od kluczy FCM/APNs (blokada dotyczy wysyłki, nie
rejestracji). Nie dodaje pakietów.

## Data Contract

Żądanie `POST /api/v1/devices` (nagłówek `X-Device-Secret` tylko dla istniejącego id):

```json
{"installation_id": "<32-64 znaków [A-Za-z0-9_-]>", "platform": "android|ios",
 "push_token": "ExponentPushToken[...]" , "observed_area_code": "0208011",
 "app_version": "1.0.0"}
```

`push_token`, `observed_area_code`, `app_version` opcjonalne/nullable. Odpowiedź
(`DeviceOut`): `installation_id`, `platform`, `push_registered`, `observed_area_code`,
`app_version`, `active`, `last_seen_at`, `device_secret` (tylko w 201, inaczej `null`).
`DELETE /api/v1/devices/{installation_id}` → 204. Błędy: 403, 404, 409 (tylko UNIQUE/deadlock 40P01/serialization 40001 przy równoległej
rejestracji; ponów; jeśli ponowienie da 403, nowy `installation_id`; inne błędy bazy, np. rozłączenie, to 500, nie 409), 422, 429.

### Reguły dla klientów i konsumentów

- **Klient (10.5/12.5):** 403 na własnym `installation_id` bez ważnego sekretu (np. po
  utracie odpowiedzi 201) = wygeneruj nowy `installation_id` i zarejestruj się od nowa.
- **Wysyłka (10.2):** musi filtrować `active AND push_token IS NOT NULL`. Urządzenie,
  któremu odebrano token (przeniesienie na nową instalację, `push_token: null`), zostaje
  `active=true` z `push_token=NULL`.

## Follow-up (TASK-15.x)

Uvicorn z `--proxy-headers` i `FORWARDED_ALLOW_IPS` ustawionym wyłącznie na IP proxy
(Caddy). Bez tego limiter za proxy widzi jeden adres, czyli jeden globalny kubełek.
Nie implementowane w tym PR.

## Security

Patrz ADR-017: sekret 256-bit zwracany raz, hash SHA-256 + porównanie stałoczasowe,
nagłówek zamiast URL, 404 bez rozróżniania, brak tokenów/sekretów w logach i
odpowiedziach, brak współrzędnych/IP/PII w bazie, rate limit per IP. Znane ograniczenia:
limiter per proces i za proxy widzi IP proxy bez `--proxy-headers`; `installation_id`
pojawia się w ścieżce `DELETE` (logi ścieżek) — jest pseudonimowy, nie jest sekretem.

## Architecture Impact

Nowa tabela `devices`, nowy router, ADR-017 (uwierzytelnianie urządzeń bez konta).
Brak mikroserwisów/kont. Rule #7: `Device` ≠ Notification ≠ preferencje.
