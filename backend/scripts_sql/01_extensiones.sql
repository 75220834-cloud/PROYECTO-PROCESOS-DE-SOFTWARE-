-- ---------------------------------------------------------------------------
-- Extensiones que necesita la base de datos de RutaVivaMantaro.
-- Este script lo ejecuta Docker automaticamente la primera vez que se crea
-- la base, gracias al montaje en /docker-entrypoint-initdb.d/.
-- ---------------------------------------------------------------------------

-- PostGIS: tipos y funciones geograficas. Permite guardar la ubicacion de cada
-- recurso turistico como GEOGRAPHY(POINT, 4326) -- coordenadas en grados sobre
-- el elipsoide WGS84, el mismo sistema del GPS y del inventario del MINCETUR.
CREATE EXTENSION IF NOT EXISTS postgis;

-- unaccent: permite buscar "Nunoa" y que encuentre "Ñuñoa", o "Concepcion" y
-- que encuentre "Concepción". Necesario porque los nombres de distrito del
-- inventario oficial vienen con tildes y los visitantes no siempre las escriben.
CREATE EXTENSION IF NOT EXISTS unaccent;

-- pg_trgm: busqueda por similitud de texto (trigramas). Sostiene el buscador
-- del catalogo tolerante a errores de tipeo.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
