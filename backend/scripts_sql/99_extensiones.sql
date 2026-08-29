-- ---------------------------------------------------------------------------
-- Extensiones de la base de datos de RutaVivaMantaro.
--
-- Docker ejecuta los archivos de /docker-entrypoint-initdb.d/ en orden
-- alfabetico, y la propia imagen de PostGIS trae un 10_postgis.sh que instala
-- sus extensiones. Por eso este archivo empieza por 99: tiene que correr
-- DESPUES, para poder desinstalar lo que no necesitamos.
--
-- Solo se ejecuta la primera vez que se crea la base de datos.
-- ---------------------------------------------------------------------------

-- --- Lo que si necesitamos ------------------------------------------------

-- PostGIS: tipos y funciones geograficas. Permite guardar la ubicacion de
-- cada recurso turistico como GEOGRAPHY(POINT, 4326) -- coordenadas en grados
-- sobre el elipsoide WGS84, el mismo sistema del GPS y del inventario del
-- MINCETUR -- y calcular distancias reales en metros.
CREATE EXTENSION IF NOT EXISTS postgis;

-- unaccent: permite buscar "Concepcion" y que encuentre "Concepción", o
-- "Nunoa" y que encuentre "Ñuñoa". Necesario porque los nombres del
-- inventario oficial llevan tildes y los visitantes no siempre las escriben.
CREATE EXTENSION IF NOT EXISTS unaccent;

-- pg_trgm: busqueda por similitud de texto mediante trigramas. Sostiene el
-- buscador del catalogo, tolerante a errores de tipeo.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- --- Lo que sobra ----------------------------------------------------------

-- postgis_tiger_geocoder es el geocodificador del censo de ESTADOS UNIDOS.
-- La imagen lo instala por omision y crea mas de cincuenta tablas que este
-- proyecto no usa: ensucian las migraciones de Alembic y confunden a quien
-- abra la base por primera vez. El proyecto es de Junin, Peru.
DROP EXTENSION IF EXISTS postgis_tiger_geocoder CASCADE;
DROP EXTENSION IF EXISTS postgis_topology CASCADE;

DROP SCHEMA IF EXISTS tiger CASCADE;
DROP SCHEMA IF EXISTS tiger_data CASCADE;
DROP SCHEMA IF EXISTS topology CASCADE;
