// Extends app.json with the parts that depend on the build profile or must stay out of the
// hand-edited app.json.
//
// 1. Foreground location only (rule #11): `expo-location` for "Użyj mojej lokalizacji" (one
//    read to find the nearest place). Coarse location is enough for a town, so FINE and every
//    background/foreground-service permission the plugin or its libraries could add are blocked.
// 2. The EAS "preview" profile (eas.json) is a TEST APK that talks to a backend on a local
//    network over plain HTTP (no VPS yet), and release builds on Android block cleartext traffic
//    by default. So cleartext is allowed for that profile ONLY; development and production
//    builds keep Android's default (HTTPS only).
module.exports = ({ config }) => ({
  ...config,
  android: {
    ...(config.android ?? {}),
    blockedPermissions: [
      ...(config.android?.blockedPermissions ?? []),
      "android.permission.ACCESS_FINE_LOCATION",
      "android.permission.ACCESS_BACKGROUND_LOCATION",
      "android.permission.FOREGROUND_SERVICE",
      "android.permission.FOREGROUND_SERVICE_LOCATION",
    ],
  },
  plugins: [
    ...(config.plugins ?? []),
    [
      "expo-location",
      {
        isAndroidBackgroundLocationEnabled: false,
        isAndroidForegroundServiceEnabled: false,
        locationWhenInUsePermission: "Za Oknem używa Twojej lokalizacji jednorazowo, żeby znaleźć najbliższą miejscowość.",
      },
    ],
    ...(process.env.EAS_BUILD_PROFILE === "preview"
      ? [["expo-build-properties", { android: { usesCleartextTraffic: true } }]]
      : []),
  ],
});
