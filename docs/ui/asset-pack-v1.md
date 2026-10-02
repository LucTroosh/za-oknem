# Za Oknem — Asset Pack v2

Final approved asset direction for the mobile app.

## Repository location
`apps/mobile/assets/za-oknem/`

## Raster delivery
The companion package is `za_oknem_asset_pack_v2.zip`.

### Android / store
- app icon master: 1024×1024 PNG
- adaptive foreground: 1024×1024 transparent PNG
- adaptive background: 1024×1024 PNG
- adaptive monochrome: 1024×1024 transparent PNG
- Google Play listing icon: 512×512 PNG

### Brand
- logo mark: 1024 / 512 / 256 PNG
- vector source: `brand/logo-mark.svg`

### Backgrounds
- Welcome hero: 1242×2688 JPEG, high quality, no baked-in logo/copy/controls
- dashboard sunny: 1242×2688 JPEG
- dashboard cloudy: 1242×2688 JPEG
- dashboard evening: 1242×2688 JPEG

Photographic assets use JPEG rather than PNG to reduce the application bundle without visible quality loss.

### State illustrations
Runtime PNG fallback size: 1200×800.
Vector source files are stored in the repository.

- condition good — open window, sun and city/nature; no decorative leaf
- condition caution — cloud/wind window composition; no decorative leaf
- condition bad — storm window + explicit warning symbol
- no alerts
- no data
- offline — large, readable Wi‑Fi-off symbol
- location required — single location pin; no decorative leaf

## Implementation rules
- Functional navigation/domain/weather icons come from one vector icon library in code.
- Do not use bitmap icons for tabs or metric cards.
- Do not bake user-facing copy into images.
- Render logo, text, scrims, buttons and controls natively.
- Never communicate state only by color.
- Respect Dynamic Type, VoiceOver/TalkBack and Reduce Motion.
- Use `cover` for full-screen photographic backgrounds.
- Android adaptive foreground and monochrome assets preserve transparency and safe-zone padding.

## Layout
```
apps/mobile/assets/za-oknem/
  android/
  brand/
  backgrounds/
  illustrations/
  asset-manifest.json
```
