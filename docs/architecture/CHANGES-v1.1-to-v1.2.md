# Zmiany względem Development Master Plan v1.1

Ten dokument opisuje ustalenia z rozmowy, które trzeba wnieść do Master Planu jako
v1.2 (numer wersji + wpis w historii zmian w samym dokumencie, zgodnie z Twoją zasadą
iterowania wersji zamiast cichego nadpisywania). Master Plan v1.1 zostaje nietknięty
na Drive; to jest lista delt do ręcznego wklejenia albo do wskazania mi "rób pełny v1.2"
i wtedy wygeneruję cały dokument na nowo.

## 1. Architektura danych pogodowych i pyłkowych (nowa sekcja / uzupełnienie §35, §55, §106)

Dodać odwołanie do **ADR-001**: mobile API nigdy nie woła Open-Meteo/CAMS bezpośrednio.
Dane są pobierane przez scheduler jako snapshot per gmina (nie per użytkownik, nie
cała siatka współrzędnych) i czytane z Postgresa. Zasięg pobierania (liczba aktywnych
gmin) jest konfigurowalny i rośnie wraz z bazą użytkowników.

## 2. Push i obserwowany obszar (uzupełnienie §66, §50)

Dodać odwołanie do **ADR-002**: `devices` przechowuje `observed_area_code` (TERYT),
nie surowe współrzędne GPS. Aktualizacja tylko przy foreground/ręcznej zmianie
lokalizacji. Endpointy przyjmujące współrzędne w celu wyznaczenia TERYT nie logują
pełnych współrzędnych w standardowych logach.

## 3. Dostawca pogody i licencja (uzupełnienie §106, §109, nowe w §38)

Dodać odwołanie do **ADR-003**: Open-Meteo na darmowym, niekomercyjnym tierze, dopóki
aplikacja jest bezpłatna, bez reklam, bez subskrypcji i **bez Patronite ani innej formy
stałego wsparcia finansowego**. Jakakolwiek z tych trzech rzeczy wymaga rewizji ADR-003
PRZED włączeniem, nie po.

## 4. Pyłki / CAMS jako osobne źródło (doprecyzowanie §106 MVP)

"CAMS pollen / odpowiednie źródło" → **Copernicus Atmosphere Data Store (ADS)
bezpośrednio**, nie przez Open-Meteo. Osobny connector `cams` o innym kształcie niż
connectory "zapytanie per punkt" (pobranie wycinka NetCDF/GRIB dla Polski raz dziennie).
Wpis startowy w Source Registry już przygotowany (`docs/data/source-registry.md`).

## 5. Google Play account (doprecyzowanie §88, §89)

**Personal**, nie Organization — decyzja podjęta, bo publikacja odbywa się na razie
jako osoba prywatna / projekt social-impact, a nie jako komercyjny produkt JDG.
Konsekwencja: obowiązuje wymóg zamkniętego testu — min. 12 testerów przez min. 14
kolejnych dni przed dostępem do produkcji (bez zmian względem tego, co już było w
dokumencie, tylko teraz jest to jawnie przesądzone, nie "do rozważenia").

**Uwaga do sprawdzenia później (nie blokuje developmentu):** jeśli w przyszłości konto
zostanie przeniesione na Organization/JDG, sprawdzić warunki transferu package name
i aplikacji między kontami Play — nie sprawdzone w tej rozmowie.

## 6. Platformy — kolejność, nie zmiana decyzji (doprecyzowanie §123, §107)

Android + iOS zostają jako platformy docelowe (bez zmian w tabeli §123). Doprecyzowanie
kolejności: **Android pierwszy w praktyce** — kod od początku pisany iOS-safe (bez
bibliotek blokujących iOS), ale build i closed testing na iOS zaczynamy równolegle do
lub tuż po rozpoczęciu 14-dniowego okresu closed testingu na Androidzie, nie wcześniej.
To nie zmienia żadnego z Phase 0–19, tylko harmonogram równoległości.

## 7. Co NIE zostało zmienione

Wszystkie pozostałe sekcje (Product Principles, MVP scope, architektura systemu,
modular monolith, connector contract, alert/notification separation, testing strategy,
release gates, 20 kluczowych zasad w §124) zostają bez zmian. Numer wersji dokumentu:
**v1.1 → v1.2**, data: dzisiejsza, status: nadal FINAL / SOURCE OF TRUTH.

---

**Otwarte, świadomie odłożone (nie blokują Task 0.1):**
- Dokładna cena i decyzja "kiedy realnie przejść na płatny plan Open-Meteo" —
  odłożona do momentu rozważania monetyzacji (ADR-003, Trigger).
- Data Dictionary v1.3 z kolumną `release` (v0.1/v0.2/Future) — do zrobienia jako
  osobny task, nie blokuje repo foundation ani vertical slice GIOŚ→PM2.5 (GIOŚ nie
  zależy od Open-Meteo/CAMS).
- Dokładny rate limit i pełna specyfikacja techniczna CAMS ADS — do zweryfikowania
  przed Phase 8 (Pollen), nie przed Task 0.1.
