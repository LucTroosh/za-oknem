# Za Oknem — uruchomienie i test aplikacji mobilnej na telefonie

Praktyczna ściąga (TASK „instrukcja uruchomienia”). Szczegóły backendu i ingestu: [`README.md`](../../README.md).
Stan weryfikacji na urządzeniu: [`docs/ROADMAP.md`](../ROADMAP.md). Ta instrukcja niczego nie obiecuje ponad to, co jest sprawdzone.

## 1. Wybierz backend (`EXPO_PUBLIC_API_URL`)

Aplikacja czyta WYŁĄCZNIE z naszego API (reguła #14). Adres jest wypiekany w bundlu przy starcie (`apps/mobile/.env.example`).

| Scenariusz | Adres | Uwagi |
|---|---|---|
| Emulator Androida + backend lokalnie | `http://10.0.2.2:8000` | `10.0.2.2` = komputer-gospodarz |
| Fizyczny telefon + backend lokalnie | `http://<LAN-IP komputera>:8000` | ta sama sieć Wi-Fi; `localhost` na telefonie to telefon |
| Backend na VPS | adres Twojej instancji (HTTPS za Caddy) | adresu VPS nie ma w repo (zero sekretów/hostów); jeśli dev build ma łączyć się z VPS, ustaw go w env builda |

Po zmianie zmiennej: `npx expo start -c` i całkowite zamknięcie aplikacji (zmienna jest inlinowana w bundlu).
Szybki test sieci: otwórz adres API w przeglądarce telefonu (`/api/v1/health` → `{"status":"ok"}`).

### Backend lokalnie (minimum, żeby ekrany miały dane)

```bash
cp .env.example .env && docker compose up --build -d
cd apps/api && uv sync --dev && uv run alembic upgrade head
python -m app.connectors.open_meteo.ingest
python -m app.connectors.gios.ingest --list   # potem --station-id <id>
python -m app.connectors.imgw_hydro.ingest
python -m app.connectors.imgw_warningshydro.ingest
docker compose exec api python -m app.connectors.geonames_places.ingest --download   # wyszukiwarka miejscowości
```

Bez importu GeoNames wyszukiwarka zwraca „Nie znaleziono…”, ale lista „Większe miasta” (`/areas`) działa.
Brak danych dla któregoś źródła = ekran pokazuje „niedostępne”, nigdy „wszystko OK” (reguła #8).

## 2. Expo Go czy dev build?

| | Expo Go | Dev build (`npx expo run:android` / EAS development) |
|---|---|---|
| Szybki start, logika, układ ekranów | tak | tak |
| **Ikona launchera, adaptive/monochrome, splash** | **nie widać** (to ikona Expo Go) | tak |
| Wersja | musi zgadzać się z SDK 52 ([link](https://expo.dev/go?sdkVersion=52&platform=android&device=true)) | własna, niezależna od Sklepu Play |
| Wymaga | telefonu + Wi-Fi | Android SDK/JDK lub konta EAS |

Zasada: **układ i zachowanie testuj w Expo Go, wygląd natywny (ikona, splash) wyłącznie w buildzie natywnym.**

## 3. Reset do pierwszego uruchomienia

Wybór lokalizacji jest tylko na urządzeniu (AsyncStorage). Żeby zobaczyć Welcome od zera: Android → Ustawienia → Aplikacje
→ (Expo Go albo Za Oknem) → Pamięć → Wyczyść dane.

## 4. Co przetestować ręcznie (lista kontrolna)

1. Welcome → „Zaczynamy” → wybór miejscowości → Start. Powrót (Back) z pickera nie wraca do Welcome.
2. Tryb samolotowy → Start/Alerty pokazują błąd z ilustracją „offline” i „Spróbuj ponownie”; po włączeniu sieci odświeżenie działa.
3. Jasny/ciemny motyw systemu (bez restartu).
4. Czcionka systemowa 130% i 200% (nic nie ucięte, przycisk osiągalny).
5. TalkBack: kolejność fokusa Welcome i Start, nagłówki, przyciski mają nazwy.
6. Alerty: brak ostrzeżeń pokazuje się TYLKO przy świeżym źródle; przy awarii źródła „Nie udało się sprawdzić ostrzeżeń”.

## 5. Czego dziś NIE zweryfikowano na urządzeniu

- Cały front był dotąd weryfikowany testami jednostkowymi i podglądem react-native-web (przybliżenie), nie na emulatorze/telefonie w CI.
- Ikona launchera (maski okrągła/squircle, motyw monochromatyczny), splash, TalkBack, skalowanie czcionek 130/200%.
- Rastry asset packu v2 czekają na instalację (PR #90).
- Zachowanie na realnych danych produkcyjnych (zależy od importu GeoNames i aktywnych źródeł).
