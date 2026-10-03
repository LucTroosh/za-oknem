# ADR-032: Moduł „Twoja okolica” (dodatkowe dane GIOŚ) — kontrakt, granice i flagi

**Status:** Accepted
**Data:** 2026-10-03
**Uzupełnia:** ADR-001/006/025/029 (powietrze, geo), ADR-004 (częstotliwość fetchu), ADR-012 (świeżość), ADR-013 (Alert ≠ Event), ADR-014 (provenance), Master Plan §11 (poza MVP)
**Podstawa wiedzy:** `docs/data/gios/` (pakiet z PR #134, stan 2026-10-03), `docs/data/gios/07-operation-gates.md`

## Context

Poza bieżącymi warunkami (powietrze, pogoda, pyłki, woda, alerty) właściciel chce pokazać, co dotyczy
okolicy wybranej lokalizacji: historyczne pomiary i oceny hałasu, zakłady raportujące emisje (PRTR),
rejestr zakładów ZZR/ZDR i historię awarii, monitoring wód i ekosystemów. GIOŚ opublikował siedem
nowych specyfikacji OpenAPI (CC BY 4.0). Research (pakiet `docs/data/gios/`) pokazał ograniczenia,
które zmieniają pierwotny pomysł: brak współrzędnych zakładów PRTR i ZZR/ZDR, brak wyników jakości
w API wód powierzchniowych (tylko plan monitoringu), niepotwierdzone jednostki PRTR i CRS wód
podziemnych, rzeczywiste odpowiedzi różne od specyfikacji (błąd przy HTTP 200, dodatkowe wymagane
filtry), brak deklarowanych limitów i cyklu publikacji.

## Problem

1. Jak dodać dane o okolicy bez nowej zakładki, mapy, konta, nowego uprawnienia lokalizacji ani
   zmiany stosu (Master Plan §11, CLAUDE.md)?
2. Jak nie pomylić danych historycznych, rejestrowych i planistycznych z bieżącymi warunkami,
   ostrzeżeniami i prognozą (reguła #7), ani ponownego pobrania starego pliku ze świeżym pomiarem
   (reguła #8)?
3. Jak włączać źródła pojedynczo, skoro każde ma inny stan weryfikacji (reguła #15), a awaria jednego
   nie może psuć reszty (reguła #1)?

## Options

**Wejście w UI:** (A) nowa zakładka — odpada (trzy zakładki to zablokowana architektura); (B) kafelki
nowych danych na Start — odpada (dashboard ma zostać prosty, nie kilkanaście kafelków);
(C) jeden drugorzędny wiersz na Start prowadzący do ukrytego ekranu — wybrane.

**Model danych pomiarów okresowych:** (A) reuse `measurements` — odpada: tabela ma jeden `observed_at`,
a dashboard i EAQI czytają z niej bieżące odczyty; pomiar hałasu to przedział z porą doby i kategorią,
a rejestr/plan/ocena nie są pomiarami; (B) osobne tabele addytywne per rodzaj danych — wybrane.
Wspólny `observation` odłożony do chwili, gdy drugi rodzaj danych faktycznie go wymaga.

**Pobieranie:** (A) scheduler godzinowy jak GIOŚ powietrze — odpada (dane roczne/wieloletnie,
cykl publikacji nieznany, ADR-004 i reguła #16); (B) import ręczny przez CLI operatora z walidacją
i promocją snapshotu — wybrane; cykliczność dopiero po potwierdzeniu cyklu publikacji.

## Decision

1. **Zakres:** moduł addytywny „Twoja okolica”. Wejście: drugorzędny wiersz na Start (widoczny tylko, gdy
   API raportuje co najmniej jedną włączoną sekcję) → ukryty ekran (jak Pogoda/Powietrze). Zostają
   zakładki Start / Alerty / Ustawienia. Bez mapy, konta, push i dodatkowych uprawnień. To nie jest
   „Green Index” ani „pełna historia danych” z §11: nie liczymy wspólnego wyniku i nie przechowujemy
   własnych szeregów czasowych, tylko pokazujemy opublikowane rejestry z okresem i źródłem.
2. **Sekcje (kolejność w UI):** Hałas → Zakłady raportujące emisje → Rejestr przemysłowy → Monitoring wód →
   Monitoring ekosystemów. Każda ma własne źródło, własną flagę i własny stan; kolejność wdrożenia
   wg `docs/data/gios/04-work-breakdown.md`. Nie ma wspólnego score „bezpiecznie”.
3. **Rodzaje danych (`data_kind`)** i ich miejsce w modelu pojęć (reguła #7):

   | `data_kind` | Co to jest | Czym NIE jest |
   |---|---|---|
   | `historical_measurement` | pomiar z przedziału dat (np. hałas) | pomiarem „teraz”, Alertem, Forecastem |
   | `long_term_assessment` | ocena roczna/wieloletnia, mapa długookresowa | bieżącą jakością |
   | `register_entry` | wpis rejestru (PRTR, ZZR/ZDR) | naruszeniem, aktywnym zagrożeniem |
   | `monitoring_plan` | plan badań (wody) | wynikiem jakości |
   | `historical_event` | zdarzenie z przeszłości (awaria) | Alertem; to `Event` (ADR-013), nigdy push |

   Żadna z nich nie uruchamia powiadomień ani rekomendacji „zostań w domu”; „Co dziś robimy?”
   (ADR-016) czyta wyłącznie bieżące powietrze/pogodę.
4. **API (tylko z bazy, reguła #14):** `GET /api/v1/neighborhood?geo_area_id={id}`. **Odstępstwo od
   propozycji pakietu (`place_id`):** mobile zapamiętuje `geoAreaId`, a siedem miast z seedów nie ma
   `place_id` (`geo_areas.place_id` jest NULL). Obszar wskazuje miejscowość przez `place_id`, a bez
   niego przez własne współrzędne i TERYT. Odpowiedź:

   ```json
   {
     "geo_area_id": 12,
     "enabled": true,
     "sections": [
       {
         "id": "noise",
         "data_kind": "historical_measurement",
         "availability": "available",
         "source_id": "gios_noise",
         "attribution": "Źródło danych: GIOŚ · CC BY 4.0. Dane zostały uporządkowane i przetworzone przez Za Oknem.",
         "license_url": "https://creativecommons.org/licenses/by/4.0/",
         "source_period": { "from": "2024-05-10", "to": "2024-11-10", "precision": "date" },
         "fetched_at": "2026-10-03T10:25:05Z",
         "retrieval_status": "ok",
         "spatial_match": { "kind": "nearby_site", "distance_km": 4.2, "reference": "selected_location" },
         "limitations": ["historical_not_live"],
         "items": []
       }
     ]
   }
   ```

   To kształt, nie dane. Pola dokładnie wg tej decyzji (OpenAPI i `packages/api-contract` powstają przy
   pierwszej implementacji, PR-D).
5. **`availability`** (jawny enum, osobno od świeżości): `available` · `no_coverage` (brak źródła/punktu w
   zasięgu tej lokalizacji) · `no_records` (poprawnie zakończone zapytanie bez rekordów; wolno zwrócić
   dopiero po kompletnym snapshocie) · `unavailable` (awaria, brak snapshotu) · `pending_verification`
   (źródło bez zatwierdzonej bramki). Awaria jednej sekcji nie zmienia pozostałych.
6. **Czas, nie „świeżość”.** Sekcje historyczne **nie mają pola `freshness`**. Mają `source_period`
   (+ `precision`: `date` | `year` | `range`), `fetched_at` (moment naszego pobrania, zawsze UTC) i
   `retrieval_status` (`ok` | `degraded` — ostatnie pobranie nieudane, pokazujemy poprzedni dobry
   snapshot | `none`). Ponowne pobranie starego pomiaru nie czyni go aktualnym: UI zawsze pokazuje
   okres z danych obok daty pobrania. `FRESH/RECENT/STALE/UNAVAILABLE` (ADR-012) zostają dla danych
   bieżących. Dzień zachowuje precyzję dnia, rok — roku; nie wymyślamy godziny 00:00.
7. **Flagi (env, domyślnie wyłączone):** `NEIGHBORHOOD_NOISE_ENABLED`, `NEIGHBORHOOD_PRTR_ENABLED`,
   `NEIGHBORHOOD_INDUSTRIAL_ENABLED`, `NEIGHBORHOOD_WATER_ENABLED`, `NEIGHBORHOOD_ECOSYSTEMS_ENABLED`.
   API zwraca tylko włączone sekcje; gdy żadna nie jest włączona: `enabled=false`, `sections=[]`, a mobile
   nie pokazuje wiersza na Start (zero zmian w obecnym UI, rollback = wyłączenie flagi).
8. **Pobieranie:** bez schedulera dla nowych źródeł (cykl publikacji UNKNOWN — wyjątek od reguły #16
   uzasadniony tutaj i w Source Registry). Import ręczny przez CLI (`--validate-only`, `--file`), snapshot
   staging → atomowa promocja po kompletnym przebiegu, poprzedni dobry snapshot zostaje przy błędzie, nic
   nie jest usuwane po niekompletnym przebiegu. Reguła #5 zachowana: timeout połączenia 5 s / odpowiedzi
   20 s, najwyżej 2 ponowienia (timeout/429/5xx, `Retry-After` + jitter), BEZ ponowień dla błędu walidacji.
   Limiter własny (nie limit GIOŚ): 1 żądanie / 5 s na usługę, równoległość 1, konfigurowalny.
9. **Poprawność odpowiedzi nowych API:** HTTP 200 z `wynik.status=BLAD` to błąd źródła; `SUKCES` z
   `liczbaRekordow=0` i bez `strona` to zaobserwowany pusty wynik; `liczbaRekordow` NIE jest sumą wszystkich
   rekordów (w próbach równa rozmiarowi strony); koniec paginacji wg potwierdzonej pustej strony, z ochroną
   przed powtórzoną stroną (hash) i limitem stron. Nieznane pola trafiają do `raw`, nieznane enumy do
   kwarantanny. `wynik.data` nie jest datą pomiaru.
10. **Geo (deterministyczne, testowalne, reguła #9):**
    - hałas, pomiar: najbliższy punkt (WGS84: `coordWgs84X` = długość, `coordWgs84Y` = szerokość) **do
      progu** `NEIGHBORHOOD_NOISE_MAX_KM` (domyślnie 10 km; konfigurowalny, to granica „w okolicy”, nie
      deklaracja reprezentatywności); odległość zawsze „od wybranej lokalizacji”, nie od telefonu ani domu;
      poza progiem: `no_coverage`, nigdy wynik „miejscowości”;
    - hałas, zasięg (polygon): dopiero po zweryfikowanej geometrii i CRS (zablokowane);
    - PRTR i ZZR/ZDR: dopasowanie administracyjne po województwie / powiecie / miejscowości (bez promienia i
      odległości, bo brak współrzędnych zakładów); sama nazwa miejscowości bez hierarchii nie wystarcza;
    - wody powierzchniowe/podziemne: dopiero z geometrią JCWP/JCWPd i potwierdzonym CRS (zablokowane).
11. **Źródła i licencja:** siedem nowych źródeł `gios_*` ma osobne wpisy w `docs/data/source-registry.md`,
    wszystkie CC BY 4.0 w specyfikacjach. Atrybucja w każdej sekcji i w Ustawienia → Źródła:
    „Źródło danych: GIOŚ · CC BY 4.0. Dane zostały uporządkowane i przetworzone przez Za Oknem. Okres danych:
    {period}. Pobrano: {fetched_at}.” + link do strony źródła i licencji; bez sugerowania poparcia GIOŚ.
    Licencja zbioru nie przenosi się na inne portale, mapy bazowe ani grafiki. Bez monetyzacji w tej zmianie
    (ADR-031 zostaje).
12. **Zmiana bazy:** wyłącznie migracje Alembic, addytywne (reguła #4). Rollback: wyłączenie flag
    (UI znika, dane zostają); rollback bazy tylko przetestowaną migracją `downgrade`.

## Consequences

- Dashboard i istniejące endpointy bez zmian i kompatybilne; moduł można wyłączyć jedną flagą.
- Sekcje startują niezależnie od siebie; blokery per operacja (patrz `07-operation-gates.md`) blokują
  tylko daną sekcję. Dziś: hałas (pomiary) — gotowy do implementacji i weryfikacji przez operatora;
  PRTR/ZZR/ZDR — lista administracyjna możliwa, liczby emisji zablokowane do potwierdzenia jednostek;
  wody powierzchniowe — tylko plan monitoringu, karta jakości zablokowana do pozyskania wyników i geometrii;
  wody podziemne — zablokowane do potwierdzenia CRS i polygonów JCWPd; mapa/ekspozycja hałasu — zablokowana
  do próbki prawdziwego zasięgu.
- Hałas z państwowego monitoringu ma rzadką siatkę punktów: dla wielu lokalizacji wynik to `no_coverage`.
  Dlatego ekran pokazuje taką sekcję jako jedną spokojną linię, a wiersz na Start pojawia się dopiero po
  włączeniu przynajmniej jednej flagi.
- Dane „z rejestru” mogą mylić użytkownika, jeśli UI nada im ton ostrzeżenia: żadnych czerwonych alarmów
  za sam wpis PRTR/ZZR/ZDR; „przekroczenie” z pomiaru hałasu jest cytatem ze źródła dla tego punktu, nie oceną
  miejscowości.
- Koszt: nowe tabele addytywne, nowy ekran i kontrakt API; brak nowych zależności w tym ADR.
- Weryfikacja na żywo (powtórzenie żądań do `dane.gios.gov.pl`) nie jest możliwa z środowiska agenta
  (blokada egress); robi ją operator CLI `--validate-only` i wpisuje wynik do Source Registry. Do tego
  czasu operacje mają status wg dowodów z pakietu, nie wyżej.
