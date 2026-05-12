# Cartografía INE Secciones Electorales

Directorio para shapefiles descargados manualmente desde https://cartografia.ine.mx/sige8/

Estructura esperada:
- `cdmx/SECCION.shp` + `.dbf` + `.prj` + `.shx` (entidad 09)
- `oaxaca/SECCION.shp` + companions (entidad 20, opcional)

Gitignored — no commitear los SHP, solo este README.

Uso (script genérico `import_ine_secciones.py` acepta cdmx|oaxaca):
```
# CDMX
docker exec -e INE_SHP_PATH=/app/data/raw/ine_cartografia/cdmx/SECCION.shp \
    crece-backend python -m scripts.import_ine_secciones cdmx

# Oaxaca (opcional)
docker exec -e INE_SHP_PATH=/app/data/raw/ine_cartografia/oaxaca/SECCION.shp \
    crece-backend python -m scripts.import_ine_secciones oaxaca
```

Notas:
- CDMX: 16 alcaldías esperadas con nombres canonicos INEGI (Cuauhtémoc,
  Álvaro Obregón, etc.) — mapeo hardcoded en el script.
- Oaxaca: 570 municipios — el script usa INITCAP sobre el nombre CAPS del SHP
  (no hay diccionario manual; se reconcilia si se requiere por query posterior).
