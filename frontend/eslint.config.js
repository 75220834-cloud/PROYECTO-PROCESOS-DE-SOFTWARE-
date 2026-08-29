/**
 * Configuracion de ESLint, el revisor de codigo del frontend.
 *
 * Usa el formato "plano" (eslint.config.js), que es el estandar desde
 * ESLint 9. Cada objeto del arreglo anade reglas al anterior.
 */
import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

export default tseslint.config(
  { ignores: ['dist', 'node_modules', 'coverage'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
    },
    plugins: {
      // Verifica que los ganchos de React se usen correctamente: es el
      // origen de la mayoria de errores sutiles en React.
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Permite marcar una variable como intencionalmente no usada
      // anteponiendole un guion bajo.
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
  // Debe ir al final: desactiva las reglas de estilo que chocarian con
  // Prettier, para que las dos herramientas no se peleen.
  prettier,
);
