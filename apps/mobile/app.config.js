// Extends app.json. The only dynamic part: the EAS "preview" profile (eas.json) is a TEST APK
// that talks to a backend on a local network over plain HTTP (no VPS yet), and release builds on
// Android block cleartext traffic by default. So cleartext is allowed for that profile ONLY;
// development and production builds keep Android's default (HTTPS only).
module.exports = ({ config }) => ({
  ...config,
  plugins: [
    ...(config.plugins ?? []),
    ...(process.env.EAS_BUILD_PROFILE === "preview"
      ? [["expo-build-properties", { android: { usesCleartextTraffic: true } }]]
      : []),
  ],
});
