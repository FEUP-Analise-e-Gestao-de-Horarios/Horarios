import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import reactPlugin from "eslint-plugin-react";
import jsxA11y from "eslint-plugin-jsx-a11y";
import tseslint from "typescript-eslint";
import prettierConfig from "eslint-config-prettier";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  globalIgnores(["dist", "node_modules"]),

  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      // Base
      js.configs.recommended,

      // TypeScript — type-aware rules (catches more bugs, requires parserOptions below)
      ...tseslint.configs.recommendedTypeChecked,

      // React
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,

      // Prettier must be last — disables ESLint rules that conflict with Prettier formatting
      prettierConfig,
    ],

    plugins: {
      react: reactPlugin,
      "jsx-a11y": jsxA11y,
    },

    rules: {
      ...reactPlugin.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,

      "react/react-in-jsx-scope": "off", // Not needed with React 17+ JSX transform
      "react/prop-types": "off", // TypeScript covers this
    },

    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        // Required for recommendedTypeChecked
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },

    settings: {
      react: { version: "detect" },
    },
  },
]);
