-- Sprint 1 · 2026-05-09 · Asigna municipio a rows Mitofsky de alcaldes CDMX
-- (Demoscopía Digital ya trae municipio en columna; Mitofsky no — bug histórico de seed)

BEGIN;

-- Iztapalapa
UPDATE encuestas_publicas SET municipio='Iztapalapa'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Aleida Alavez','Aleida Alavez Ruíz','Clara Brugada','Clara Brugada Molina');

-- Cuauhtémoc
UPDATE encuestas_publicas SET municipio='Cuauhtémoc'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Alessandra Rojo','Sandra Cuevas','Sandra Cuevas Nieves');

-- Tláhuac
UPDATE encuestas_publicas SET municipio='Tláhuac'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Berenice Hernández','Berenice Hernández Calderón','Raúl Ortega Rodríguez');

-- Cuajimalpa de Morelos
UPDATE encuestas_publicas SET municipio='Cuajimalpa de Morelos'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Carlos Orvañanos','Adrián Rubalcava','Adrián Rubalcava Suárez');

-- Xochimilco
UPDATE encuestas_publicas SET municipio='Xochimilco'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Circe Camacho','José Carlos Acosta','José Carlos Acosta Ruíz');

-- Venustiano Carranza
UPDATE encuestas_publicas SET municipio='Venustiano Carranza'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Evelyn Parra','Evelyn Parra Álvarez');

-- La Magdalena Contreras
UPDATE encuestas_publicas SET municipio='La Magdalena Contreras'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Fernando Mercado','Gerardo Quijano','Gerardo Quijano Morales');

-- Tlalpan
UPDATE encuestas_publicas SET municipio='Tlalpan'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Gabriela Osorio','Alfa González','Alfa González Magallanes');

-- Coyoacán
UPDATE encuestas_publicas SET municipio='Coyoacán'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Giovani Gutiérrez','Giovani Gutiérrez Aguilar');

-- Gustavo A. Madero
UPDATE encuestas_publicas SET municipio='Gustavo A. Madero'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Janecarlo Lozano','Francisco Chiguíl','Francisco Chiguíl Figueroa');

-- Álvaro Obregón
UPDATE encuestas_publicas SET municipio='Álvaro Obregón'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Javier Casarín','Javier López','Javier López Casarin','Lía Limón','Lía limón','Lía Limón García');

-- Iztacalco
UPDATE encuestas_publicas SET municipio='Iztacalco'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Lourdes Paz','Lourdes Paz Reyes','Armando Quintero','Armando Quintero Martínez');

-- Benito Juárez
UPDATE encuestas_publicas SET municipio='Benito Juárez'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Luis Mendoza','Luis Alberto Mendoza','Santiago Taboada','Santiago Taboada Cortina');

-- Miguel Hidalgo
UPDATE encuestas_publicas SET municipio='Miguel Hidalgo'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Mauricio Tabe','Mauricio Tabe Echartea');

-- Azcapotzalco
UPDATE encuestas_publicas SET municipio='Azcapotzalco'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Nancy Núñez','Nancy Marlene Núñez Reséndiz','Margarita Saldaña','Margarita Saldaña Hernández');

-- Milpa Alta (foco del sprint)
UPDATE encuestas_publicas SET municipio='Milpa Alta'
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NULL
   AND actor_nombre IN ('Octavio Rivero','Judith Vanegas','Judith Vanegas Tapia');

-- Verificar cobertura
SELECT municipio, COUNT(DISTINCT actor_nombre) AS alcaldes, COUNT(*) AS mediciones,
       MIN(fecha_publicacion) AS desde, MAX(fecha_publicacion) AS hasta
  FROM encuestas_publicas
 WHERE entidad='Ciudad de México' AND ambito='municipal' AND municipio IS NOT NULL
 GROUP BY municipio
 ORDER BY municipio;

COMMIT;
