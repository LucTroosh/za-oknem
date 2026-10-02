# Za Oknem — Asset Pack v2 implementation handoff

This document is the implementation contract for PR #90.

## Goal

Move the approved visual assets into the Expo mobile app and wire them into the product without introducing mock functionality or inaccessible image-based copy.

## Before merge

PR #90 is **not complete for merge** until every checkbox below is done by the implementing developer/agent.

### 1. Install the raster pack

Use the approved `za_oknem_asset_pack_v2.zip`.

Run:

```bash
python scripts/install_ui_asset_pack.py /path/to/za_oknem_asset_pack_v2.zip
```

The installer:
- validates SHA-256 checksums,
- validates image dimensions,
- copies only approved production exports,
- normalizes filenames,
- places files under `apps/mobile/assets/za-oknem/`.

Do not hand-copy alternate exports or replace the approved files with regenerated variants.

### 2. Expected runtime files

```
apps/mobile/assets/za-oknem/
  android/
    app-icon-1024.png
    adaptive-icon-foreground-1024.png
    adaptive-icon-background-1024.png
    adaptive-icon-monochrome-1024.png
    play-store-icon-512.png
  brand/
    logo-mark.svg
    logo-mark-512.png
  backgrounds/
    welcome-hero-1242x2688.jpg
  illustrations/
    condition-good.svg
    condition-caution.svg
    condition-bad.svg
    no-alerts.svg
    no-data.svg
    offline.svg
    location-required.svg
    condition-good-1200x800.png
    condition-caution-1200x800.png
    condition-bad-1200x800.png
    no-alerts-1200x800.png
    no-data-1200x800.png
    offline-1200x800.png
    location-required-1200x800.png
  asset-manifest.json
```

### 3. Expo / Android app icon configuration

Update `apps/mobile/app.json` so Expo uses the approved assets.

Required intent:

```json
{
  "expo": {
    "icon": "./assets/za-oknem/android/app-icon-1024.png",
    "android": {
      "package": "pl.zaoknem.app",
      "adaptiveIcon": {
        "foregroundImage": "./assets/za-oknem/android/adaptive-icon-foreground-1024.png",
        "backgroundColor": "#F4FAF7",
        "monochromeImage": "./assets/za-oknem/android/adaptive-icon-monochrome-1024.png"
      }
    }
  }
}
```

Keep package id, scheme, version and existing plugins unchanged.

The Play Store 512×512 file is a store-listing asset and should not be referenced by runtime code.

### 4. Welcome screen

Replace the current placeholder `partly-sunny-outline` hero in `apps/mobile/app/welcome.tsx`.

Use:
- background: `backgrounds/welcome-hero-1242x2688.jpg`,
- brand mark: `brand/logo-mark-512.png`,
- native React Native text and button components.

Approved hierarchy:

1. background image fills the screen with `cover`,
2. safe-area-aware brand mark,
3. `Za Oknem`,
4. `Sprawdź, co dzieje się wokół Ciebie`,
5. four lightweight domain cues: Powietrze / Pogoda / Pyłki / Alerty,
6. primary CTA `Zaczynamy`,
7. privacy line `Bez konta. Bez profilowania.`.

Do **not** bake any of those labels into the JPG.

The bottom of the background must receive a subtle light scrim/gradient so CTA and privacy text remain readable.

### 5. Accessibility rules for Welcome

- image background is decorative and excluded from VoiceOver/TalkBack,
- logo image has an accessibility label only if it conveys information not already announced by the adjacent `Za Oknem` text; otherwise mark it decorative,
- headline is an accessibility header,
- CTA minimum touch target 48×48 dp,
- support Dynamic Type,
- no text embedded inside bitmap assets,
- verify AA contrast on top of the hero/scrim,
- preserve the existing onboarding navigation behavior.

### 6. State illustrations

Use the SVG source illustrations where the existing stack can render them without introducing fragile dependencies.

If the project does not yet support SVG rendering:
- use the approved 1200×800 PNG fallbacks for this PR,
- create a separate follow-up only if a vector migration is justified.

Mapping:
- positive/good verdict or friendly success state → `condition-good`
- caution state → `condition-caution`
- clearly adverse conditions → `condition-bad`
- empty alerts → `no-alerts`
- API/data unavailable → `no-data`
- network offline → `offline`
- no location selected / permission flow → `location-required`

Do not use these illustrations as replacements for data or critical warning text. Critical information must remain native text.

### 7. Do not use imagery for

- bottom tab icons,
- weather glyphs,
- AQI/UV/PM metric icons,
- alert severity icons,
- buttons,
- chevrons,
- switches.

Those continue to use the single vector icon library already used by the app.

### 8. Dark mode

The photographic Welcome background stays the same.

Dark mode must adapt:
- overlay/scrim,
- native text,
- button surface,
- privacy row.

Do not create a second dark-mode JPG unless visual testing proves necessary.

### 9. Performance

- do not use the unoptimized master PNGs in runtime UI,
- use only normalized production files installed by the script,
- keep Welcome background as JPEG,
- avoid loading all state PNG fallbacks on app startup,
- only require/import assets in screens that use them.

### 10. Validation

Before marking implementation complete:

```bash
cd apps/mobile
npm run lint
npm run typecheck
npm test
```

Also run the app on Android and verify:
- launcher icon on at least one round and one squircle mask,
- monochrome/themed icon if supported by the test launcher,
- Welcome at small Android phone width,
- Welcome at large phone width,
- light mode,
- dark mode,
- font scaling at 130% and 200%,
- TalkBack focus order.

### 11. Screenshots required in the PR

Attach screenshots of:
1. launcher icon on device/emulator home screen,
2. Welcome light mode,
3. Welcome dark mode,
4. Welcome with increased font size,
5. at least one state illustration rendered in-app.

## Acceptance criteria

- [ ] all approved raster assets are present in `apps/mobile/assets/za-oknem/`
- [ ] checksums/dimensions pass the installer
- [ ] `app.json` references approved launcher/adaptive assets
- [ ] current Welcome placeholder is removed
- [ ] approved Welcome hero is used
- [ ] Welcome copy is native, not baked into the image
- [ ] privacy copy says `Bez konta. Bez profilowania.`
- [ ] current onboarding routing remains unchanged
- [ ] accessibility requirements pass manual review
- [ ] no bitmap navigation/metric icons introduced
- [ ] lint passes
- [ ] typecheck passes
- [ ] tests pass
- [ ] Android visual verification screenshots are attached
