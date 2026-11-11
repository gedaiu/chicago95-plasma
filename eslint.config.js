// re:cinq house rules for the JS here; its stylistic rules add the blank lines prettier never inserts.
import stylistic from "@stylistic/eslint-plugin";
import reLint from "@re-cinq/eslint-plugin-re-lint";
import tseslint from "typescript-eslint";

const houseRules = reLint.configs.recommended({ tseslint, stylistic });
const scopedToJavaScript = (config) => (config.files ? config : { ...config, files: ["**/*.js"] });

export default tseslint.config(
  {
    ignores: [
      "node_modules/**",
      "data/clippy/**",
      "tests/references/**",
      "docs/**",
      "test-output/**",
      "report/**",
      // QML JavaScript libraries begin with ".pragma library", which no JavaScript parser accepts.
      "**/clockFormat.js",
      "**/launchers.js",
      "**/quickLaunch.js",
      "**/quickLaunchBand.js",
      "**/sizing.js",
      "**/settings.js",
      // user.js is a list of Firefox preferences, so its boolean arguments are data, not behaviour flags.
      "config/firefox-user.js",
    ],
  },
  { files: ["**/*.js"], languageOptions: { ecmaVersion: 2022, sourceType: "script" } },
  ...houseRules.map(scopedToJavaScript),
);
