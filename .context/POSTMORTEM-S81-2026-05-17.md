# POSTMORTEM S-8.1 · Ingest reactors Saymi → Misael comparativo

**Fecha:** 2026-05-17
**Sprint:** S-8.1 · `POST /api/v1/aceptacion/watched-profiles/ingest-reactions-bulk`
**Solicitado por:** CEO (instrucción "asuman responsabilidades, dame diagnóstico")
**Participantes:** Linda (CRECE v2) · Juan (md-research, peer 21fuse1f)
**Caso de negocio:** Validar si los 13 contactos curados por Misael (Director TICs Sría Turismo Oaxaca) reaccionan a posts de Saymi.

---

## 1. Resultado vs expectativa

| Métrica | Valor real | Target retrospectivo razonable* |
|---|---|---|
| Likes reales Saymi FB (BD post-backfill) | **27,330** sobre 124 posts | — |
| Comments reales Saymi FB en BD | 1,765 totales / 415 capturados con texto | — |
| Reactors capturados por Juan | **176** | ≥5,000 (para muestra estadística mínima) |
| **% cobertura reactors** | **0.64%** | ≥50% |
| Posts con reactors recuperados | 9 de 161 (5.5%) | ≥80% |
| Posts en BD que matchearon vs envelopes Juan | 3 de 9 (33%) | ≥90% |
| **Matches lista Misael (13) ↔ reactors (176)** | **0** | — |

`*` Targets retrospectivos — **NO fueron acordados en planning**. Esa es exactamente la falla compartida #11. Se muestran solo como referencia de "lo que debió haberse pedido". El problema raíz no fue "fallar contra metas explícitas" sino "no haber fijado metas".

**Veredicto:** entregable no permite validar caso de negocio. 176/27,330 es muestra estadísticamente irrelevante.

---

## 2. Fallas de Linda (CRECE)

### Coordinación / planificación
1. **Nunca definí criterio de aceptación cuantitativo del corpus.** Acepté "lo que Juan pudiera entregar" en lugar de "necesito X posts × Y reactors mínimo por post o no entregues".
2. **Diseñé endpoint flexible para CUALQUIER input** en lugar de validar `len(envelopes_with_reactors) >= len(posts_published) * 0.5` y rechazar si no.

### Verificación técnica
3. **Acepté pfbid como key sin sondear estabilidad.** Tardé 3h en encontrar (con SQL) que pfbid rota por sesión. Una query de 5 min al inicio hubiera ahorrado ese ciclo.
4. **Pedí "FB user_id RAW (numérico)" contradiciéndome con acuerdo previo del 2026-05-16.** Juan me lo recordó textualmente. Falla de no leer mi propio historial.
5. **Acepté `story_fbid` como OPCIONAL en endpoint** cuando debió ser REQUIRED desde sprint 1. Juan tuvo que re-correr 16 min extra.

### Estimación / capacidad
6. **Estimé Apify $0.10 sin consultar runs históricos.** Real fue $0.33. Pude haber leído `apify_refresh_all` logs previos antes de prometer cifra.
7. **MAX_FB_POSTS=80 cuando target real era ~120-150** (Saymi postea 3-5/día × 30 días). Backfill se cortó dejando gap 04-19 → 05-06 que cubrió 6/9 envelopes Juan.

### Comunicación
8. **Framing 4 opciones cuando 1+1 era suficiente.** CEO corrigió explícitamente. Patrón de exhaustividad como velo de inseguridad.

---

## 3. Fallas de Juan (md-research) — reportadas por Juan en autocrítica

### Críticas confirmadas (las que Linda flageó)
1. **Modal abrió en 5.5% NO era esperable.** Saymi tiene ~220 likes/post promedio. La mayoría DEBERÍA haber abierto modal. "5.5% normal" fue racionalización sin ground truth.
2. **53 envelopes low_engagement skipped sin método alternativo aplicado.** Era item #1 de su backlog. Entregó sin ejecutarlo. 33% del corpus skipped es finding gigante que debió flagearse como riesgo, no aceptarse como output.
3. **story_fbid como deuda inicial.** No se le ocurrió. Asumió que `post_url` con pfbid era stable identifier. Karpathy "Think Before Coding" pisado.
4. **post_date ±4 días sin caveat prominente.** Resolución semanal del parser `_parse_fb_relative_timestamp` no documentada. Solo salió cuando Linda detectó discrepancia de 4 días.
5. **profile_external_id mixed username/numeric — riesgo JOIN downstream no evaluado.** Cerraron schema sin sample con `compute_watched_hash` para validar JOIN.

### Las 5 adicionales que Juan identificó (Linda NO las vio)
6. **[LA RAÍZ] Métrica de éxito wrong.** Validó `completeness = captured / badge_count_que_FB_mostró` en lugar de `coverage = captured / ground_truth_independiente`. Toda su verificación fue contra FB mismo, no contra Apify. **Por esto el 99.3% del Saymi 149 le pareció "IN" cuando era 100% del subconjunto que FB le dejó ver.** Este es THE error metodológico — los otros derivan de aquí.
7. **"Verdict IN" declarado con 1 post de validación.** Sprint 0 fue Saymi 149 únicamente. Antes de escalar a 161 posts debió samplear 5-10 posts diversos (text/video/share/reel/low/high engagement).
8. **NO investigó los 99 posts "sin badge".** 61% del corpus marcado no_badge. Asumió "posts sin engagement". Con 240K followers, Saymi NO tiene posts con cero engagement. Esos 99 posts TIENEN reactions pero `find_main_post_reactions_badge()` no las encuentra. Probable: tipos de post (video, reel, share, image-only) tienen UI distinta.
9. **NO clasificó por tipo de post.** Helper trata todos iguales. FB renderea distinto: regular text, video, reel, share, photo album, link share. Extractor probablemente solo funciona para "regular text post" — el resto falla silenciosamente.
10. **NO pidió cross-check Apify ANTES del E2E.** Apify backfill Linda corría en paralelo. Pudo pedir 1 cruce ("1 post Saymi, mi helper vs Apify, coinciden?") antes de declarar JSON listo. Lo hicieron solo en E2E final.

---

## 4. Fallas compartidas (planning conjunto, 50/50)

11. **Schema bilateral cerrado sin criterio de aceptación cuantitativo.** Acordaron el cómo (campos, formato) sin acordar el qué (cobertura mínima %, tipos de post target, ground truth para validar). Ambos responsables.
12. **NO Sprint 0 E2E test con 1 post antes del corpus completo.** Hubiera sido: 1 post Saymi → helper Juan → endpoint Linda → BD → cross-check vs Apify. Esa corrida hubiera mostrado el 0.64% **inmediatamente**.
13. **Asumimos "engagement extraíble = engagement total"** sin cuestionar cómo FB limita visibilidad del modal para non-friends de figuras públicas (240K followers Saymi). Probable que FB le mostraba solo fracción del modal real. Investigación nunca hecha.
14. **NO validamos overlap esperado ANTES de invertir 4h.** Una query de 1 min ("¿cuántos comments en BD tienen autor con handle de los 13 de Misael?") hubiera dado señal de probabilidad baja de hit. Saltaron a implementar.

---

## 5. Lo que NO es falla de nadie

- **0/13 lista Misael ↔ reactors.** Es finding de negocio, no técnico. Saymi probablemente tiene audiencia distinta a la que Misael curó. Información valiosa para Saymi/Misael:
  - O la lista Misael no representa audiencia FB activa
  - O el corpus 9 posts es muy chico para tener overlap
  - O reaccionaron a posts viejos fuera del scope de Juan
- **pfbid session-specific** es característica de FB, no error de Juan.

---

## 6. Lecciones operativas (qué cambiar)

### Para Linda
- **A1.** Antes de aceptar cualquier ingesta externa: definir SLO numérico (cobertura mínima %, fechas críticas, tipos de datos requeridos vs opcionales). Sin SLO no se arranca.
- **A2.** Antes de codificar contra schema externo: 1 query SQL contra BD usando una muestra real de 1 record. 5 min ahorran horas.
- **A3.** Estimaciones de costo (Apify) deben venir de runs históricos en el mismo proyecto, no de número intuitivo.
- **A4.** Framing al CEO: arrancar con la mejor opción + 1 alternativa. Nunca 4 opciones.

### Para Juan
- **B1.** Promover regla "Verificar fuente primaria antes de scoring/diagnóstico" (active 6+ misses) a CLAUDE.md global como hard rule.
- **B2.** Toda métrica de cobertura DEBE validarse contra ground truth INDEPENDIENTE (no la misma fuente que se está scrappeando).
- **B3.** Sprint 0 con 1 muestra ≠ verdict. Sprint 0 requiere N≥5 muestras diversas.
- **B4.** Clasificación por tipo de post + reporte de cobertura por tipo es obligatorio en extractores DOM.

### Para coordinación (Linda ↔ Juan)
- **C1.** Schema bilateral debe incluir sección "Success Criteria" con cobertura mínima cuantitativa.
- **C2.** Sprint 0 E2E obligatorio con 1 post antes de escalar a corpus completo.
- **C3.** Cross-validation entre fuentes independientes (Juan extractor vs Apify) ANTES de declarar JSON listo, no después.

---

## 7. Estado actual de la BD (lo que NO se rolleó)

- 13 cliente_seed Saymi intactos (lista Misael).
- 154 watched_profiles auto_suggested (de Juan, ingestados E2E).
- 320 watched_like_events (3 posts matcheados × ~107 reactors promedio).
- 124 posts Saymi FB (92 pre-backfill + 32 nuevos del Apify run).
- Cobertura BD: 2026-04-14 → 2026-05-17 con gap 04-19 → 05-06.

CEO no ha autorizado cleanup. La BD queda como está hasta nueva orden.

---

## 8. Acciones pendientes (sin ejecutar — esperando orden CEO)

### Operativas (sobre los datos / código)
- [ ] ¿Limpiar 154 auto_suggested + 320 events del E2E?
- [ ] ¿Re-correr Apify con cap 150 para cerrar gap 04-19 → 05-06? (~$0.30, saldo INICIAL $0.41)
- [ ] ¿Solicitar a Juan sprint #1 (método alt low_engagement + clasificación por tipo de post)?
- [ ] ¿Commit del endpoint S-8.1 + parametrización Apify + cleanup BLOCKERS?
- [ ] ¿Pivotar a Instagram (donde quizás los 13 SÍ tienen overlap)?

### De gobierno (sobre las reglas globales del agente)
- [ ] **Aprobar promoción de regla "Verificar fuente primaria antes de scoring/diagnóstico" a hard rule en `~/.claude/CLAUDE.md` global.** Sustento: notebook `~/.claude/skills/learned/writing-review-list.md` la marca `active needs hard rule` con 6+ misses entre Linda y Juan en una sola sesión (Juan-2026-04-11 Skill Vault + Juan-2026-05-14 audit-security + Juan-2026-05-15 RADAR + Juan-2026-05-17 helper FB + Linda-2026-05-17 pfbid). Si CEO aprueba, Juan se ofreció a escribir la sección del CLAUDE.md.

Decisión de cada uno la toma el CEO. No actuamos sin orden.
