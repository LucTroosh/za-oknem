# Za Oknem — Production component & iconography spec v1

This supplements `docs/ui/production-ui-v1.md`.
The approved mockup is the visual reference. Unsupported mockup features remain out of scope.

## 1. Icon strategy

We already have enough vector icon coverage for the production UI.

Use the existing Expo vector icon package already available in the mobile app.
Prefer **Ionicons consistently** for functional UI so we do not mix visual languages.

Do not generate bitmap icons for:
- navigation
- weather conditions
- activity rows
- settings
- metrics
- chevrons
- alerts
- status tiles

Custom image assets are reserved for:
- Welcome hero photography
- brand mark
- approved state illustrations
- optional future editorial/hero artwork

### Required icon roles

Use the closest valid Ionicons glyph available in the installed Expo SDK and verify the actual name at implementation time.

Navigation / actions:
- Start: home
- Alerty: notifications
- Ustawienia: settings
- back: chevron-back
- forward: chevron-forward
- location: location
- search: search

Domains:
- air: leaf
- weather: partly-sunny / sunny
- pollen: flower
- UV: sunny
- alerts: warning / notifications

Weather:
- sunny
- partly-sunny
- cloudy
- rain
- thunderstorm
- snow
- wind
- thermometer
- water / droplet
- eye / visibility

Activities:
- walk
- bicycle
- home
- trail / outdoor: use a valid nature/footsteps alternative from the installed set

Settings:
- location
- color-palette / contrast equivalent
- accessibility
- shield / lock
- server / database equivalent
- information-circle

Status semantics:
- good: checkmark-circle
- caution: alert-circle
- bad: warning
- unknown: help-circle

### Icon containers

Primary/domain icon container:
- 36 x 36 dp
- radius 12
- tinted semantic background
- icon 20–22 dp

Hero status icon:
- 48–56 dp container
- icon 30–34 dp

Settings row icon:
- 36 x 36 dp
- radius 10
- icon 20 dp

Tab icon:
- 22–24 dp

Never use color as the only status signal.

## 2. Start screen exact composition

Horizontal screen padding: 16 dp.

Vertical order:

```
SafeArea
└─ ScrollView
   ├─ HomeHeader
   ├─ HeroVerdict
   ├─ QuickStatusGrid
   ├─ ActivityRecommendations [only when real logic exists]
   ├─ AlertPreview [conditional]
   └─ SecondarySections
BottomTabBar
```

Section gaps:
- header -> hero: 16
- hero -> quick status: 12
- quick status -> next section: 24
- section heading -> content: 10–12

## 3. Home header

Height should feel compact, not like a card.

Left:
- location 22–24 px, bold
- chevron
- date 12–13 px

Right:
- current temperature 22–24 px, bold
- optional weather icon 22 px
- high/low 12 px

No enclosing white card.
No border.

## 4. Hero verdict card

Target visual footprint:
- full content width
- radius: 24
- min height: 150 dp
- padding: 18–20
- no hard border
- subtle elevation
- semantic tinted gradient or soft solid background

Layout:

```
[status icon]  HEADLINE
               supporting copy

[clock icon] Best-time / important secondary line    >
```

Headline:
- 22–24 px
- weight 800
- max 2 lines

Supporting:
- 13–14 px
- max 2 lines

Secondary strip:
- height 44–48
- background: translucent white / elevated neutral
- radius 14–16
- shown only when there is truthful real data for it

UNKNOWN / partial state:
do not render a grey diagnostic block with internal variable/source names.
Use human copy and a neutral icon.

## 5. Quick status grid

This is a core visual signature.

Desktop/tablet layouts are not required. Mobile behavior:

For content width >= 328 dp:
- one row of 4 equal tiles

For smaller widths:
- 2 x 2 grid

Gap:
- 8 dp

Tile:
- flex: 1
- min height: 108 dp
- radius: 18
- padding: 10–12
- subtle shadow
- no visible hard border in light mode

Content:
1. domain icon container 30–34
2. label 11–12 semibold
3. strong value 16–18 bold
4. supporting value 10–11

Example:

```
[leaf]
Powietrze
Dobre
PM2.5 12 µg/m³
```

Use real semantic background accents:
- air: green tint
- weather: warm yellow tint
- pollen: light green tint
- UV: amber tint
- unavailable: neutral tint

If a domain has no production source, omit the tile rather than faking content.

## 6. Section headers

```
Co możesz dziś robić?             Zobacz szczegóły >
```

Heading:
- 18 px / 24
- 700

Action:
- 12–13 px
- accent
- only show when it has a real destination

## 7. Activity rows

Only render when production recommendation logic exists.

Container:
- white/elevated surface
- radius 18
- rows separated by subtle divider OR individual compact cards
- do not use four large full-width cards with large empty padding

Row:
- min height 60
- horizontal padding 12–14
- icon container 36
- text column
- optional status badge
- chevron

Text:
title 14–15 semibold
support 12–13 secondary

## 8. Alerts preview on Start

Use one concise preview card.

High-priority:
- soft danger tint
- 16–18 px title
- source + timestamp as meta
- one actionable sentence
- CTA to Alerty

Do not show nationwide alert counts as the dominant top content unless directly relevant to the current user location.

## 9. Weather detail visual structure

```
PageHeader
SegmentedControl [only supported ranges]
CurrentWeatherHero
HourlyStrip
MetricGrid
InterpretationCard
SourceMeta
```

Current hero:
- large weather glyph: 48–64
- temperature: 40–44 px / bold
- condition: 14–15
- high/low: 12–13

Hourly strip:
- horizontal
- cell width 54–64
- no enclosing giant card
- each: time / icon / temp

Metric grid:
- 2 columns
- gap 8
- tile min height 82
- icon 20
- label 11–12
- value 15–17 bold

## 10. Air detail visual structure

Top status card:
- icon container 56
- human status headline
- index line
- optional real scale bar

Pollutant metrics:
- 3 columns when width permits, otherwise 2
- compact tile
- pollutant name 11–12
- value 16 bold
- unit 10–11

Interpretation:
separate soft-tint card titled:
"Co to oznacza?"

Keep source and methodology below, visually secondary.

## 11. Pollen detail visual structure

Top:
- flower icon
- risk headline
- index if actual

Tabs/segments only when backed by real ranges.

Taxa list:
compact rows:
- small plant/flower glyph
- taxa
- risk label on right
- optional mini status dot PLUS text

Calendar CTA/section:
secondary, visually distinct from current forecast.

## 12. Alerts feed

Each alert item:
- radius 18
- padding 14
- gap 8
- semantic icon container 36
- source meta 11
- headline 15–16 bold
- scope 13
- validity 12
- freshness badge

Use one card per alert or grouped surface with clear separators.
Avoid long continuous text blocks.

Priority ordering remains:
1. local
2. unresolved
3. rest of Poland

## 13. Settings exact row style

Settings top-level is a clean list, not large paragraphs.

Section surface:
- white/elevated
- radius 20
- overflow hidden

Row:
- min height 64
- padding H 14–16
- icon container 36
- title 15 semibold
- optional secondary value 12–13
- trailing chevron

Rows:
- Lokalizacja
- Wygląd
- Dostępność
- Prywatność
- Źródła danych
- O aplikacji

Long copy must live on detail screens/subpages, not in top-level Settings.

## 14. Location exact layout

Top:
- optional 96–120 dp illustration
- title 28 bold
- supporting 14

Search:
- height 52
- radius 16
- search icon left
- clear affordance right when text exists

City/location row:
- min height 56
- icon 20 in subtle container
- title 15–16
- secondary status only if real
- checkmark for active
- divider or grouped surface

Do not render every city as a giant standalone card.

## 15. Card/shadow implementation

Light:
- surface #FFFFFF
- shadow opacity ~0.06–0.10
- blur/radius 12–18
- Android elevation 2–4

Dark:
- use elevated surfaces and minimal/no shadow

Avoid visible medium-grey outlines unless needed for contrast.

## 16. Responsive rules

At 320–339 dp width:
- quick status grid becomes 2x2
- metric grids become 2 columns
- long section actions may move below heading

At >=340 dp:
- quick status may use 4 columns if labels remain readable

At 200% font scale:
- tiles can grow vertically
- never clip status values
- allow 2-line labels where necessary

## 17. Production fidelity requirement

The implementation should be reviewed visually against the approved mockup for:
- density
- hierarchy
- card proportions
- whitespace
- icon size
- status color treatment
- border/shadow subtlety

The goal is not pixel-perfect copying of unsupported screens.
The goal is to make every **in-scope** screen feel like it belongs to the same polished product as the approved mockup.
