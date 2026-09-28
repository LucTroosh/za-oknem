// Exact shape per Expo's own docs (docs.expo.dev/guides/using-eslint) — the
// earlier hand-guessed `[...expoConfig]` spread wasn't verified and failed CI.
const { defineConfig } = require("eslint/config");
const expoConfig = require("eslint-config-expo/flat");

module.exports = defineConfig([expoConfig, { ignores: ["dist/*"] }]);
