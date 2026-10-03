# Probe operatora: jak zamknąć blocker B-6 (i część B-8)

Środowisko agenta nie sięga do `dane.gios.gov.pl`, więc pytania, od których zależy `APPROVED`, rozstrzyga
**uruchomienie na maszynie z internetem** (Twój komputer albo VPS). Narzędzie `app.gios_open.probe`
(PR GIOS-02) nic nie zapisuje do bazy i wysyła kilka żądań, jedno na 5 s, nigdy równolegle.

## Co ustala

| Pytanie (blocker) | Jak odpowiada probe |
|---|---|
| Czy `liczbaRekordow` jest sumą wszystkich rekordów? (B-6) | `reported_count_equals_page_length` / `reported_count_exceeds_page_length` na stronie 50 elementów |
| Jak wygląda koniec danych i strona poza końcem? | `page_far_beyond_end` (`empty_observed`, czy jest klucz `strona`, albo błąd źródła) |
| Czy kolejność jest stabilna i spójna między rozmiarami strony? | `same_page_is_stable`, `order_is_consistent_across_page_sizes` |
| Czy strony się powtarzają albo nakładają? | `page1_repeats_page0`, `page1_overlaps_page0`, `walk.stopped_by` |
| Czy ostatnia strona jest krótsza (czy „krótka strona = koniec” jest bezpieczne)? | `walk.page_lengths`, `walk.last_page_short` |
| Ile rekordów ma cały zakres i czy przejście się kończy? | `walk.total_records`, `walk.completed` |
| Czy zakres dat/filtrów przechodzi? | `steps.*.error` (np. „zakres dat poza limitem”) |

## Uruchomienie

Z katalogu repo, po `git pull` i `docker compose up -d --build api`:

```bash
# Hałas: pomiary, rok 2024, Śląskie, kategoria Droga (pierwsza operacja do wdrożenia)
docker compose exec api python -m app.gios_open.probe \
  --service halas --path /v1/pomiar-halasu-w-srodowisku \
  --param kategoria=Droga --param "wojewodztwo=ŚLĄSKIE" \
  --param dataOd=2024-01-01 --param dataDo=2024-12-31 \
  --walk-pages 40 --out /tmp/halas-probe.json
docker compose cp api:/tmp/halas-probe.json ./halas-probe.json
```

Wartości województw to **wielkie litery** (enum z OpenAPI); mała litera daje `wynik.status=BLAD` przy HTTP 200.
Kolejne operacje (ta sama składnia, inne `--service` i `--path`):

| Operacja | `--service` | `--path` | Filtry startowe |
|---|---|---|---|
| PRTR uwolnienia | `prtr` | `/v1/uwolnienia` | `rokRaportu=2023` + `wojewodztwo=ŚLĄSKIE` (bez roku zwraca rekordy sprzed lat; bez województwa zbiór jest duży) |
| Rejestr ZZR/ZDR | `powazne-awarie` | `/v1/zaklady` | bez filtrów |
| NEC stanowiska | `nec` | `/v1/monitorowanie/stanowiska` | `rokRaportowania=2023` |

`--walk-pages N` chodzi do N stron po 50 (kończy się wcześniej, gdy przejście się domknie). Dla dużych zbiorów
zacznij od `--walk-pages 5`. Zmienne `GIOS_OPEN_*` (limit odstępu, liczba ponowień) są w `.env.example`.

## Co mi odesłać

Plik JSON (albo jego treść) w PR/wiadomości. Na jego podstawie zapiszę w `07-operation-gates.md` i w Source Registry
semantykę paginacji i kształt pustego wyniku, a operację przeniosę z `IMPLEMENTABLE` do `APPROVED` (po pozostałych
punktach gate: zakres dat, jednostki, cykl). Raport zawiera jeden przykładowy rekord (`first_record_sample`) i nic
poza publicznymi danymi GIOŚ (CC BY 4.0).

## Gdy coś pójdzie nie tak

- `GiosOpenTransportError` / timeout: sieć albo usługa niedostępna; probe zapisuje to jako wynik kroku.
- `GiosOpenSourceError ... 400`: zły filtr (najczęściej brak wymaganego parametru albo zła wielkość liter).
- `GiosOpenPageLoopError` w `walk.stopped_by`: usługa zwraca tę samą stronę zamiast następnej. To właśnie dowód,
  którego szukamy; nie ponawiaj, odeślij raport.

---

# Import hałasu (GIOS-04): walidacja, import, włączenie sekcji

Kolejność ma znaczenie: najpierw walidacja bez zapisu, dopiero potem import i flaga. Import jest **ręczny** — cykl
publikacji GIOŚ jest nieznany (wyjątek od reguły #16, ADR-032 pkt 8), nic nie biegnie w tle.

**Zakres dat: zawsze `2015-01-01` – `2026-12-31` (jeden snapshot na kombinację obejmuje wszystkie lata).**
Filtr dat nie ogranicza okresu samego pomiaru, a punkt mierzony ostatnio w 2022 wypadłby z importu jednego roku.
Zweryfikowane 2026-10-03 (Droga × ŚLĄSKIE): 4415 rekordów w 89 stronach (dla samego 2024 było 346). Jedna kombinacja
tej wielkości to ok. 7,5 min przy limicie 1 żądanie / 5 s; pełny kraj to dziesiątki minut do kilku godzin (mniejsze
kategorie są krótsze) — puść w tle. Zakres musi być **ten sam** przy każdym imporcie, bo jest częścią klucza snapshotu
(inny zakres = osobny, równoległy snapshot).

```bash
# 1) Walidacja bez zapisu do bazy: ile rekordów, ile stron, co odrzucone i dlaczego
docker compose exec api python -m app.connectors.gios_noise.ingest \
  --date-from 2015-01-01 --date-to 2026-12-31 \
  --category Droga --voivodeship ŚLĄSKIE --validate-only

# 2) Import jednej kombinacji; można powtarzać (nowy snapshot zastępuje poprzedni)
docker compose exec api python -m app.connectors.gios_noise.ingest \
  --date-from 2015-01-01 --date-to 2026-12-31 \
  --category Droga --voivodeship ŚLĄSKIE

# 3) Cały kraj (4 kategorie × 16 województw = 64 kombinacje) — długo, w tle
docker compose exec -d api python -m app.connectors.gios_noise.ingest \
  --date-from 2015-01-01 --date-to 2026-12-31

# 4) Co poszło do kwarantanny (rekordy, których parser nie przyjął) i dlaczego
docker compose exec api python -c "
import json
from app.db import SessionLocal
from app.models import IngestQuarantine as Q
db = SessionLocal()
for q in db.query(Q).filter(Q.source_id == 'gios_noise').all():
    print(q.reason, '|', q.detail, '|', json.dumps(q.raw, ensure_ascii=False))
"
```

- Kombinacja, która się nie uda, jest raportowana (kod wyjścia 1), a poprzedni aktywny snapshot **zostaje** i dalej
  jest serwowany. Inny trwający import tej usługi = kod 2.
- Rekordy niepasujące do kształtu (zła kolejność współrzędnych, tekst zamiast liczby, kategoria sprzeczna z filtrem,
  duplikat) trafiają do `ingest_quarantine` z powodem; import idzie dalej. W Droga × ŚLĄSKIE było ich 2 z 4415
  (1 `duplicate_record`, 1 pozycja bez wyniku: `wynikPomiaru: null`) — punkt 4 pokazuje, co to było. Powody: `value_missing`
  (źródło nie podało wyniku), `value_not_number` (wynik innego typu niż liczba = zmiana kontraktu, do zgłoszenia),
  `duplicate_record` z `detail`: `identical` (ten sam rekord opublikowany dwa razy) albo `differs: <pola>` (klucz
  rekordu byłby wtedy zbyt gruby — do zgłoszenia).
- „W pobliżu nie ma punktu pomiarowego” (`no_coverage`) pojawia się dopiero, gdy **każda** z 64 kombinacji ma aktywny
  import obejmujący cały zakres `NEIGHBORHOOD_NOISE_COVERAGE_FROM` – `…_TO` (domyślnie 2015-01-01 – 2026-12-31).
  Przy imporcie częściowym albo jednego roku API zwraca `unavailable` (brak punktu w niepełnych danych nie dowodzi
  braku punktu). Komunikat podaje, z jakich lat są dane.
- Włączenie: `NEIGHBORHOOD_NOISE_ENABLED=true` w `.env` serwera i restart `api`. Promień: `NEIGHBORHOOD_NOISE_MAX_KM`
  (domyślnie 10). Dopóki flaga jest wyłączona, `GET /api/v1/neighborhood` zwraca `enabled=false`, a aplikacja
  nie pokazuje wejścia.
- Bez internetu w środowisku: `--file odpowiedz.json` (lista odpowiedzi stron, jedna kombinacja).
- Wynik walidacji i treść kwarantanny prześlij — zaktualizuję bramkę.
