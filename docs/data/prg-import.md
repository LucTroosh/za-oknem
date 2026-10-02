# Import granic gmin (PRG) — procedura operatora

Źródło: `prg_gminy` (GUGiK), status APPROVED do importu (`source-registry.md`, decyzja właściciela
2026-10-02). Importer: `apps/api/app/connectors/prg_gminy/`. Repo nie zawiera danych — plik przygotowuje
operator, import jest ręczny, raz w roku (dane PRG wg stanu na 1 stycznia).

## Po co
Zamienia współrzędne (GPS, miejscowość) na dokładną gminę (point-in-polygon, reguła #9) i nadaje
miejscowościom kod TERYT gminy. Dla alertów IMGW hydro (poziom województwa) nic się nie zmienia; to
fundament pod dokładniejsze źródła i pod `POST /api/v1/geo/resolve`. Wybór miasta w aplikacji NIE zmienia
się: `GET /areas` domyślnie zwraca tylko obszary pollowane (zaimportowane gminy mają
`weather_polling_active = false`), a dowolną miejscowość wybiera się z rejestru `places` (GeoNames).

## Kroki (Mac, katalog repo)
```
brew install gdal                       # ogr2ogr / ogrinfo
mkdir -p data && cd data
curl -fLO https://opendata.geoportal.gov.pl/prg/granice/00_jednostki_administracyjne.zip
unzip -o 00_jednostki_administracyjne.zip -d prg
ls prg                                  # znajdź warstwę gmin (nazwa niezweryfikowana, zwykle A03_*)
ogrinfo -so prg/<warstwa_gmin>.shp <warstwa_gmin>   # sprawdź układ i nazwy pól
ogr2ogr -f GeoJSON -t_srs EPSG:4326 gminy.geojson prg/<warstwa_gmin>.shp
```
Sprawdzenia przed importem:
- `ogrinfo` pokazuje układ PL-1992 (EPSG:2180) → konwersja `-t_srs EPSG:4326` jest konieczna; importer
  odrzuci plik nie-WGS84.
- Pole z kodem TERYT ma 7 cyfr jako tekst; jeśli nazywa się inaczej niż domyślne, podaj
  `--teryt-field` i `--name-field`.

```
docker compose cp data/gminy.geojson api:/tmp/gminy.geojson
docker compose exec api python -m app.connectors.prg_gminy.ingest --file /tmp/gminy.geojson --validate-only
docker compose exec api python -m app.connectors.prg_gminy.ingest --file /tmp/gminy.geojson
```
Oczekiwane: około 2,5 tys. rekordów. Import jest idempotentny. NIE używaj `--retire-missing` przy
pierwszym imporcie.

## Weryfikacja po imporcie
1. Siedem miast z seedów zachowuje id, slug i nazwę, i dostaje granicę (ich kody TERYT są z migracji
   `0016`; jeśli któryś kod nie występuje w pliku PRG, importer przypisze miasto po punkcie w wielokącie).
2. `POST /api/v1/geo/resolve` dla współrzędnych znanego miejsca zwraca właściwą gminę (sprawdź kod w TERC;
   centrum Wrocławia powinno dać `0264011`).
3. `python3 infrastructure/scripts/smoke_data.py wroclaw` — dalej same OK.
4. `GET /api/v1/areas` nadal zwraca tylko miasta z seedów (lista „Większe miasta” w aplikacji bez zmian).

## Odtworzenie
Dane nie są w repo i nie są sekretem; plik i wynik `ogr2ogr` można odtworzyć z tego samego URL. Przy
błędzie: popraw plik i uruchom import ponownie (idempotentny).
