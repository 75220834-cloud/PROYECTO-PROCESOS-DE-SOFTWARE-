/**
 * Preparacion comun de todas las pruebas del frontend.
 *
 * Anade a Vitest las comprobaciones de jest-dom, que permiten escribir
 * expect(elemento).toBeInTheDocument() en vez de comparar nodos a mano.
 */
import '@testing-library/jest-dom/vitest';
