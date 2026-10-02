# Za Oknem — Asset Pack v1

This branch is reserved for the approved UI asset pack.

## Custom assets

### Android / store
- app icon master: 1024×1024 PNG
- adaptive foreground: 1024×1024 transparent PNG
- adaptive background: 1024×1024 PNG
- adaptive monochrome: 1024×1024 transparent PNG
- Google Play listing icon: 512×512 PNG

### Brand
- transparent logo mark: 1024 / 512 / 256 PNG

### Ambient backgrounds
- welcome: 1242×2688 PNG
- dashboard sunny: 1242×2688 PNG
- dashboard cloudy: 1242×2688 PNG
- dashboard evening: 1242×2688 PNG

Backgrounds contain no baked-in copy. Overlay text and scrims natively so contrast can meet WCAG 2.2 AA.

### State illustrations
Each illustration is supplied as SVG and 1200×800 PNG:
- good conditions
- caution conditions
- bad conditions
- no alerts
- no data
- offline
- location required

## Implementation rules
- Functional navigation/domain/weather icons must come from one vector icon library in code.
- Do not use bitmap icons for tabs or metric cards.
- Do not bake user-facing copy into images.
- Never communicate a status only with color.
- Render text, labels and controls natively for Dynamic Type, VoiceOver and TalkBack.
- Prefer SVG illustrations where supported; PNGs are fallbacks.
- Android adaptive-icon foreground includes extra safe-zone padding for OEM masks.

## Recommended repository location
`mobile/assets/za-oknem/`

Suggested layout:
```
mobile/assets/za-oknem/
  android/
  brand/
  backgrounds/
  illustrations/
```

The source package is generated as `za_oknem_asset_pack_v1.zip`.
