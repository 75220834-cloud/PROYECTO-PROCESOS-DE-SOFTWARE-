/**
 * Configuracion de Vite, el servidor de desarrollo y empaquetador del frontend.
 *
 * Incluye tambien la configuracion de Vitest (las pruebas), porque ambos
 * comparten el mismo sistema de resolucion de modulos y asi no se duplica.
 */
/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { defineConfig } from 'vite';

// import.meta.dirname es la forma moderna de obtener la carpeta de este
// archivo en modulos ES. Sustituye a __dirname, que solo existia en CommonJS.
const carpetaDeEsteArchivo = import.meta.dirname;

export default defineConfig({
  plugins: [
    react(),
    // En Tailwind 4 la integracion es un plugin de Vite: ya no hace falta
    // PostCSS ni un archivo tailwind.config.js aparte.
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // Permite escribir  import X from '@/componentes/X'  en vez de
      // rutas relativas largas como '../../componentes/X'.
      '@': path.resolve(carpetaDeEsteArchivo, './src'),
    },
  },
  server: {
    port: 5173,
  },
  test: {
    // Las pruebas de componentes necesitan un DOM simulado; jsdom lo provee.
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/configuracion_pruebas.ts',
    css: true,
    // Nuestros archivos de prueba se llaman *.prueba.tsx (regla del proyecto:
    // todo en espanol), no *.test.tsx como espera Vitest por omision.
    include: ['src/**/*.prueba.{ts,tsx}'],
  },
});
