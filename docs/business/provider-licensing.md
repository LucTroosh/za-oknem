# Licencje dostawców danych — rekord biznesowy

Tu trzymamy fakty prawno-handlowe, które NIE są konfiguracją aplikacji (nie trafiają do env ani
do kodu). Źródło prawdy dla wdrożenia: `docs/data/source-registry.md`; decyzje: `docs/architecture/ADR-*.md`.

## Open-Meteo (OpenMeteo GmbH) — pisemne potwierdzenie

| Pole | Wartość |
|---|---|
| Dostawca | OpenMeteo GmbH |
| Forma | Bezpośrednia korespondencja pisemna z właścicielem projektu (relacja właściciela) |
| Data korespondencji | **UNKNOWN — uzupełnić** (właściciel; nie wymyślamy daty) |
| Identyfikator wątku / zgłoszenia | **UNKNOWN — uzupełnić** (jeśli istnieje) |
| Gdzie jest oryginał | **UNKNOWN — uzupełnić** (poza repo; nie commitować korespondencji ani danych kontaktowych) |
| Zapis w repo | 2026-10-02, ADR-031 |

Treść potwierdzenia (streszczenie, jak przekazał właściciel):

- Całkowicie darmowa aplikacja Za Oknem może używać Free API.
- Prowadzenie aplikacji przez zarejestrowaną JDG samo w sobie nie wymaga planu komercyjnego,
  dopóki aplikacja jest darmowa i bez reklam.
- Dobrowolne darowizny (np. Patronite) są dozwolone na Free API.
- Reklamy czynią użycie komercyjnym.
- Płatne/premium funkcje czynią użycie komercyjnym, nawet jeśli same dane pozostają darmowe.
- Architektura Open-Meteo → zaplanowany fetch backendu → storage/cache → API Za Oknem → wielu
  użytkowników jest jawnie dozwolona (okresowe pobieranie, przechowywanie ostatnich danych/prognozy,
  serwowanie wielu użytkownikom).
- Po komercjalizacji odpowiedni jest plan Standard dla tej architektury.

### Oferta handlowa (nie konfiguracja aplikacji)

- 50% rabatu na **pierwszy rok** planu komercyjnego, oferta **ważna 6 miesięcy**.
- Data oferty i termin wygaśnięcia: **UNKNOWN — uzupełnić** (z korespondencji). Dopóki nie ma daty, nie
  zakładamy, że oferta nadal obowiązuje; sprawdzić z dostawcą przed decyzją o planie.
- Cena planu Standard: nadal NIEZWERYFIKOWANA w repo (nie przyjmować kwot z blogów jako fakt).

### Konsekwencje dla wydania

Reklamy i funkcje premium wymagają planu komercyjnego **przed** włączeniem —
`docs/release/business-gates.md`. Patronite/darowizny: dozwolone na Free, ale każde włączenie
monetyzacji to nadal decyzja właściciela.
