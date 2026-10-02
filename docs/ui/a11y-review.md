# Za Oknem — przegląd dostępności (TASK-12.19, odświeżony po production-ui-v1, PR #102–#117)

Stan kodu `apps/mobile` na dzień przeglądu. To przegląd **kodu i testów**, nie testów na urządzeniu: punkty
„do sprawdzenia na telefonie” nie są zweryfikowane.

## Co jest sprawdzone (kod / testy)

| Obszar | Wynik | Dowód |
|---|---|---|
| Kontrast tekstu ≥ 4.5:1 (WCAG AA) | każda używana para tekst/tło w obu paletach | `lib/theme.test.ts` (`TEXT_PAIRS`); Welcome na scrimie: `lib/welcome.test.ts` (PR #90) |
| Minimalny dotyk **48 dp** | każdy z 15 plików z `Pressable` ustawia wysokość ≥ 48 (`MIN_TOUCH = 48`; przyciski i pola 52, wiersze 56–64, karty 72+, CTA Welcome 52, pozycje paska zakładek 48; „Wstecz” 48 dp, `hitSlop` tylko jako dodatek) | przegląd kodu (`grep Pressable`/`minHeight`), `lib/theme.ts` |
| Role i etykiety | wszystkie interaktywne elementy mają `accessibilityRole`; przyciski nazwane; nagłówki sekcji z `accessibilityRole="header"`; stan rozwinięcia (`expanded`) i wybór (`selected`) ustawiane | przegląd kodu |
| Kolor nigdy jako jedyny nośnik | status = glif + słowo + kolor (werdykt, świeżość, alerty, stany rzek, wybór motywu = ptaszek + wypełnienie) | przegląd kodu |
| Skalowanie czcionek (Dynamic Type) | brak stałych wysokości na tekście, brak `numberOfLines`, `allowFontScaling` nie jest wyłączane; rozmiary w `typo` skalują się z ustawieniem systemu | przegląd kodu; podgląd rnw ×1,3 i ×2 Welcome (symulacja, nie urządzenie) |
| Reduce Motion | aplikacja nie ma własnych animacji (brak `Animated`/`LayoutAnimation`/Reanimated), szkielety są statyczne; pozostają tylko systemowe `ActivityIndicator` i `RefreshControl` | `grep` po `app/`, `components/`, `lib/` |
| Wybór motywu | Systemowy (domyślny) / Jasny / Ciemny zapisany lokalnie; „Systemowy” zdejmuje nadpisanie i dalej podąża za systemem; zły zapis ⇒ „Systemowy” | `lib/theme.test.ts`, `lib/location.test.ts` |
| Własne przełączniki dostępności | brak (system daje Dynamic Type i Reduce Motion), więc ich nie dodano | decyzja zgodna z TASK-12.19 |

## Zmiany po przebudowie UI (stan kodu na `main`)

- **Tab bar** (Start / Alerty / Ustawienia): etykieta to własny `Text` z `maxFontSizeMultiplier={2}`, jedna linia i
  `adjustsFontSizeToFit` (min. 0,6), a wysokość paska rośnie z `fontScale`. Przy 200% fontu etykieta może się
  zmniejszyć, żeby zmieścić się w 1/3 szerokości (zamiast być ucięta) — do oceny na urządzeniu.
- **Nagłówek Startu** (`HomeHeader`): nazwa miejscowości ma `numberOfLines={2}` (długie „Miejscowość, pow. …” może
  zostać skrócona wizualnie przy dużej czcionce; etykieta dostępności zawiera pełny tekst). Układ zawija się
  (temperatura pod nazwą).
- **Kafelki** (`StatusTile`): etykieta `numberOfLines={2}`; liczba kolumn siatki zależy od szerokości i skali
  fontu (≥ 1,3 → 2 kolumny), wartości nie są obcinane w połowie słowa (`lib/start.ts`).
- **Welcome**: tekst natywny; kapsuła czytana jako jedna linia, ikony ukryte przed czytnikiem; przy fontcie ≥ 130%
  kapsuła 2×2. Kontrast sprawdzany testem (`lib/welcome.test.ts`) względem zmierzonych skrajnych pikseli zdjęcia
  łącznie z welonem i lokalnym scrimem; **górna granica jasności nieba to 98. percentyl, nie absolutne
  maksimum** — pojedyncze rozbłyski chmur (do ~2% pikseli strefy tekstu) mogą lokalnie spaść poniżej 4,5:1.
- **Alerty**: ikona i tło kart neutralne; stopień IMGW pokazywany tekstem (ADR-009), bez własnej skali kolorów;
  „Dotyczy Twojej lokalizacji” jako osobna etykieta (nie sam kolor).
- **Nawigacja**: „Wstecz” (etykieta `Wstecz`, 48 dp) na Lokalizacji także na pierwszym uruchomieniu; po wyborze
  lokalizacji historia onboardingu jest czyszczona (`lib/navigation.ts`, testy).
- **GPS**: zgoda systemowa, tylko przybliżona lokalizacja; odmowa ma komunikat i nie blokuje ręcznego wyboru.
- Czcionka Welcome (Nunito) ładowana lokalnie; jeśli się nie załaduje, działa czcionka systemowa (bez błędu).

## Do sprawdzenia ręcznie na urządzeniu (NIEzweryfikowane)

0. **Welcome i nawigacja**: TalkBack czyta „Za Oknem” jako nagłówek, potem kapsułę jako jedną linię i CTA;
   systemowy Back z Lokalizacji wraca do Welcome, a ze Startu zamyka aplikację; „Użyj mojej lokalizacji”
   z TalkBackiem (okno zgody, wynik ogłaszany jako alert).
1. **TalkBack**: kolejność fokusa na Start / Alerty / szczegółach / Ustawieniach; czy karty czytają się jako jedno zdanie sensownie; grupa „Wygląd” czytana jako lista opcji z zaznaczoną.
2. **Rozmiar czcionki systemowej 130% i 200%** na wszystkich ekranach (nie tylko Welcome): brak ucięć, przyciski osiągalne.
3. **Usuń animacje** (Reduce Motion) – potwierdzić brak ruchu poza systemowym spinnerem.
4. **Zmiana motywu na żywo**: „Systemowy” + przełączenie jasny/ciemny w systemie bez restartu; „Jasny”/„Ciemny” przy odwrotnym motywie systemu (pasek stanu, klawiatura, ekran odświeżania).
5. Duże i małe szerokości ekranu.

## Znane ograniczenia

- Nadpisanie motywu działa przez `Appearance.setColorScheme`; w podglądzie webowym (react-native-web) nie zmienia schematu, więc tam sprawdzono tylko zapis wyboru i układ.
- `StatusBar` jest liczony z efektywnego schematu (jasne ikony na ciemnym tle), niezweryfikowane na urządzeniu.
