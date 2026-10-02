# Za Oknem — przegląd dostępności (TASK-12.19)

Stan kodu `apps/mobile` na dzień przeglądu. To przegląd **kodu i testów**, nie testów na urządzeniu: punkty
„do sprawdzenia na telefonie” nie są zweryfikowane.

## Co jest sprawdzone (kod / testy)

| Obszar | Wynik | Dowód |
|---|---|---|
| Kontrast tekstu ≥ 4.5:1 (WCAG AA) | każda używana para tekst/tło w obu paletach | `lib/theme.test.ts` (`TEXT_PAIRS`); Welcome na scrimie: `lib/welcome.test.ts` (PR #90) |
| Minimalny dotyk 44 dp | wszystkie `Pressable` mają `minHeight`/`MIN_TOUCH` (przyciski, karty, wiersze, „Wróć”, przełącznik motywu) | przegląd kodu (`grep Pressable`), stała `MIN_TOUCH` |
| Role i etykiety | wszystkie interaktywne elementy mają `accessibilityRole`; przyciski nazwane; nagłówki sekcji z `accessibilityRole="header"`; stan rozwinięcia (`expanded`) i wybór (`selected`) ustawiane | przegląd kodu |
| Kolor nigdy jako jedyny nośnik | status = glif + słowo + kolor (werdykt, świeżość, alerty, stany rzek, wybór motywu = ptaszek + wypełnienie) | przegląd kodu |
| Skalowanie czcionek (Dynamic Type) | brak stałych wysokości na tekście, brak `numberOfLines`, `allowFontScaling` nie jest wyłączane; rozmiary w `typo` skalują się z ustawieniem systemu | przegląd kodu; podgląd rnw ×1,3 i ×2 Welcome (symulacja, nie urządzenie) |
| Reduce Motion | aplikacja nie ma własnych animacji (brak `Animated`/`LayoutAnimation`/Reanimated), szkielety są statyczne; pozostają tylko systemowe `ActivityIndicator` i `RefreshControl` | `grep` po `app/`, `components/`, `lib/` |
| Wybór motywu | Systemowy (domyślny) / Jasny / Ciemny zapisany lokalnie; „Systemowy” zdejmuje nadpisanie i dalej podąża za systemem; zły zapis ⇒ „Systemowy” | `lib/theme.test.ts`, `lib/location.test.ts` |
| Własne przełączniki dostępności | brak (system daje Dynamic Type i Reduce Motion), więc ich nie dodano | decyzja zgodna z TASK-12.19 |

## Do sprawdzenia ręcznie na urządzeniu (NIEzweryfikowane)

1. **TalkBack**: kolejność fokusa na Start / Alerty / szczegółach / Ustawieniach; czy karty czytają się jako jedno zdanie sensownie; grupa „Wygląd” czytana jako lista opcji z zaznaczoną.
2. **Rozmiar czcionki systemowej 130% i 200%** na wszystkich ekranach (nie tylko Welcome): brak ucięć, przyciski osiągalne.
3. **Usuń animacje** (Reduce Motion) – potwierdzić brak ruchu poza systemowym spinnerem.
4. **Zmiana motywu na żywo**: „Systemowy” + przełączenie jasny/ciemny w systemie bez restartu; „Jasny”/„Ciemny” przy odwrotnym motywie systemu (pasek stanu, klawiatura, ekran odświeżania).
5. Duże i małe szerokości ekranu.

## Znane ograniczenia

- Nadpisanie motywu działa przez `Appearance.setColorScheme`; w podglądzie webowym (react-native-web) nie zmienia schematu, więc tam sprawdzono tylko zapis wyboru i układ.
- `StatusBar` jest liczony z efektywnego schematu (jasne ikony na ciemnym tle), niezweryfikowane na urządzeniu.
