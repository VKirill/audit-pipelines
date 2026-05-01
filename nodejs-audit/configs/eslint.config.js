// ESLint 9+ flat config
// Скопируй в корень проекта как eslint.config.js
// Если в проекте старый .eslintrc.* — сначала разберись, потом мигрируй

import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';
import security from 'eslint-plugin-security';
import sonarjs from 'eslint-plugin-sonarjs';
import unicorn from 'eslint-plugin-unicorn';
import importPlugin from 'eslint-plugin-import';

export default [
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  security.configs.recommended,
  sonarjs.configs.recommended,
  unicorn.configs.recommended,
  prettier,
  {
    languageOptions: {
      parserOptions: {
        project: './tsconfig.json',
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // Базовое
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-unused-vars': 'off', // отключаем в пользу TS-версии
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/explicit-function-return-type': [
        'warn',
        { allowExpressions: true },
      ],

      // Unicorn — слишком строгие правила выключаем
      'unicorn/prevent-abbreviations': 'off', // позволяет idx, ctx, req, res
      'unicorn/no-null': 'off', // null это нормально
      'unicorn/filename-case': ['error', { case: 'kebabCase' }],

      // SonarJS — сложность
      'sonarjs/cognitive-complexity': ['error', 15],
      'sonarjs/no-duplicate-string': ['warn', { threshold: 5 }],

      // Размеры
      'max-lines': ['warn', { max: 300, skipBlankLines: true, skipComments: true }],
      'max-lines-per-function': [
        'warn',
        { max: 50, skipBlankLines: true, skipComments: true },
      ],
      'max-depth': ['error', 4],
      'max-params': ['warn', 4],
      complexity: ['error', 10],

      // Импорты
      'import/no-cycle': 'error',
      'import/no-duplicates': 'error',
      'import/order': [
        'warn',
        {
          groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index'],
          'newlines-between': 'always',
          alphabetize: { order: 'asc' },
        },
      ],
    },
  },
  {
    // Послабления для тестов
    files: ['**/*.test.*', '**/*.spec.*', '**/tests/**'],
    rules: {
      'max-lines-per-function': 'off',
      'max-lines': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      'sonarjs/no-duplicate-string': 'off',
    },
  },
  {
    ignores: ['dist/**', 'build/**', 'node_modules/**', 'coverage/**', '*.config.js'],
  },
];
