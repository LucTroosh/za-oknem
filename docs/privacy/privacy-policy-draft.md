# Polityka prywatności — Za Oknem (SZKIC)

> **Status: SZKIC do przeglądu właściciela.** Opisuje to, co aplikacja i backend faktycznie robią w kodzie
> (stan `main`, 2026-10-02). To nie jest porada prawna. Pola oznaczone **[UZUPEŁNIĆ]** nie wynikają z kodu i
> musi je wypełnić administrator danych. Przed publikacją w Google Play: przegląd prawny i zgodność
> z formularzem „Bezpieczeństwo danych” w konsoli Play.

**Obowiązuje od:** [UZUPEŁNIĆ]  **Wersja:** 0.1 (szkic)

## 1. Kim jesteśmy
Administratorem danych jest **[UZUPEŁNIĆ: imię i nazwisko / nazwa firmy (JDG), adres, e-mail kontaktowy]**.

## 2. Krótko
Za Oknem nie wymaga konta, nie zawiera reklam, nie śledzi lokalizacji w tle i nie profiluje użytkowników.
Aplikacja pokazuje powietrze, pogodę, pyłki, ostrzeżenia i stany rzek dla wybranej miejscowości w Polsce.

## 3. Jakie dane przetwarzamy

### 3.1 Dane zapisane tylko na Twoim telefonie
- wybrana miejscowość (jedna), wersja ustawień, wybrany motyw (jasny/ciemny/systemowy),
- informacja, że pierwsze uruchomienie (Welcome) zostało zakończone.
Nie wysyłamy tych danych na serwer jako zestawu powiązanego z Tobą. Usunięcie danych aplikacji lub jej
odinstalowanie kasuje je z telefonu.

### 3.2 Lokalizacja urządzenia (tylko na Twoje żądanie)
- Aplikacja odczytuje lokalizację **jednorazowo, gdy dotkniesz „Użyj mojej lokalizacji”**, i tylko gdy
  zezwolisz na to w systemie. Używa **przybliżonej** lokalizacji; dokładna lokalizacja, lokalizacja
  w tle i usługi pierwszoplanowe są zablokowane w aplikacji.
- Współrzędne są wysyłane **jednorazowo** na nasz serwer (`POST`, w treści żądania, nie w adresie), który
  zwraca najbliższą miejscowość. **Serwer nie zapisuje współrzędnych w bazie** i aplikacja nie zapisuje
  ich na telefonie; zapamiętujemy wyłącznie miejscowość, którą wybierzesz.
- Możesz zawsze wpisać miejscowość ręcznie i nie udzielać zgody na lokalizację.

### 3.3 Dane techniczne połączenia z naszym serwerem
Aplikacja łączy się wyłącznie z naszym serwerem (nie z zewnętrznymi dostawcami danych). Jak każdy serwer,
widzi **adres IP** i czas żądania. Adres IP jest używany do ograniczania nadużyć (limit żądań aktywacji
miejscowości, przechowywany w pamięci procesu, nie w bazie). Treść wyszukiwania miejscowości nie jest
zapisywana przez aplikację backendu. **[UZUPEŁNIĆ: czy serwer WWW / hosting zapisuje logi dostępu, jak
długo je przechowuje i na jakiej podstawie — zależy od konfiguracji wdrożenia (VPS/Caddy), której jeszcze
nie ma.]**

### 3.4 Czego NIE zbieramy
konta i loginy, imię, e-mail, numer telefonu, identyfikatory reklamowe, dane do analityki lub raportów
awarii (w kodzie aplikacji nie ma takich bibliotek), historia lokalizacji, kontakty, zdjęcia, mikrofon.

### 3.5 Powiadomienia push
Obecna wersja aplikacji **nie wysyła ani nie rejestruje** powiadomień push. Jeśli w przyszłości je
dodamy, opiszemy to tutaj i poprosimy o osobną zgodę przed pierwszym użyciem.

## 4. Skąd pochodzą dane, które widzisz
Dane środowiskowe pobiera nasz serwer od instytucji i dostawców, nie Twój telefon: GIOŚ (jakość powietrza),
IMGW-PIB (stany rzek, ostrzeżenia hydrologiczne), Open-Meteo / CAMS Copernicus (pogoda, prognoza, pyłki),
GeoNames (nazwy miejscowości; CC BY 4.0). Szczegóły i atrybucje: ekran „Źródła” w aplikacji.
Oceny w aplikacji mają charakter orientacyjny i nie zastępują oficjalnych komunikatów.

## 5. Podstawy prawne i cele (RODO)
- dostarczenie funkcji aplikacji (art. 6 ust. 1 lit. b lub f RODO — **[UZUPEŁNIĆ po przeglądzie prawnym]**),
- jednorazowe użycie lokalizacji — Twoja zgoda w systemie (art. 6 ust. 1 lit. a), możliwa do cofnięcia
  w ustawieniach telefonu,
- bezpieczeństwo i ograniczanie nadużyć (adres IP) — prawnie uzasadniony interes (art. 6 ust. 1 lit. f).

## 6. Odbiorcy i transfery
Dane techniczne (adres IP) widzi dostawca hostingu serwera **[UZUPEŁNIĆ: nazwa i kraj hostingu po wyborze VPS]**.
Nie sprzedajemy danych i nie udostępniamy ich reklamodawcom. Dostawcy danych środowiskowych (rozdz. 4) nie
otrzymują od nas żadnych danych o użytkownikach: backend pobiera dane dla miejscowości, nie dla osób.

## 7. Jak długo przechowujemy
- ustawienia na telefonie: do czasu ich usunięcia lub odinstalowania aplikacji,
- współrzędne lokalizacji: nie zapisujemy,
- logi dostępu serwera: **[UZUPEŁNIĆ okres]**.

## 8. Twoje prawa
Masz prawo dostępu do danych, sprostowania, usunięcia, ograniczenia przetwarzania, sprzeciwu oraz skargi do
Prezesa Urzędu Ochrony Danych Osobowych. Ponieważ nie prowadzimy kont, zwykle nie jesteśmy w stanie
powiązać żądania z konkretną osobą; napisz na **[UZUPEŁNIĆ e-mail]**.

## 9. Dzieci
Aplikacja nie jest skierowana do dzieci poniżej 16 lat i nie zbiera danych umożliwiających ich identyfikację.

## 10. Zmiany
O zmianach poinformujemy w aplikacji i na tej stronie; zmiana wersji i daty na górze.

## Lista kontrolna do publikacji (dla właściciela)
- [ ] Wypełnione pola **[UZUPEŁNIĆ]** (administrator, kontakt, hosting, logi serwera, podstawy prawne).
- [ ] Opublikowana pod stałym adresem https (wymóg Google Play) i podlinkowana w karcie sklepu oraz w ekranie
      „Prywatność” aplikacji.
- [ ] Formularz „Bezpieczeństwo danych” w Google Play zgodny z rozdz. 3 (lokalizacja przybliżona, zbierana
      opcjonalnie, nieprzechowywana; brak kont, reklam, analityki).
- [ ] Ekran „Prywatność” w aplikacji (`app/(tabs)/privacy.tsx`) spójny z tym dokumentem.
- [ ] Przegląd prawny.
