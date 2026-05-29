# PLAN · UX Perfil Dirigente (Social) — ronda Gemini 2 · 2026-05-12 noche

## Objetivo
Aplicar las 8 mejoras restantes que Gemini observó sobre `/dashboard/dirigentes/[id]`,
agregar nueva visualización de sentimiento (alfombra/stacked area) sin quitar la
de barras actual, y dejar el demo SAS-grade.

## Inputs vigentes
- Bugs funcionales ya resueltos (commit `[reciente]`):
  - Actividad Política Alineada ✅ (4,108 posts clasificados)
  - Semáforo Crecimiento ✅ (mensaje informativo)
  - Treemap letras visibles ✅ (custom content fit-text)
  - plataformas_destino estructurado ✅
- Saymi en Vercel ya ve cards con voz oaxaqueña real (35 hand-crafted)

## Sprints

### S1 · Sentimiento Timeline · nueva opción "Área Apilada"
**Esfuerzo**: 35 min
**Archivos**: `frontend/src/components/charts/sentiment-line-chart.tsx` (o equivalente)

- Agregar toggle de 2 botones: `Barras (actual)` / `Área Apilada`
- Mantener la versión de barras intacta (default)
- Nueva vista usa `<AreaChart>` de Recharts con stackOffset="silhouette" (river)
  o stack normal proporcional · suaviza el "efecto moiré" de Gemini
- Tooltip que destaca día específico con `<ReferenceLine>` al hover
- Persistir preferencia en localStorage (`sentiment-chart-kind`)

**Criterio**: pasar `npx tsc --noEmit` clean + smoke screenshot en local.

### S2 · Engagement por Plataforma · ejes "0000" fix
**Esfuerzo**: 15 min
**Archivos**: `frontend/src/components/charts/engagement-bar-chart.tsx`

- Bug: el YAxis muestra "0000" porque tickFormatter no está o usa precisión nula.
- Fix: `tickFormatter={(v) => formatNumber(v)}` con utility ya existente
  (`formatNumber` que convierte 1500 → "1.5K", 20000 → "20K")
- También aplicar al `XAxis` si tiene mismo problema.

**Criterio**: screenshot muestra "1K", "5K", "10K" en lugar de "0", "0000".

### S3 · Timeline de Publicaciones · tags + thumbnails
**Esfuerzo**: 30 min
**Archivos**: `frontend/src/components/social/post-card.tsx` (o equivalente)

- (3a) Tags sentimiento más contrastantes:
  - Neutral actual es muy pálido. Cambiar a `bg-slate-500/15 text-slate-700`
  - Positivo verde más saturado, Negativo rojo más saturado
  - Background del badge con borde para visibilidad rápida en scroll
- (3b) Thumbnails:
  - Si `social_post.media_urls` (jsonb) tiene primer item, renderizar `<img>` 60×60
    miniatura a la izquierda del texto
  - Skeleton si no carga (next/image)
  - Fallback: si no hay media_urls, mostrar icono de plataforma como placeholder

**Criterio**: post con imagen muestra miniatura · post sin imagen muestra icono ·
3 sentimientos visualmente distintos al scroll rápido.

### S4 · Header Dirigente · espaciado + badges plataforma
**Esfuerzo**: 25 min
**Archivos**: `frontend/src/components/dirigentes/profile-header.tsx`

- Gemini: "El nombre tiene mucho aire a la derecha, los iconos están apretados abajo"
- Fix: nombre + cargo a la izquierda con max-width: 60% · stats agrupados a la derecha
- Iconos redes en bloque visual más estilizado:
  - Box gris claro alrededor de los 5 iconos
  - Hover muestra cuenta de followers per red
  - Si red está vacía (0 followers), ícono opaco

**Criterio**: layout responsive · screenshot muestra header balanceado.

### S5 · Actividad Alineada Card · indicador animado "Análisis en proceso"
**Esfuerzo**: 15 min
**Archivos**: `frontend/src/components/dashboard/actividad-alineada-card.tsx`

- Cuando `empty_state="no_classified"`:
  - Agregar barra de progreso animada sutil (animate-pulse o shimmer)
  - Color sutil amber con texto "Clasificación IA en proceso · revisa en 1h"
- Cuando hay datos: mantener actual.

**Criterio**: empty state se siente activo · no estático.

### S6 · SemaforoCrecimiento · badge stale más vibrante
**Esfuerzo**: 10 min
**Archivos**: `frontend/src/components/dashboard/semaforo-crecimiento.tsx`

- Gemini: badge ">48h sin update" debería ser más llamativo
- Cambiar de `border-amber-500/40 text-amber-600` a `bg-amber-500/15 text-amber-700 border-amber-500/50 font-medium`
- Icono `<AlertTriangle>` ya está · OK
- Agregar pulsing dot al lado del badge para acción inmediata

**Criterio**: badge se nota inmediatamente al scrollear.

### S7 · Sidebar · iconografía consistencia
**Esfuerzo**: 10 min
**Archivos**: `frontend/src/components/layout/sidebar.tsx`

- Sidebar usa Sparkles para "Recomendaciones" y "Diferenciadores"
- Header de Recomendaciones ya cambió a Wand2 (commit anterior)
- Unificar: sidebar también a `Wand2` para "Recomendaciones" (Sparkles queda para
  "Diferenciadores" como diferenciador)

**Criterio**: sidebar Recomendaciones muestra Wand2 · header Recomendaciones muestra Wand2.

### S8 · Cross-audit Gemini + ajustes
**Esfuerzo**: 15 min

- Después de implementar S1-S7, screenshot completo de `/dashboard/dirigentes/[id]`
- Enviar a Gemini con prompt: "¿Quedan issues? Devuelve veredictos por sección"
- Aplicar al 100% lo que Gemini observe
- Re-deploy si fixes son no-triviales

**Criterio**: Gemini aprueba "ready for demo" o lista 0-2 nits cosméticos.

## Asignación de recursos

| Sprint | Skill / Tooling | Validación |
|--------|-----------------|------------|
| S1 | recharts AreaChart docs (Context7) | tsc + browser screenshot |
| S2 | utility formatNumber existente | tsc + screenshot |
| S3 | thumbnail Next.js `<Image>` | tsc + screenshot |
| S4 | Tailwind responsive flex | tsc + responsive test |
| S5 | Tailwind animate-pulse | tsc + screenshot |
| S6 | UX cosmético rápido | screenshot |
| S7 | lucide-react Wand2 | tsc |
| S8 | gemini-clean --mode review | manual |

## Cierre

- `npx tsc --noEmit` clean
- Single commit con scope `ux(perfil-dirigente)` describiendo los 7 fixes
- Push + deploy Vercel
- Smoke test login Saymi en Vercel
- Reporte breve al CEO con before/after por bullet

## Riesgos

- **Recharts AreaChart**: si stackOffset="silhouette" rompe con datos pocos puntos,
  fallback a stack normal (no silhouette)
- **Tunnel**: si rota durante deploy, manual restart (PID actual 61084)
- **next/image en thumbnails**: si remote loader no está configurado para hosts
  Apify, usar `<img>` plain

## Tiempo total estimado: ~2h 35min

Comenzando ahora.
