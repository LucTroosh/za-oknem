# ADR-013: Granica Measurement ≠ Forecast ≠ Event ≠ Alert ≠ Notification + geo-matching alertów

**Status:** Proposed (do zaakceptowania wraz z merge PR „event-alert-matching”)
**Data:** 2026-10-01

Numer zarezerwowany w ADR-014 dla `Event`. Treść `Event` zależy od decyzji o źródle (niżej),
więc ten ADR (a) utrwala granicę pojęć zgodnie z kodem, (b) rozstrzyga geo-matching alertów,
(c) opisuje `Event` i `Notification` jako **jeszcze nieistniejące** — bez udawania, że są.

## Context

Reguła #7 zabrania mieszania pojęć, a Master Plan §29–§32 definiuje je oszczędnie. Stan kodu:

| Pojęcie | Tabela / kod | Znaczenie |
|---|---|---|
| Measurement | `measurements` (GIOŚ, IMGW hydro) | zaobserwowana wartość, `observed_at` |
| (obserwacja pogody/pyłków) | `weather_snapshots`, `pollen_snapshots` | obserwacja / modelowany odczyt per `geo_area` |
| Forecast | `forecasts` (ADR-010) | wartość PRZYSZŁA, `valid_from/until` + `forecast_reference_time` |
| Alert | `alerts` (ADR-009) | ostrzeżenie wydane przez źródło (IMGW hydro), tekst i `severity_raw` bez reinterpretacji |
| Event | **brak** | zweryfikowane zdarzenie środowiskowe (§31) — brak źródła (BACKLOG TASK-9.4) |
| Notification | **brak** (tylko `devices`, ADR-017) | wysyłka do urządzenia (§32/§50) |

Ostrzeżenia hydro IMGW (`obszary`, zweryfikowane na żywo, ADR-009) niosą wyłącznie
`wojewodztwo` (nazwa), `opis` i `kod_zlewni` (kody zlewni). **Nie niosą TERYT, powiatów ani
gmin.** Ostrzeżenia meteo: kształt rekordu niezweryfikowany (TASK-9.2 ⛔), więc ich
obszarów nie znamy i nie zgadujemy (reguły #10/#15).

## Problem

1. Gdzie dokładnie kończy się Alert, a zaczyna Event i Notification — tak, by kolejne taski
   (Alert Engine 9.6, push 10.x) nie rozmyły granic?
2. Jak deterministycznie (#9) dopasować alert do obszaru użytkownika, skoro źródło daje
   tylko nazwę województwa?

## Options

**Granica pojęć** — A: jedna tabela „zdarzenia" z polem `kind` (alert/event/notification) —
odrzucone, to dokładnie mieszanie z #7. B: osobne byty z jednokierunkowymi odniesieniami
(niżej). **Wybrane B.**

**Geo-matching** — A: nowa tabela `alert_areas` (alert↔`geo_area`) wypełniana przy ingeście.
B: czysta funkcja nad surowym JSON `alerts.areas` + `geo_areas.teryt_code`, liczona przy
odczycie. C: dopasowanie po lat/lon do zlewni (brak danych zlewnia↔gmina — niedostępne).
D: LLM/fuzzy po nazwach — zakazane (#9, #10).
**Wybrane B**: ostrzeżeń jest kilka–kilkadziesiąt naraz, a stałe wiersze powiązań musiałyby
być przeliczane przy każdym imporcie granic i każdej zmianie mapy nazw (stan pochodny, który
się starzeje). Funkcja jest deterministyczna, testowalna i nie wymaga migracji.

## Decision

**Granica pojęć (obowiązująca):**
- **Measurement/Snapshot** i **Forecast**: dane o świecie; Forecast zawsze z oknem ważności.
- **Alert** = ostrzeżenie wydane przez *organ źródłowy*. Pole `severity_raw`, `description`,
  `comment`, `areas`, `published_at` to przekaz źródła (#10). My dokładamy tylko metadane
  odczytu (`freshness`, `geo_match`) — nigdy nie zmieniamy treści ani nie liczymy własnej
  „ważności".
- **Event** = zweryfikowane zdarzenie (§31), odrębny rekord z provenance (`source_fetch_id`,
  ADR-014). **Nie powstaje w tym PR**: nie ma źródła ani workflow zasilania (BACKLOG 9.4:
  decyzja człowieka). Alert nie jest Eventem i nie jest do niego „promowany"; Event może w
  przyszłości *odwoływać się* do Alertu (FK od Event do Alert), nigdy odwrotnie.
- **Notification** = fakt (próba) wysyłki konkretnego alertu/eventu do konkretnego `Device`.
  Odwołuje się do Alertu/Eventu i Device (ADR-017), nigdy go nie zastępuje; Alert istnieje
  bez Notification (§32). Wymaga kluczy FCM/APNs (blokada człowieka, TASK-10.1) — poza tym PR.
- Kierunek zależności: `Alert/Event → (geo_match) → area → Notification → Device`. Preferencje
  (TASK-10.3a) i anti-spam (10.2) żyją przy Notification, nie w Alercie.

**Geo-matching alertów (wdrożone, `app/alert_geo.py`):**
- Jedyny poziom, który źródło faktycznie daje: nazwa województwa → kod TERC (2 cyfry; stała
  oficjalna lista 16 pozycji, porównanie bez uwzględniania wielkości liter/spacji) →
  prefiks `geo_areas.teryt_code` (powiat 4, gmina 7 — `teryt_covers` akceptuje tylko te
  długości, więc „1" ani „146" nie są prefiksem). Wynik: `geo_match = "voivodeship"`.
- Dopasowanie jest **na poziomie województwa z definicji**: alert dla jednej zlewni w
  wielkopolskim trafia do każdego obszaru w wielkopolskim. Nazwane to jest w polu, nie
  udajemy dokładności; `kod_zlewni` nie jest mapowany na gminy (brak zbioru zlewnia↔gmina).
- **Fail-safe, nie fail-silent** (dane bezpieczeństwa, #10): nierozpoznana nazwa, pusta
  lista `obszary` albo obszar bez `teryt_code` (seed jeszcze niepowiązany z importem gmin,
  ADR-019) daje `geo_match = "unresolved"` — alert jest pokazywany i oznaczony, nie ukrywany.
  Alert częściowo nierozpoznany dopasowuje się przez swoje rozpoznane województwa, a do
  pozostałych obszarów trafia jako `unresolved`.
- API (addytywnie): `GET /api/v1/alerts/latest?geo_area_id=N` (404 dla nieznanego obszaru;
  bez parametru lista krajowa jak dotąd, `geo_match = null`); `AlertOut.geo_match`; w
  `/dashboard/latest` każdy obszar ma `local_alerts`, a krajowe `alerts` zostaje bez zmian.
  Kontrakt (`openapi.json`, `schema.ts`) zregenerowany (ADR-024).
- Meteo (`imgw_warningsmeteo`): `normalize()` nadal ⛔; gdy kształt `obszary` zostanie
  zweryfikowany, rozszerza się `alert_voivodeship_codes` (np. o jawne kody TERYT przez
  `teryt_covers`) — bez zmian API.

## Consequences

- Użytkownik z obszarem w TERYT widzi alerty swojego województwa; do czasu załadowania granic
  gmin (krok ręczny, ROADMAP §6) obszary seedowe mają `teryt_code = NULL`, więc dostają
  wszystkie alerty jako `unresolved` — czyli dzisiejsze zachowanie, tyle że uczciwie
  oznaczone. Odblokowanie to dane, nie kod.
- Brak migracji i brak stanu pochodnego; zmiana mapy nazw = zmiana jednego słownika.
- Mobile nie korzysta jeszcze z `local_alerts`/`geo_match` (ekran Alerty to TASK-9.7).
- Nadal otwarte: Event (źródło), Alert Engine 9.6, Notification (klucze), meteo,
  filtrowanie `/hydro/latest` po lokalizacji (osobna część TASK-9.5).
