# Cartografía INE Secciones Electorales

Directorio para shapefiles descargados manualmente desde https://cartografia.ine.mx/sige8/

Estructura esperada:
- `cdmx/SECCION.shp` + `.dbf` + `.prj` + `.shx` (entidad 09)
- `oaxaca/SECCION.shp` + companions (entidad 20, opcional)

Gitignored — no commitear los SHP, solo este README.

Uso:
```
docker exec -e INE_SHP_PATH=/app/data/raw/ine_cartografia/cdmx/SECCION.shp \
    crece-backend python -m scripts.import_ine_secciones_cdmx
```
