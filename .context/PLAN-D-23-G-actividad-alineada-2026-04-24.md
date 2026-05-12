# Plan D-23-G' · Actividad Política Alineada · 2026-04-24

**Origen:** `/sprint-review` post diálogo CEO sobre "Sentimiento Prom. Negativo -50%" en ficha Piña.
**Status:** Plan vigente · supersede al plan 4-fases D-23-G' (con disenso CEO abierto desde 2026-04-23).
**Disuelve:** B-23-03 (motor sentimiento con afiliación) · disenso D-23-G' · taskboard #12 (decisión vocabulario A/B/C).

---

## Cambio fundamental

El plan anterior intentaba **arreglar el flip** (D-23-G aplicado como multiplicador × -1 sobre score crudo). Este plan **reformula el KPI** para que el flip ya no sea necesario.

### Diagnóstico raíz

El bug "Piña Negativo -50%" es síntoma de un error de modelado:
- Lo que el CEO quiso encodear: *"¿el dirigente está haciendo el trabajo político que su rol demanda?"* — pregunta de **alineación de actividad**.
- Lo que se implementó: multiplicador × -1 sobre score de polaridad agregado — operación de **inversión de polaridad**.

Las dos preguntas no son equivalentes. Aplicar inversión de polaridad para responder alineación de actividad genera respuestas literalmente al revés en posts personales (Copa Naranja: positivo personal → flipea a negativo político sin sustento).

### Reformulación

KPI principal pasa de **score numérico ajustado** a **proporción de actividad alineada a rol**.

Para cada post, IA clasifica `target_politico` ∈ {`oficialismo`, `oposicion`, `propio`, `personal`} (4 etiquetas excluyentes, no scores ni multi-label).

Por dirigente computamos:

| Rol | Fórmula KPI | Lectura |
|-----|-------------|---------|
| **Oposición** | `(target=oficialismo + target=propio) / total` | "% de tu actividad fue construir narrativa de oposición" |
| **Oficialismo** | `(target=propio + target=oposicion) / total` | "% de tu actividad fue defender o responder" |
| **Independiente** | `target=propio / total` | "% de tu actividad fue agenda propia" |

Sentimiento crudo (raw `sentiment_score`) se preserva como **subline informacional** sin manipulación. Etiquetado: *"Tono general de tu contenido"* (no "momentum político").

### Lo que esto elimina

| Elemento | Estado |
|----------|--------|
| `frontend/src/lib/politica/sentiment.ts` (helper flip) | **Eliminado** del bundle |
| Disenso D-23-G' (matriz v2/v3 vocabulary) | **Disuelto** · sin matriz de scores |
| Taskboard #12 BLOCKER decisión CEO | **Cerrado** sin necesidad de decisión |
| Phase B "humano clasifica" (riesgo postergamiento) | **Disuelto** · KPI no depende de juicio humano |
| Cold start ("clasifica para activar") | **Eliminado** · IA backfilea desde día 1 |
| Cascada resolver de 3 tiers | **Reducida** · solo lectura directa de columna precomputada |
| Compliance LFPDPPP automated decision-making | **Reducido** · IA solo identifica intención del autor (target), no decide sentimiento |

---

## Schema (forward-compatible mínimo)

```sql
-- social_posts: 3 columnas nuevas
ALTER TABLE social_posts ADD COLUMN target_politico varchar(32);     -- oficialismo|oposicion|propio|personal | NULL
ALTER TABLE social_posts ADD COLUMN nlp_model_version varchar(64);    -- 'crece-political-v1' | etc
ALTER TABLE social_posts ADD COLUMN clasificacion_origen varchar(32) DEFAULT 'ai_suggested';
                                              -- 'ai_suggested' | 'human_dirigente' | 'human_admin' | 'human_consultor'
                                              -- valores 'human_*' reservados forward-compat (Phase B opcional posterior)

-- dirigentes: 1 columna recreada
ALTER TABLE dirigentes ADD COLUMN rol_politico varchar(32);          -- oficialismo|oposicion|independiente

-- Index para queries de KPI
CREATE INDEX ix_social_posts_target_politico_dirigente
  ON social_posts (dirigente_id, target_politico)
  WHERE target_politico IS NOT NULL;
```

**Lo que NO se incluye** (vs propuestas anteriores):
- ~~`tono_discurso`~~ (3-cat redundante con target)
- ~~`sentimiento_politico_ajustado`~~ (no flip, no necesita columna)
- ~~`sentimiento_humano`~~ (Phase B opcional posterior)
- ~~`clasificacion_history`~~ (Phase B)
- ~~`clasificacion_samples`~~ (Phase B)

---

## Ejecución · 4 días

### Día 1 · Migración hand-written + revisión

**Quién:** Claude (autor) · `superpowers:code-reviewer` subagent (auditor independiente per D-OPS-10) · CEO firma diff antes de aplicar.

**Acciones:**
1. Verificar schema actual (information_schema) confirma que las 4 columnas no existen
2. Escribir migración a mano (sin autogenerate · D-OPS-08): `recreate_political_columns_actividad_alineada.py`
3. Cabecera explícita: *"# D-OPS-08 hand-written · NO autogenerate · D-OPS-09 atómica · D-OPS-10 revisor §9.8 firma antes de aplicar"*
4. `upgrade()` con `IF NOT EXISTS` defensivo (ALTER TABLE ... ADD COLUMN IF NOT EXISTS) por si schema parcialmente reconstruido
5. `downgrade()` simétrico
6. Code-reviewer subagent lee diff completo + entrega checklist + report
7. Diff + report a CEO para sign-off
8. Aplicar local: `alembic upgrade head` en crece_dev (`:5438`)
9. Verificar columnas existen via `\d social_posts` y `\d dirigentes`

**Done:**
- 4 columnas creadas en local DB
- Migración committed con firma D-OPS-08 en mensaje
- Code-reviewer report archivado en `.context/diagnostico-visual-2026-04-24/code-review-migration-D23G.md`
- Cero filas afectadas (NULL default · backwards-safe)

### Día 2 · Clasificador IA Gemini API

**Quién:** Claude (autor) · golden set CEO (validación)

**Ajustes Gemini cross-audit 2026-04-24:**
- Golden set sube de 20 a **60 posts** (15/categoría aprox) · 5 posts/cat es smoke test, no validación predictiva
- Prompt incluye **regla desempate**: "Ante duda entre propio/oficialismo, prioriza 'propio' si hay llamado a la acción"
- Prompt incluye **contexto nivel de gobierno** según cargo del dirigente (federal/estatal/municipal)
- Posts sin texto (pura imagen/video) clasifican como **`no_determinado`** (no se incluyen en denominador del KPI)
- Implementación con **pytest parametrizado** para iterar prompt rápido contra golden set

**Acciones:**
1. CEO clasifica manualmente 60 posts golden set distribuidos por dirigente y rol · incluir adversariales explícitos:
   - 5 Copa-Naranja-style (autopromocional puro)
   - 5 críticas directas al gobierno
   - 5 mixtos ("Mientras MORENA arruina, ganamos copa naranja")
   - 5 personales puros (familia, deporte, cultural)
   - 40 distribuidos entre los 8 dirigentes activos+shadow (5 c/u)
2. Script `backend/scripts/classify_target_politico.py`:
   - Input: `post.content` + `post.dirigente_nombre` + `post.dirigente_partido` + `post.dirigente_cargo` (federal/estatal/municipal)
   - Prompt Gemini API: *"Clasifica el target del post entre 4 etiquetas excluyentes: 'oficialismo' (critica/menciona al gobierno actual al nivel del cargo del dirigente), 'oposicion' (critica/menciona oposición política), 'propio' (habla de su propia gestión/iniciativas/logros · prioriza esta etiqueta si hay llamado a la acción), 'personal' (deportes, familia, cultural, sin contenido político). Si el post no tiene texto suficiente para clasificar, responde 'no_determinado'. Responde solo con una etiqueta."*
   - Output: 1 token (5-cat con `no_determinado` como fallback) + log de razón opcional
   - Idempotente: `WHERE target_politico IS NULL OR nlp_model_version != 'crece-political-v1'`
3. Test contra golden set con pytest parametrizado: F1 macro ≥ 0.80 sobre 4 categorías productivas (no_determinado se excluye de F1)
4. Si F1 < 0.80: iterar prompt (temperatura 0.0, ajustar reglas desempate) o abortar a Opción "apagar flip puramente"

**Done:**
- Golden set 60 posts archivado en `.context/golden-set-target-politico-2026-04-24.json`
- F1 macro ≥ 0.80 sobre golden set
- Script ejecutable contra DB local con dry-run mode
- Logs de razonamiento por post para auditar errores
- Tests pytest parametrizados verdes

### Día 3 · Backend KPI + Frontend cambio principal

**Quién:** Claude

**Acciones backend:**
1. `app/services/actividad_alineada.py`: función `compute_actividad_alineada(dirigente_id, days=7)` retorna `{score: 0..1, breakdown: {oficialismo, oposicion, propio, personal}, total_posts, days}`
2. Endpoint nuevo `GET /api/v1/dirigentes/{id}/actividad-alineada?days=7`
3. Endpoint existente `/dashboard/overview` agrega campo `actividad_alineada`

**Acciones frontend:**
1. Crear `ActividadAlineadaCard.tsx` (reemplaza `SentimentKpiCard` en Tier 1 ficha dirigente)
2. KPI hero: número grande (ej. "37%") + label "Actividad Política Alineada · 7d"
3. **Breakdown visual obligatorio** (Gemini ajuste): barras apiladas con 4 segmentos · oposición 90/10 vs 10/90 requiere estrategia diferente · KPI unifica · desglose diagnostica
4. Pills con conteos por categoría
5. Tooltip con fórmula por rol político
6. Sentimiento raw movido a sección "Tono general" subordinada (sin flip)
7. Eliminar `frontend/src/lib/politica/sentiment.ts` del bundle
8. Eliminar `partido` prop de `SentimentBadge`, `PostCard`, `SentimentPieChart`
9. Backfill de los componentes downstream

**Done:**
- KPI hero muestra "Actividad Política Alineada" en lugar de "Sentimiento Prom. flipeado"
- `tsc --noEmit` clean
- `next build` clean
- Sin dependencias residuales a `sentiment.ts` (`grep -r adjustSentimentScoreForRole src/`)

### Día 4 · Backfill + Validación + Cierre

**Quién:** Claude (autor) · CEO (validación visual)

**Ajustes code-reviewer 2026-04-24 (D-OPS-10):**
- Backfill DEBE actualizar `clasificacion_origen='human_admin'` para los 95 posts pre-clasificados manualmente por equipo MD en sprint NLP framework 2026-04-13. Sin este paso, esos 95 posts quedarían como `ai_suggested` por accidente del default de la migración.
- Pre-flight check antes de aplicar migración: confirmar `\d social_posts` y `\d dirigentes` no contienen las 4 columnas, confirmar `alembic heads` = `s5m1_onboarding_tables`.

**Acciones:**
1. Script `backfill_target_politico.py` corre sobre Piña + Ballesteros + Máynez + Solano + Pineda + Nolasco + Jiménez + Cravioto
2. Lotes de 50 posts · idempotente · `WHERE target_politico IS NULL OR nlp_model_version != 'crece-political-v1'`
3. **Backfill semántico inicial**: identificar los 95 posts del sprint 2026-04-13 (filter por `topics_extracted` no nulo + classified prior to 2026-04-18) y `UPDATE social_posts SET clasificacion_origen='human_admin' WHERE id IN (...)` antes del IA backfill. Esos 95 posts quedan respetados sobre IA en queries del KPI.
3. Validación cruzada visual:
   - Piña: KPI "Actividad Alineada · X%" coherente · sin "Negativo -50%"
   - Ballesteros: idem
   - Posts personales (Copa Naranja) NO contaminan KPI
   - Posts críticos al gobierno cuentan en favor
4. Update `.context/STATUS.md` + `DECISIONS.md` con D-23-G' cerrado
5. Cierre incidente: `B-23-03` motor sentimiento con afiliación · pasa de "ESTRUCTURAL §9.8" a **RESUELTO via reframe**
6. Smoke test Playwright en local: `/dashboard/dirigentes/1`, `/8`, `/7`

**Done:**
- 100% posts piloto clasificados con `target_politico`
- KPI coherente para 8 dirigentes
- `B-23-03` cerrado en BLOCKERS.md
- Disenso D-23-G' resuelto en DECISIONS.md
- `sentiment.ts` no aparece en bundle (`grep -r sentiment.ts src/` debe regresar 0 archivos)

---

## Cuello de botella · Day 4 backfill

Si Gemini API tiene rate limits o el prompt es inestable, el procesamiento de N posts puede fallar a la mitad.

**Mitigación:** lotes de 50, idempotente con filtro `WHERE target_politico IS NULL`, retry-safe con backoff exponencial. Si falla, próximo run reanuda desde donde quedó.

## Riesgo principal

Falsos positivos en clasificación binaria 4-cat (post genuinamente mixto · ej. "Mientras MORENA arruina, ganamos copa naranja" puede clasificarse como `oficialismo` o `propio`).

**Mitigación aceptada:** F1 macro ≥ 0.80 como gate. Si después de iteración el F1 no llega a 0.80 sobre golden set, abortar a Opción 1 (apagar flip · sentimiento crudo informacional · sin KPI alineación).

## Por qué este plan es definitivo

1. Sin Phase B colgando · KPI no necesita humanos en el loop
2. Más simple que propuestas previas · 4 columnas vs 10 · 4 días vs 5+
3. Semánticamente honesto · cliente lee porcentaje sin necesidad de explicación
4. Forward-compatible si se agrega humano-clasifica después (Phase B opcional)
5. Elimina riesgo legal LFPDPPP · IA solo identifica intención · no decide sentimiento
6. Disuelve disensos abiertos · D-23-G' cerrado · #12 BLOCKER cerrado
7. Recupera valor de migración 3d6fe3f sin restaurar 11 columnas NLP completas

---

## Decisiones de protocolo confirmadas

- **D-OPS-08** · migración hand-written · firma `Migration reviewed: upgrade N ops, downgrade N ops, rationale: ...` en commit
- **D-OPS-09** · commit atómico solo migración · sin mezclar con código backend/frontend
- **D-OPS-10** · code-reviewer subagent (auditor independiente) lee diff completo · CEO firma diff antes de aplicar
- **Karpathy 2-3** · solo se tocan archivos necesarios · cero refactor adyacente

## Trazabilidad

- Plan supersedido: `SPRINT-23E-INVESTIGACION.md` (motor sentimiento 4-fases con disenso CEO)
- Disenso CEO 2026-04-23 sobre 4-fases: archivo a `archive/` post-cierre Day 4
- Decisión nueva: D-23-H · Reframe KPI Sentimiento → Actividad Alineada (a documentar en DECISIONS.md al cierre)
