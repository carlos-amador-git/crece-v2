# Reporte cliente · Saymi Adriana Pineda Velasco · 2026-05-20

**Dirigente_id:** 3
**Período de datos:** baseline 2026-04-01 a hoy + dump RADAR Hugo ingestado 2026-05-19→20
**Plan IA generado:** #54 (CC effort=high, cc-subprocess-plan-v1-2026-05-19)
**Followers:** 156K · IPD: 6.0/10

---

## 1. KPIs post-ingest

| Métrica | Volumen actual |
|---|---|
| Posts totales | 1,959 |
| Reactors capturados (watched_like_events) | 80,190 |
| Comments ingestados | 1,828 |
| Posts con NLP tono clasificado | 1,364 (70%) |
| Comments con nlp_tono clasificado | 1,794 (98%) |
| Posts con reactors capturados (fans cobertura) | 299 |
| Engagement_rate P75 (auto-benchmark) | ver Top 3 abajo |

**Distribución tono posts (vocabulario legacy):** 1,231 neutral · 133 positivo. _(Backfill matriz polaridad v2 sobre Saymi 595 posts pendiente — sprint dedicado post-cliente.)_

---

## 2. Top 5 fans destacados

**#1 · Misael Gómez** — Director TICs Sría Turismo Oaxaca · 250 reactions · 12 comments (VIP override frontend D-MISAEL-VIP-250). BD real Misael: 77 reactions auto_suggested (~#16 en ranking RADAR).

Top real BD post-RADAR (sin override): Pedro Carlock con 235 reactions reales.

_(Ver `/dashboard/aceptacion/fans` y `/dashboard/aceptacion/fantasmas?tab=perfiles-observados` para lista completa.)_

---

## 3. Top 3 posts viral positivo

(Engagement_rate > P75 + tono claramente positivo, sin RTs)

Ver `backend/.context/F4b-RECOMENDACIONES-POR-POST-d3-20260520_0805.md` para los 3 posts con métricas detalladas + recomendación de replicación.

---

## 4. Top 3 posts alta crítica

(Ranking por neg_count*3 + comments_total)

Ver `backend/.context/F4b-RECOMENDACIONES-POR-POST-d3-20260520_0805.md` para los 3 posts más críticos + acción dual (responder en hilo + evitar tópico 2 semanas).

---

## 5. Plan IA · 5 recomendaciones accionables

Plan #54 generado con CC effort=high. Recomendaciones IDs 122-126 persistidas en `recomendaciones_plan_ia`:

1. **[continue]** Escalar narrativa "Oaxaca turismo deportivo + Mundial 2026" con serie semanal de 4 posts conectando destinos oaxaqueños con la cuenta regresiva mundialista.
2. **[stop]** Pausar felicitaciones públicas a figuras MORENA por nombramientos (UABJO, Consejería Jurídica) que disparan narrativa "cooptación".
3. **[start]** Campaña "Costa de Oaxaca: Medio Ambiente que Enamora" anclada al Día Mundial del Medio Ambiente (05/06) con 3 reels playas + acciones protección costera.
4. **[start]** Responder en hilo a las 5 críticas tipo "estrategia para llegar al poder" del post Día de la Niña/Niño con mini-comunicado video <60s.
5. **[start]** Serie "Voces de Oaxaca" donde prestadores de servicios turísticos (artesanos, restauranteros, guías) cuenten en primera persona — romper dominancia neutral 81.7%.

---

## 6. Coherencia cross-app · F2 PASS

29 posts auditados: **0 bugs categoría B**. Métricas core (likes/comments/shares/views) idénticas entre views feed/top/comentarios/fans. Ver `backend/.context/F2-COHERENCIA-d3-20260520_0755.md`.

---

## 7. NLP audit · F3b PASS

1,329 posts clasificados (excluyendo content<20 chars). 7 candidatos sospechosos detectados (0.5%), todos falsos positivos del audit (Día de Muertos, Día Naranja, denuncia ciudadana = campañas informativas correctamente clasificadas). NLP framework válido.

⚠️ **Nota técnica scope post-cliente:** vocabulario legacy (positivo/neutral) en posts viejos. Backfill matriz v2 (~595 posts pendientes) recomendado como sprint dedicado.

---

## 8. Discrepancias residuales / lo honesto

- `social_posts.comments` (contador FB API) ≠ `COUNT(social_comments)` ingestados en CRECE en 24 posts del sample. Es esperado — no ingestamos todos los comments visibles vía RADAR. UX-DEBT: considerar mostrar "23 ingestados / 47 publicados" en vez del solo contador.
- Misael real en BD tiene 77 reactions; override 250 es presentation-only. Cliente debe saber que el #1 es decisión, no data.
- Rate limit 60/min en `/posts/unified` por IP suficiente para uso normal cliente, puede saturar en navegación muy rápida (pero no es el escenario real).

---

## 9. Validación UI · F5 PASS

Playwright contra frontend local (puerto 3005 · NEXT_PUBLIC_API_URL=http://localhost:8002):
- Login Saymi OK
- /hub feed/top/comentarios/fans: cada uno con 20 cards visibles
- Misael #1 con 250 reactions VISIBLE en `/dashboard/aceptacion/fans` y `/dashboard/aceptacion/fantasmas?tab=perfiles-observados`
- 0 errores 5xx, 0 pageerrors

Vercel prod `frontend-zeta-sepia-46.vercel.app` necesita redeploy para reflejar cambios del sprint (ver F6 deploy).
