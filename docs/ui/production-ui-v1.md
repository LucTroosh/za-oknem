# Za Oknem — Production UI v1

Status: implementation contract
Target: production-ready mobile UI
Reference direction: approved product mockup from 2026-10-02
Scope rule: use the mockup as the visual quality bar, but omit mockup features that are not in the current product scope.

## 1. Product architecture — locked

Bottom navigation has exactly 3 tabs:
- Start
- Alerty
- Ustawienia

Do not add:
- permanent Map tab
- More tab
- Profile
- account
- saved locations
- topic/profile selection

First-run flow:
Welcome -> Lokalizacja -> Start

Returning users:
Start

There is one active location only. Location can be changed later from Start and Settings.

The app must not contain the onboarding screen "Co chcesz śledzić?".
Remove the same Topics UI from Settings.
All available domains are shown by default.

## 2. Visual target

The UI should feel:
- warm
- modern
- calm
- premium consumer product
- light and spacious
- environmental/lifestyle, not a technical monitoring dashboard
- visually coherent across every screen

Avoid:
- grey enterprise-dashboard appearance
- large walls of diagnostic text
- card-in-card-in-card layouts
- hard borders around every surface
- excessive explanatory copy
- exposing internal API/source diagnostics as primary UI
- mock data in safety-critical states

Design principle:
**answer first, data second**

The first thing the user should understand is:
1. what is happening,
2. whether conditions are good/bad,
3. what it means for them,
4. then the underlying measurements.

## 3. Design system

### Light palette

- app background: #F4F8FA
- surface: #FFFFFF
- primary text: #102A3A
- secondary text: #5E7180
- subtle text: #7E8D98
- primary teal: #087B69
- primary teal dark: #046253
- good: #3FAE52
- good background: #EAF8EA
- warning: #E89B25
- warning background: #FFF5DF
- danger: #E8554E
- danger background: #FFF0EE
- info blue: #3D8FDB
- soft border: #E4ECEF

Domain accents:
- air: #44B76E
- weather: #F6B61D
- pollen: #71B934
- alerts: #EF5B4F
- UV: #FFB52F

### Dark palette

Keep semantic relationships and WCAG AA.
Use deep blue-green backgrounds rather than pure black.
Suggested:
- bg: #0C171B
- surface: #142328
- elevated: #1A2B31
- text: #EEF5F6
- secondary: #A8BAC1
- primary teal: #5ED4BD

### Typography

Use the system font stack unless a production-safe bundled font is already approved.

- hero display: 30 / 36, weight 800
- page title: 28 / 34, weight 800
- section heading: 18 / 24, weight 700
- card title: 16 / 22, weight 700
- body: 15 / 22, weight 400
- supporting: 14 / 20, weight 400
- meta: 12 / 17, weight 500

All text must support device font scaling.

### Spacing

Base scale:
4 / 8 / 12 / 16 / 20 / 24 / 32

Screen horizontal padding:
16 px

Primary vertical section gap:
24 px

Related content gap:
8–12 px

### Radius

- hero / major cards: 24
- regular cards: 18
- compact tiles: 16
- inputs: 16
- pills/chips/buttons: 999

### Shadows

Light mode:
subtle elevation only.

Target look:
- low opacity
- large blur
- almost no visible dark outline

Do not rely on borders for card separation if shadow/background is enough.

### Touch targets

Minimum:
48 x 48 dp

## 4. Shared components to create/refactor

Create reusable production components instead of styling each screen independently.

Recommended:
- AppScreen
- PageHeader
- HeroSurface
- StatusTile
- MetricTile
- SectionHeader
- SettingsRow
- SegmentedControl
- FilterChip
- StatusBadge
- InfoBanner
- EmptyState
- StateIllustration
- PrimaryButton
- SecondaryButton
- BottomTabBar styling
- SkeletonCard
- SourceMeta

Every reusable component must support dark mode and Dynamic Type.

## 5. Welcome

Visual direction:
approved warm city + nature hero.

Use:
`apps/mobile/assets/za-oknem/backgrounds/welcome-hero-1242x2688.jpg`

Do not bake text into the image.

Hierarchy:
1. logo
2. "Za Oknem"
3. "Sprawdź, co dzieje się wokół Ciebie"
4. four domain cues:
   - Powietrze
   - Pogoda
   - Pyłki
   - Alerty
5. CTA "Zaczynamy"
6. "Bez konta. Bez profilowania."

The hero should occupy most of the screen.
Use a soft bottom fade/scrim into the CTA area.

Do not show the long supporting sentence from the current implementation if it makes the screen visually busy.

## 6. Location

Replace the current form-heavy appearance.

Header:
"Gdzie jesteś?"

Supporting:
"Wybierz lokalizację, aby pokazać aktualne warunki w Twojej okolicy."

Top:
small location illustration or branded pin asset.

Search:
large rounded search input with search icon.

If GPS support is actually implemented:
show secondary button:
"Użyj mojej lokalizacji"

If GPS is not implemented:
do not show a dead CTA.

Below:
show current / recent / suggested locations only if backed by real app state.

For the current backend city list:
render as compact rows, not large white cards.

Row:
- location pin icon
- city
- optional current-state label
- chevron or checkmark

Selecting a location in first-run onboarding must go directly to Start.

No Topics screen.

## 7. Start — primary product screen

This screen gets the highest visual priority.

Order:

### A. Header

Left:
- location name + chevron
- date

Right:
- current temperature
- optional small weather icon
- daily min/max if available

Keep it compact.

### B. Hero verdict

The hero is the main answer.

Examples:
- "Dziś warto wyjść na zewnątrz"
- "Warunki są dziś średnie"
- "Lepiej ograniczyć aktywność na zewnątrz"
- "Nie możemy jeszcze ocenić wszystkich warunków"

Use:
- large semantic icon/glyph
- 1 strong headline
- max 2 lines explanation
- optional best-time row

Do not expose internal diagnostics such as:
"brak danych: jakość powietrza (brak), NO2 (brak), O3 (brak)"
as the hero copy.

If data is incomplete:
human-facing text first.
Detailed missing-source information can appear in a secondary disclosure/details area.

For UNKNOWN:
preferred copy:
"Nie możemy jeszcze ocenić wszystkich warunków"
supporting:
"Brakuje części aktualnych danych. Dostępne informacje pokazujemy poniżej."

Do not show a disclaimer inside the hero unless legally/product-required.
Source/disclaimer text belongs lower in the screen.

### C. Quick status tiles

Use a horizontal row/grid of compact visual tiles.

Current domains:
- Powietrze
- Pogoda
- Pyłki
- UV only when production data is available

If UV is not available, do not render an empty fake tile.

Each tile:
- icon
- label
- strong value/status
- one small supporting value
- semantic tint

Examples:
Powietrze / Dobre / PM2.5 12 µg/m³
Pogoda / 16°C / Słonecznie
Pyłki / Niskie / Indeks 1.8

Cards should navigate to details if a detail screen exists.

### D. "Co możesz dziś robić?"

This is a product feature, not generic advice.

Show only if backed by production recommendation logic.
Never hardcode mock recommendations.

Preferred rows:
- Spacer
- Rower / bieganie
- Wietrzenie mieszkania
- optional additional supported outdoor activity

Each row:
- activity icon
- title
- short recommendation
- semantic status icon + text
- chevron only if there is a real detail destination

Examples:
"Świetne warunki do 18:00"
"Najlepiej przed 17:00"
"Teraz są dobre warunki"

If the recommendation engine is not production-ready, hide this section rather than using mocks.

### E. Alert preview

Only show if:
- there is a relevant warning,
- data is unavailable and that uncertainty matters,
- or a concise all-clear is genuinely justified.

Alert preview:
- icon
- source type
- one-line headline
- short actionable interpretation
- CTA to Alerty

Do not put a nationwide wall of hydrology notices on Start.

### F. Secondary details

Pollen calendar, source diagnostics and verbose data belong lower down or in detail screens.

## 8. Weather detail

Use the existing production weather data only.

Header:
back + "Pogoda"

Top:
large current temperature + icon + condition
daily high/low

If supported:
segmented control:
Dziś / Jutro / 3 dni

Hourly strip:
horizontal scroll
time + icon + temperature

Metric grid:
- opady
- wiatr
- porywy
- wilgotność
- widoczność
- apparent temperature
only when actually available.

Sunrise/sunset only if actual data exists.

Interpretation card:
one concise natural-language summary.

No invented metrics.

## 9. Air detail

Header:
back + "Powietrze"

Top hero:
- semantic leaf icon
- human label e.g. "Dobra jakość powietrza"
- CAQI/index value if available

Gradient/scale can be used only if it represents the real index scale.

Metric grid:
- PM2.5
- PM10
- NO2
- O3
- SO2
- CO
only when data exists.

Below:
"Co to oznacza?"
2–3 lines max.

Source/coverage/freshness belong below the interpretation.

## 10. Pollen

If a dedicated pollen screen is implemented:
header:
"Pyłki"

Top:
overall current risk if supported by real data.

Then:
list of taxa with status.

The seasonal calendar must be visually distinct from current forecast.
Do not imply that "outside typical season" equals "no pollen".

Keep explanatory disclaimer concise and secondary.

## 11. Alerts

The current Alert screen must be redesigned from a document/list look into a consumer alert feed.

Header:
"Alerty"

Optional filters only for categories that exist in production.

Each alert card:
- severity icon
- source (IMGW / RCB / GIOŚ etc.)
- event title
- location scope
- validity
- freshness
- chevron

High priority cards may use a soft danger tint.

Detail must distinguish:
- "Oficjalny komunikat"
- "Co to oznacza?"

Never rewrite an official alert as if the app were the source.

Do not display huge amounts of national alerts before relevant local information.

Order:
1. relevant to current location
2. unresolved / needs checking
3. other Poland-wide items, collapsed or lower priority

Empty:
"Brak aktywnych ostrzeżeń"
only if source freshness allows confirming that.

Error:
"Nie udało się sprawdzić ostrzeżeń"
must not imply all-clear.

## 12. Settings

Convert to a clean iOS/Android consumer-settings list.

Main rows:
- Lokalizacja
- Wygląd
- Dostępność
- Prywatność
- Źródła danych
- O aplikacji

Each:
left icon + title + secondary value + chevron where navigable.

Do not keep long source/license paragraphs on the top-level Settings screen.

Move long content into subpages/modals where appropriate.

Remove:
"Co chcesz śledzić?"

Theme row:
secondary value:
Systemowy / Jasny / Ciemny

Location row:
selected location

About:
version

## 13. Bottom navigation

Exactly:
- Start
- Alerty
- Ustawienia

Use Ionicons or the existing vector library.

Visual:
- white/elevated surface in light mode
- subtle top divider/shadow
- active icon + text in primary teal
- inactive in secondary gray
- icons approx 22–24
- labels 11–12, semibold
- safe-area aware

Do not add permanent Mapa or Więcej.

## 14. Copy cleanup

Rewrite technical UI copy into short user-facing language.

Examples:

Current:
"Brak oceny — brak danych: jakość powietrza (brak), NO2 (brak), O3 (brak)"

Production:
"Nie możemy jeszcze ocenić wszystkich warunków"

Current:
"Wartość z modelu dla obszaru, nie pomiar w miejscowości."

Production display:
"Prognoza dla Twojego obszaru"
and put methodology/source lower.

Current warning walls should become:
headline + relevant consequence + detail on tap.

Keep full source attribution accessible, but not dominant.

## 15. Data-state rules

AVAILABLE:
show real status.

PARTIAL:
show available information and clearly note what cannot be evaluated.

UNAVAILABLE:
"Dane chwilowo niedostępne."

EMPTY:
use domain-specific true empty message.

ALERTS EMPTY:
"Brak aktywnych ostrzeżeń"
only when confirmed from sufficiently fresh sources.

ALERT FETCH ERROR:
"Nie udało się sprawdzić ostrzeżeń."

One module failing must never blank the whole dashboard.

Use skeletons per section.
Do not use a single blocking full-screen spinner.

## 16. Accessibility

Target WCAG 2.2 AA where applicable to mobile.

Required:
- Dynamic Type
- TalkBack / VoiceOver labels
- correct focus order
- 48 dp touch targets
- no status conveyed only by color
- contrast AA
- Reduce Motion friendly
- decorative assets excluded from accessibility tree
- readable at 200% font scaling

## 17. Motion

Keep subtle:
- 150–220 ms
- opacity / small translate
- no bouncy animations for safety content
- respect Reduce Motion

No animations are required for MVP if they risk stability.

## 18. Performance

- lazy-load detail assets
- do not preload all large PNG illustrations
- keep photographic backgrounds JPEG
- avoid unnecessary re-renders in dashboard lists
- no base64 embedded images
- no remote image dependency for core UI

## 19. Current code changes required

At minimum:

### Remove Topics flow
- remove route /topics from onboarding
- update `apps/mobile/app/location.tsx` to navigate directly to Start
- remove TopicsPicker from Settings
- stop filtering Start via local topic settings
- migrate stored settings safely so old installations still open normally

### Refactor theme
Update `apps/mobile/lib/theme.ts` to the production visual tokens above while preserving semantic contrast tests.

### Refactor cards
Update:
- Card
- Button
- HomeHeader
- HeroVerdict
- StatusCards
- AlertsSection
- Settings screen
- Location screen
- tab bar

Avoid breaking data/business logic.

## 20. Out of scope

Do NOT implement merely because it appears in the visual mockup:
- permanent Map tab
- More tab
- favorites/saved locations
- user account/profile
- topic personalization
- fake GPS if GPS is not ready
- unsupported UV
- unsupported activity recommendations
- unsupported weekly forecast
- unsupported data sources

Visual quality from the mockup is in scope.
Unsupported product features are not.

## 21. Definition of Done

- [ ] first-run is Welcome -> Location -> Start
- [ ] no Topics screen
- [ ] no Topics picker in Settings
- [ ] bottom nav has exactly Start / Alerty / Ustawienia
- [ ] Welcome matches approved production direction
- [ ] Location looks like a polished consumer picker
- [ ] Start uses answer-first hierarchy
- [ ] hero diagnostic copy is human-facing
- [ ] status cards are compact premium tiles
- [ ] activity section only appears with real recommendation logic
- [ ] local alerts are prioritized
- [ ] Settings uses compact navigation rows
- [ ] air/weather detail screens share the same design system
- [ ] empty/error/offline states use approved illustrations
- [ ] light mode verified
- [ ] dark mode verified
- [ ] 200% text scaling verified
- [ ] TalkBack order verified
- [ ] no hardcoded fake environmental/safety data
- [ ] npm run lint passes
- [ ] npm run typecheck passes
- [ ] npm test passes
- [ ] APK builds successfully
- [ ] screenshots from a physical Android device are added to the PR

## 22. Required screenshots for review

Before merge attach:
1. Welcome
2. Location
3. Start with healthy/normal data
4. Start with partial/unavailable data
5. Weather detail
6. Air detail
7. Alerts with at least one real item or fixture only in a clearly-labelled dev/test build
8. Alerts empty/unavailable state
9. Settings
10. dark-mode Start
11. large-text Start

## 23. Implementation strategy

This PR should be treated as one coherent visual system, not independent styling patches.

Recommended order:
1. theme tokens + primitives
2. navigation + screen container
3. remove Topics flow
4. Welcome
5. Location
6. Start
7. detail screens
8. Alerts
9. Settings
10. state screens
11. accessibility / dark mode / screenshots / tests

Do not merge partially-restyled screens if they make the product visually inconsistent.
