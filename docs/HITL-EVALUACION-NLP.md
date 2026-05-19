# Editor HITL · Evaluación NLP

**Versión:** 1.0 · 2026-05-09
**Owner producto:** Linda (CC sesión electoral) · MD Consultoría TI
**Aplica a:** CRECE v2 · pilot Movimiento Ciudadano CDMX

---

## Qué es

Herramienta para que actores políticos (dirigentes piloto) confirmen o modifiquen las clasificaciones automáticas que el sistema asignó a sus posts y comments en redes sociales. Es la pieza human-in-the-loop (HITL) que cierra el ciclo de calidad del NLP de CRECE.

**Modelo:**

```
SISTEMA PROPONE             →    DIRIGENTE DECIDE
(runner Gemma + mapper v3)         (edit directo, audit log)
```

No hay queue de approval intermedia. Cada dirigente es autoridad final sobre la clasificación de SUS datos.

---

## Quién y cuándo

| Rol | Acceso | Acciones |
|---|---|---|
| VIEWER | Solo `user.dirigente_id` | Ver y editar sus posts/comments |
| ANALYST | Cualquier dirigente | Ver, editar y revisar audit |
| ADMIN | Cualquier dirigente | Ver, editar, revisar audit, exportar |
| FIELD_OPERATOR | Sin acceso al editor | — |

---

## Flujo de uso

1. Login en CRECE
2. Navegar a **Dashboard → Settings → Evaluación NLP** (`/dashboard/settings/evaluacion-nlp`)
3. Configurar filtros si se desea (default: últimos 30 días, todas las plataformas, modo cronológico)
4. Revisar las cards de posts y comments una a una:
   - **Si la clasificación está correcta**: clic en "Confirmar como está" → row queda verde
   - **Si está mal**: ajustar dropdown de tono o target, marcar off-topic si aplica, escribir razón opcional, clic "Guardar cambio" → row queda azul
5. La barra de progreso arriba muestra cuántos has revisado de cuántos pendientes
6. Volver mañana retoma donde quedaste (filtro "Solo pendientes" oculta los ya revisados)

---

## Vocabulario v2

**Tono** (7 valores):
- `critico` — crítica fundamentada con argumento
- `propositivo` — sugerencia o alternativa concreta
- `celebratorio` — elogio, felicitación, alegría
- `informativo` — pregunta neutra, dato, comunicado
- `solidario` — apoyo emocional, condolencia
- `ataque` — descalificación personal, ofensa
- `personal` — comentario personal sin valor político claro

**Target** (7 valores):
- `gobierno` — gobierno actual
- `oposicion` — partidos opositores
- `ciudadania` — ciudadanos en general
- `medios` — prensa y periodistas
- `autopromocion` — el propio dirigente o su movimiento
- `tema_especifico` — tema concreto (no actor)
- `dirigente` — el dirigente del post

---

## Off-topic flag

Si un comment es spam, ruido del runner, o no tiene relación con política, marcar `off-topic`. Esto:
- NO modifica `nlp_tono`
- Sí queda registrado en audit log con flag
- Alimenta la lista de candidatos a blacklist runner Gemma en el batch review

---

## Loop con Claude+Gemini (batch driven)

Cada cierto volumen de edits acumulados, Linda corre desde IDE local:

```bash
docker exec -e DATABASE_URL='postgresql+asyncpg://crece:crece_dev@db:5432/crece' \
  crece-backend python /app/scripts/hitl_review_batch.py --since 2026-05-09
```

Output:
- `/tmp/HITL-REVIEW-PATTERNS-{date}.md` — legible (matrices confusión, top patrones, heurísticas)
- `/tmp/HITL-REVIEW-PATTERNS-{date}.json` — input para Claude+Gemini

Linda comparte el MD con Claude (en sesión IDE) y Gemini (vía `/gemini analyze`) y reciben sugerencias:
- Ajustes a G1-G5 del mapper (`backend/app/nlp/matriz_v3_mapper.py`)
- Reglas nuevas a `framework_matrix_defaults`
- Comments para blacklist en runner Gemma

Linda revisa propuestas y comitea las que aplican. Iteración cerrada.

---

## Audit log

Tabla `hitl_edits_log` (inmutable). Cada edit o confirmación deja una row:

| Campo | Significado |
|---|---|
| entity_type | 'post' o 'comment' |
| entity_id | id del post/comment |
| dirigente_id | a quién pertenece |
| from_tono / to_tono | propuesta sistema → decisión humano |
| from_target / to_target | idem |
| off_topic | bool, marcado spam/ruido |
| actor_id | quién editó |
| reason | nota libre opcional |
| edited_at | timestamp |

ADMIN consulta el log:

```bash
GET /api/v1/hitl/audit/{dirigente_id}?since=2026-05-09
```

---

## Recompute de score

Tras un edit, el helper async `recompute_score_comment(db, comment_id)` re-aplica la matriz política v2 (60 reglas en `framework_matrix_defaults`) con:
- `rol_politico` del dirigente padre
- `nlp_tono` y `nlp_target` actualizados (puede pasar por mapper v3.0.1 si están en vocab runner)
- `contexto='comment_tercero'` para comments, `'post_dirigente'` para posts

Score nuevo se devuelve. Las agregaciones del dashboard (KPI Sentimiento Político Ajustado, Actividad Política Alineada) se computan on-the-fly al pedir el endpoint del dashboard, no se materializan.

---

## Limitaciones conocidas

- Cobertura matriz actual: 1.4% (38/2696 comments). El 78% del corpus es `personal × autopromocion` (followers aplaudiendo) sin regla — by-design.
- Posts sin clasificar: 0/4817 con `tono_discurso`. Sección posts del editor estará vacía hasta que se corra el clasificador LLM.
- Corpus desigual entre dirigentes: Solano 24 comments NLP / Máynez 0 vs Ballesteros 784 / Piña 406.

---

## Referencias

- Plan original: `.context/PLAN-2026-05-09-editor-hitl.md`
- Decisión: `.context/DECISIONS.md` § D-HITL-1
- Hallazgo previo: `.context/DECISIONS.md` § D-NLP-X (matriz vacía reparada)
- Triangulación NLP base: `research/memory/2026-04-18-triangulacion-nlp-layer2.md`
