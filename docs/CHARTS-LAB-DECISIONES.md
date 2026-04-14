# Charts Lab — Decisiones de Visualización

**Fecha del ejercicio:** ~2026-04-11 (2 días antes de esta documentación)
**Fuente:** Memoria de sesión `feedback_chart_preferences.md` (recuperada en sesión 2026-04-13)
**Estado:** Decisiones tomadas, **NO implementadas** en el dashboard aún

---

## Contexto

En un ejercicio side-by-side se evaluaron **5 tipos de gráficos** alternativos a los charts estándar de la app. El CEO rechazó inicialmente mi criterio de "5 segundos para un político" (demasiado rígido) y aceptó 3 visualizaciones más expresivas.

---

## Gráficos aceptados (en orden de preferencia del CEO)

### 1. 🟢 Treemap — preferido #1
- Con **colores semafóricos** rojo / verde / gris
- Ventaja: permite ver jerarquía y magnitud de un vistazo
- Uso sugerido: distribución de engagement por plataforma o por dirigente

### 2. 🟡 Stream graph — preferido #2
- Requiere: **leyenda interactiva con toggle "todos"** para activar/desactivar en bloque
- Ventaja: muestra evolución temporal de múltiples series sin cruces confusos
- Uso sugerido: evolución de sentimiento/engagement por plataforma en el tiempo

### 3. 🟠 Sunburst — preferido #3
- Aunque fue rechazado inicialmente por legibilidad de anillos exteriores
- El CEO lo quiere de todos modos para navegación jerárquica
- Uso sugerido: drill-down dirigente → plataforma → tipo de post

---

## Gráficos rechazados (no implementar)

No se registraron los 2 rechazados en la memoria original. Cuando el CEO confirme, actualizar este doc.

---

## Principios UX de visualización (reglas permanentes)

Derivadas del feedback del CEO:

1. **NO aplicar regla "5 segundos" rígidamente** — renderizar opciones y dejar al CEO decidir
2. **Visualizaciones expresivas > minimalistas planas** — el CEO valora insights sobre pura velocidad de lectura
3. **Toda visualización DEBE tener:**
   - (a) Filtros/cambio de datos interactivo
   - (b) Leyenda interactiva con **toggle global** cuando hay múltiples series
4. **Quitar etiquetas redundantes del eje X** cuando son auto-evidentes (ej: "Día 1, Día 2..." → "1, 2...")
5. **Cuando haya dudas de criterio estético:** construir un **lab standalone** (HTML + Plotly CDN) con datos reales y pedirle al CEO que elija visualmente

---

## Dónde implementar los 3 gráficos aceptados

**CORRECCIÓN (CEO 2026-04-13):** NO era solo para Radiografía. Los gráficos iban a usarse en **múltiples menús del dashboard** según cada contexto. La memoria de la sesión original fue ambigua en este punto.

**Asignación propuesta (pendiente validación CEO):**

| Gráfico | Menú candidato | Caso de uso |
|---|---|---|
| **Treemap** semafórico | Dashboard / Overview | Distribución de engagement por plataforma y dirigente |
| **Treemap** | /dashboard/social | Ranking de posts por engagement + color por sentiment |
| **Treemap** | /dashboard/canvassing | Cobertura territorial: secciones como celdas, color = contactados/lista_nominal |
| **Stream graph** | /dashboard/social | Evolución temporal del sentimiento por plataforma |
| **Stream graph** | /dashboard/planes | Timeline de tareas de planes por estado (pending/in_progress/done) |
| **Sunburst** | /dashboard/dirigentes | Jerarquía dirigente → plataforma → tipo de post |
| **Sunburst** | /dashboard/ciudadanos | Jerarquía alcaldía → sección → categoría P1-P5 |

### Estado del HTML lab (2026-04-11)

**Perdido.** El HTML standalone que se creó para la comparación side-by-side ya no existe en disco. Probable causa: se generó en `/tmp` y se limpió. No se commiteó al repo, no quedó en Obsidian.

**Reconstruir:** crear `tools/charts-lab/index.html` en el repo con los 3 gráficos aceptados + datos reales de la DB (fetch a API local). Así queda persistente para futuras decisiones de visualización.

Sugerencia de arquitectura:
```
frontend/src/app/dashboard/
├── page.tsx                     # Overview — charts simples (sentiment line, bar followers)
├── radiografia/                 # NUEVA página propuesta
│   ├── page.tsx                 # Container con tabs o grid
│   ├── treemap-engagement.tsx
│   ├── stream-sentiment.tsx
│   └── sunburst-jerarquia.tsx
```

---

## Deuda abierta

| Item | Estado | Próximo paso |
|---|---|---|
| Implementar Treemap | ❌ No hecho | Componente React + Recharts/Plotly |
| Implementar Stream graph | ❌ No hecho | Componente React + D3 stream layout |
| Implementar Sunburst | ❌ No hecho | Componente React + Nivo/D3 |
| Crear página Radiografía | ❌ No hecho | Route + layout + 3 componentes arriba |
| Documentar los 2 gráficos rechazados | ❌ No registrado | Preguntar al CEO cuáles fueron |

---

## Lección aprendida (para futuras sesiones)

> "No entiendo por qué la reticencia a generar documentos a los cuales podamos recurrir."
> — CEO, 2026-04-13

**Regla:** cuando se tome una decisión de diseño (gráficos, UX, arquitectura) en una sesión, crear INMEDIATAMENTE un doc en `docs/` del repo. No confiar solo en la memoria de Claude — los chats son efímeros, los archivos son persistentes.

Archivos de docs que debieron existir desde el principio:
- `docs/CHARTS-LAB-DECISIONES.md` (este)
- `docs/SENTIMENT-DESIGN.md` — decisiones sobre qué es sentiment en CRECE
- `docs/UX-PRINCIPLES.md` — reglas inquebrantables de diseño para el CEO
- `docs/DECISIONES-POR-SESION.md` — log cronológico de decisiones
