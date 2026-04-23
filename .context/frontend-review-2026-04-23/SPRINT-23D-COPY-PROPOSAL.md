# Sprint 23-D · Copy rewrite (parcial) + propuesta para full UX

**Clasificación:** 🟡 CALIB (reclasificado por Gemini audit — no toca fórmulas ni umbrales).

## Ejecutado hoy

### Renames de títulos (calibración)

**Tier 1** (`frontend/src/components/diagnostico/cards.tsx`):

| Antes | Ahora |
|---|---|
| ER normalizado por estrato | Engagement vs. tu estrato |
| Breakout Scale (Brookings) | Escalón de viralidad |
| Matriz 2×2 de contenido | Calidad de tu contenido |
| Sentiment Plutchik (6 emociones) | Emociones que provoca tu contenido |
| Crisis Spike detector | Detector de crisis |
| Growth attribution (Time-Decay) | De dónde viene tu crecimiento |
| Share / Like Ratio | Qué tan compartible es tu contenido |
| Humanización Score | Qué tan humano suena tu contenido |
| Benchmark vs competidores | (sin cambio — ya claro) |
| Share of Voice | (sin cambio — término tolerado) |

**Tier 2** (`frontend/src/components/diagnostico_tier2/cards.tsx`):

| Antes | Ahora |
|---|---|
| Cross-Partisan Validation | ¿Te siguen votantes de otro bando? |
| CIB Detector (ITESO/DFRLab) | Detector de coordinación artificial |
| Topic Drift Detector | ¿Tu audiencia habla de lo que publicas? |
| Rage Click Flag | Señales de hostilidad |
| Veda INE Compliance | Cumplimiento veda electoral |
| Filtro de Realidad | (sin cambio — ya claro) |
| Rastreador Promesas | (sin cambio — ya claro) |
| Violencia Política | (sin cambio — ya claro) |

### Contexto académico en página Diagnóstico

`frontend/src/app/dashboard/diagnostico/[dirigenteId]/page.tsx`:
- Reemplazado el párrafo que mencionaba Zenodo v1 · n=316 · Influencer Marketing 3-7% · factor 100×
- Nuevo texto: lenguaje llano, comparación es "otros políticos mexicanos de tu mismo tamaño", sin terminología académica.
- Link "Metodología completa →" renombrado a "Detalle técnico →" (apunta al mismo archivo — F-23-09 B sigue pendiente de decisión del CEO sobre destino final).

## No ejecutado (propuesta para sprint 24+)

La petición del CEO fue más profunda que renames: **"qué mide / cómo te fue / qué hacer"** + "modelo de enseñanza" + "esquema sutil que denote lo que se está mostrando".

Requiere rediseño estructural de `CardShell`:

### Propuesta de props extendida

```tsx
interface CardShellProps {
  // ... props actuales
  verdict?: {
    status: "success" | "warning" | "danger" | "neutral";
    label: string;        // "Vas bien", "Mejorable", "Requiere atención"
    interpretation: string; // "Tu ER supera al 40% de políticos comparables"
  };
  recommendation?: {
    action: string;       // "Publica más contenido de salud"
    href?: string;        // deep-link a Recomendaciones o Plan IA
  };
  // pregunta actual se mueve a un accordion "¿cómo se calcula?"
}
```

### Ejemplo visual propuesto (B01)

```
┌─────────────────────────────────────┐
│ B01 · T1                        [i] │
│ Engagement vs. tu estrato           │
├─────────────────────────────────────┤
│  1.2% │ vs. piso 0.2%               │
│                                     │
│ 🟢 Vas bien                         │
│ Tu interacción supera al 68% de     │
│ políticos mexicanos de tu tamaño.   │
│                                     │
│ [chart por plataforma]              │
│                                     │
│ → Replica lo que hiciste en TikTok │
│   (es tu red más fuerte)            │
│                                     │
│ ▸ ¿Cómo se calcula?                 │
└─────────────────────────────────────┘
```

### Fases propuestas

1. **Fase 1 — extender `CardShell`** con `verdict` + `recommendation` opcionales, sin romper callers actuales (1-2h).
2. **Fase 2 — generar verdict server-side** por bloque a partir de los thresholds ya definidos en backend (3-4h, toca `use-diagnostico-tier1.ts` + backend endpoints).
3. **Fase 3 — wire recommendations** a Plan IA (2h, deep-link a un plan o recomendación específica).
4. **Fase 4 — accordion "¿cómo se calcula?"** con el contenido académico movido ahí (1h).

**Clasificación:** fases 1 y 4 son 🟡 CALIB puro (UI). Fases 2 y 3 tocan backend endpoints — escalable a §9.8 si cambia la shape del API.

### Pregunta al CEO (para sprint 24+)

1. ¿La pregunta que hoy vive en el tooltip debe moverse al accordion o desaparecer?
2. El "verdict" ¿lo computa backend (más riguroso) o frontend con los thresholds ya expuestos?
3. Las recommendations ¿salen de Plan IA o son plantillas estáticas por bloque?

## Screenshots post-cambio

Pendientes de capturar con Playwright después de verificar en Vercel prod (requiere `vercel deploy --prod` desde `frontend/` según memoria session).
