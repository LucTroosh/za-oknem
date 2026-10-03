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
