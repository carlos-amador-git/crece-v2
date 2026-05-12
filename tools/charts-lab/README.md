# CRECE Charts Lab

Lab interactivo standalone para evaluar visualizaciones con datos reales de la API de CRECE.

## Cómo correr

```bash
cd tools/charts-lab
python3 -m http.server 8765
# Abrir http://localhost:8765
```

Luego en la UI:
1. Click "Login demo (admin)" para obtener token automáticamente
2. Elegir org (MC-CDMX / GOB-OAXACA / CDMX-IND)
3. Click "Cargar datos"
4. Los 3 gráficos se renderizan con datos reales

## Gráficos disponibles

### 1. Treemap — Engagement por dirigente × plataforma
- Color semafórico por sentimiento (rojo/verde/gris)
- Tamaño por total de seguidores
- Jerarquía: Total → Dirigente → Plataforma

### 2. Stream graph — Evolución sentimiento por plataforma
- Positivo apilado arriba, negativo abajo
- Últimos 30 días del primer dirigente
- Toggle por serie haciendo click en leyenda

### 3. Sunburst — Jerarquía org › dirigente › plataforma
- Click en un sector para drill-down
- Colores oficiales por plataforma (Twitter azul, IG rosa, etc.)

## Requisitos

- Backend CRECE corriendo en `http://localhost:8002`
- Al menos 1 dirigente con `social_profiles` en la org seleccionada

## Uso: diseño antes de mover a producción

Este lab existe porque los mismos 3 gráficos van en **múltiples menús del dashboard**
(overview, social, dirigentes). El lab permite iterar el diseño con datos reales
antes de mover los componentes a `frontend/src/components/charts/`.

Ver `docs/CHARTS-LAB-DECISIONES.md` para el mapeo propuesto de chart → menú.
