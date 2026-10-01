# ADR-027: StyleSheet + design tokens zamiast NativeWind w MVP

- **Date:** 2026-10-01
- **Status:** Accepted

## Context

CLAUDE.md wymienia w stacku mobilnym NativeWind, ale pakiet nie jest zainstalowany w
`apps/mobile/package.json`; dotychczasowy UI używał gołego `StyleSheet` z twardymi kolorami.
PR „fundament UI” dodaje jasny/ciemny motyw, nawigację i komponenty współdzielone.

## Problem

Czym stylować UI w MVP, skoro reguła #12 wymaga ADR przy zmianie stacku, a reguła „bez
nowych zależności bez uzasadnienia” (CLAUDE.md) zniechęca do dokładania Tailwind/NativeWind
(plugin Babel, konfiguracja Metro, `tailwind.config`, wersje zależne od SDK)?

## Options

1. **NativeWind** — zgodne z zapisem w stacku; nowe zależności (nativewind, tailwindcss,
   preset Babel/Metro), większe ryzyko niezgodności z Expo SDK 52, trudniejsze testowanie
   kontrastu (kolory w klasach).
2. **`StyleSheet` + tokeny w czystym TS** (`lib/theme.ts`, hook `useTheme`) — zero zależności,
   palety jako dane, kontrast sprawdzany testem jednostkowym w obu motywach.
3. Biblioteka UI (Paper, Tamagui) — duża zależność i własny język wizualny.

## Decision

Opcja 2 na czas MVP: `StyleSheet` + tokeny (`lib/theme.ts`: kolory semantyczne jasny/ciemny,
typografia, odstępy, promienie) + `useThemedStyles`. Żadnych twardych kolorów poza `theme.ts`.
NativeWind pozostaje opcją po MVP — migracja jest mechaniczna, bo wartości są w tokenach.
Zapis o NativeWind w CLAUDE.md zostaje bez zmian do decyzji właściciela (ten ADR go nie edytuje).

## Consequences

- Brak nowych zależności; kontrast ≥ 4.5:1 wszystkich użytych par tekst/tło łapie
  `lib/theme.test.ts`.
- Style są obiektami JS, więc brak utility-klas i brak wspólnego z webem języka stylów.
- Przyszła migracja na NativeWind wymaga osobnego ADR i przepisania `createStyles` w komponentach.
