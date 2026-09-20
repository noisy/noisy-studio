import js from "@eslint/js";
import globals from "globals";
import ts from "typescript-eslint";
import vue from "eslint-plugin-vue";

export default ts.config(
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/build/**",
      "**/storybook-static/**",
      "**/.venv/**",
    ],
  },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...vue.configs["flat/essential"],
  {
    files: ["**/*.{js,mjs,cjs,ts,vue}"],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node, __APP_VERSION__: "readonly" },
    },
    rules: {
      // Prettier handles line layout; this rule flags its valid chained indexing.
      "no-unexpected-multiline": "off",
      // Existing payload boundaries deliberately use dynamic shapes. Type checks
      // run separately; lint focuses on correctness rather than a type migration.
      "@typescript-eslint/no-explicit-any": "off",
      "vue/multi-word-component-names": "off",
      "@typescript-eslint/no-unused-expressions": [
        "error",
        { allowShortCircuit: true, allowTernary: true },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrorsIgnorePattern: "^_" },
      ],
    },
  },
  { files: ["**/*.{js,cjs,mjs}"], rules: { "@typescript-eslint/no-require-imports": "off" } },
  {
    files: ["**/*.vue"],
    languageOptions: { parserOptions: { parser: ts.parser, extraFileExtensions: [".vue"] } },
  },
);
