/**
 * Preparacion comun de todas las pruebas del frontend.
 *
 * Anade a Vitest las comprobaciones de jest-dom, que permiten escribir
 * expect(elemento).toBeInTheDocument() en vez de comparar nodos a mano.
 */
import '@testing-library/jest-dom/vitest';

// jsdom no implementa scrollIntoView: no tiene disposicion visual, asi que no
// hay nada que desplazar. Cualquier componente que baje solo a lo ultimo -el
// panel del asistente, sin ir mas lejos- reventaria al montarse en pruebas.
//
// Se anade como funcion vacia y no como espia porque ninguna prueba necesita
// comprobar que se llamo: lo que importa es que el componente pueda montarse.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function noHaceNadaEnJsdom() {};
}
