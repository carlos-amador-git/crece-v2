# Reporte cliente · Pepe Monroy · 2026-05-20

**Dirigente_id:** 57
**Período de datos:** baseline + dump RADAR Hugo ingestado 2026-05-19→20
**Plan IA generado:** #55 (CC effort=high, cc-subprocess-plan-v1-2026-05-19)

---

## 1. KPIs post-ingest

| Métrica | Volumen actual |
|---|---|
| Posts totales | 175 |
| Reactors capturados (watched_like_events) | 18,937 |
| Comments ingestados | 693 |
| Posts con NLP tono clasificado | 157 (90%) ← era 25 (14%) antes del backfill F3a |
| Comments con nlp_tono clasificado | 460 (66%) |
| Posts con reactors capturados (fans cobertura) | 146 |

**Distribución tono posts (vocabulario v2):** 65 personal · 44 celebratorio · 21 informativo · 17 propositivo · 3 solidario · 5 positivo (legacy) · 20 neutral (legacy). Backfill F3a clasificó 150 posts pendientes con matriz polaridad v2.

---

## 2. Top 5 fans destacados

Sin VIP override para Pepe. Top real BD (ver `/dashboard/aceptacion/fans?dirigente_id=57`).

---

## 3. Top 3 posts viral positivo

(Engagement_rate > P75 + tono claramente positivo, sin RTs)

Ver `backend/.context/F4b-RECOMENDACIONES-POR-POST-d57-20260520_0805.md` para los 3 posts + recomendación de replicación.

---

## 4. Top 3 posts alta crítica

(Ranking por neg_count*3 + comments_total)

Ver mismo reporte F4b · 3 posts más críticos + acción dual.

---

## 5. Top 3 posts polarizado

(|avg_polaridad| < 0.3 AND sd_polaridad > 0.5 AND ≥5 comments clasificados)

Ver mismo reporte F4b · 3 posts polarizados + recomendación de monitoreo + narrativa unificadora.

---

## 6. Plan IA · 5 recomendaciones accionables

Plan #55 generado con CC effort=high. Recomendaciones IDs 127-131 persistidas en `recomendaciones_plan_ia`:

1. **[continue]** Replicar formato "reto personal medible + valores" del post 04/05 (50 horas ayuno / 20 km) con segunda entrega narrativa video corto disciplina/enfoque vinculado.
2. **[start]** Serie de 3 publicaciones nombrando explícitamente liderazgos municipales (patrón Nicolás Romero/San Mateo Atenco/Atizapán) con foto + handle aliado.
3. **[stop]** Suspender publicaciones tipo Airbnb/coanfitrión del 18/05 que rompen línea editorial política y diluyen tono dominante; reusar franja para contenido proyecto PAZ.
4. **[start]** Pieza temática 05/06 Día Mundial Medio Ambiente vinculando eje "disciplina personal" (reto físico) a compromiso ambiental.
5. **[start]** Convertir post unidad con Hugo Eric Flores (19/05) en mini-serie 2 piezas testimoniales (video 30-60s) articulando QUÉ significa "PAZ fuerte basado en…".

---

## 7. Coherencia cross-app · F2 PASS

20 posts auditados: **0 bugs categoría B**. 15 casos INFO (counter scraper vs comments reales, esperado).

---

## 8. NLP audit · F3b PASS

157 posts clasificados. **0 sospechosos** detectados (0.0% tasa). Vocabulario mixto detectado (legacy 25 + v2 132). Backfill F3a completó la mayoría.

---

## 9. Discrepancias residuales / lo honesto

- 18 posts pendientes de clasificación NLP (175 totales - 157 clasificados). El backfill no clasifica posts con content NULL o muy corto (<20 chars probable filtro implícito).
- Sin VIP override — todos los fans visibles son data real RADAR.

---

## 10. Validación UI · F5 PASS

Login Pepe OK (mismo password `demo2026!`). /hub 4 tabs cada uno con 20 cards. 0 errores reales.
