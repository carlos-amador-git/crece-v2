# Checklist · Pre-reunión 2026-05-10 · Solano + Piña + Ballesteros

**Fuente única de verdad operativa.** Cada item: decidido, en ejecución, o cerrado.

---

## Decidido + ejecutado (cerrar y olvidar)

- [x] Editor HITL backend + frontend implementado y commiteado · `commits 476b397, 820d4d8, c5cbffe, 8ac545c`
- [x] Bug vocab v2 endpoint vs frontend identificado y corregido · commit `7551f6c` aprox (último push)
- [x] CI `e2e-smoke.yml` con trigger automático push/PR · `commit 6d7ca2d`
- [x] `.env.example` actualizado con 11 vars · `commit 8ac545c`
- [x] Disclaimer pre/post matriz documentado · `.context/DISCLAIMER-PRE-POST-MATRIZ-2026-05-09.md`
- [x] Decisiones documentadas · D-HITL-1, D-NLP-X, D-BR-1, D-BR-2 en DECISIONS.md
- [x] Modalidad reunión: híbrida (5 min demo + paralelo)
- [x] Volumen: `n_comments=80, n_posts=30` ≈ 55 min anotación + 25 min discusión = 1.5h reunión
- [x] Credenciales VIEWER de los 3 dirigentes confirmadas · permission ya permite editar SU dirigente

## Decidido pero NO ejecutado (todavía pendiente)

### 🔴 Bloqueantes para reunión

- [ ] **Gemma vía Coolify clasificar posts** (Q1=A) — script `nlp_layer2_gemma_bg.py` adaptado para posts + Coolify URL. **Sin esto, sección posts del editor estará vacía mañana.** Owner: Linda. ETA: ~30 min adaptación + ~110 min runtime sobre 60 posts (20 × 3 MC).

- [ ] **Verificar deploy Vercel del último commit** del branch `feat/phase-b-pesos-editables` con fix vocab. Owner: CEO. Si Vercel no auto-deploy, correr `vercel deploy --prod` desde frontend/.

- [ ] **`alembic upgrade head` aplicado en BD producción** para que tabla `hitl_edits_log` y columnas `review_status` existan. Owner: Linda (este Mac Mini = producción según hostname).

- [ ] **Smoke E2E con cuenta `solano@crece.mx`** — login → entrar a `/dashboard/settings/evaluacion-nlp` → cargar sample → 1 edit → audit log. Owner: Linda + CEO (verificar en su laptop).

### 🟡 Importante pero no bloqueante

- [ ] **Cambiar default `days=30` → `days=90`** en frontend para que Solano (24 comments NLP) vea sample útil. Owner: Linda.

- [ ] **Brief 1-pager vocab v2** con 7 tonos + 7 targets + 1 ejemplo cada uno. Owner: Linda. Para dirigentes que no recuerden criterios.

### 🟢 Post-reunión preparado

- [ ] **`hitl_review_batch.py` listo para correr** con audit del día (ya commiteado, solo verificar comando). Owner: Linda.
- [ ] **Plan de ampliación matriz** con reglas que las anotaciones revelen. Owner: Linda + firma CEO.
- [ ] **Plan recompute global tras matriz ampliada**. Owner: Linda.

---

## Sprint paralelo · branches recovery

**Estado:** suspendido temporalmente por prioridad reunión.

- [x] Fase 1 inventario base (18 ramas)
- [x] Fase 1.B análisis infra
- [x] Pre-req CI (commit 6d7ca2d)
- [x] Pre-req `.env.example` (commit 8ac545c)
- [ ] Fase 2 decisiones por rama firmadas CEO · post-reunión
- [ ] Fase 3 ejecución PRs Tier 1 LOW → HIGH
- [ ] Fase 4 política operativa

---

## Próximo paso INMEDIATO

Adaptar `nlp_layer2_gemma_bg.py` para Coolify + posts + ejecutar en background. Sin más preguntas, sin más revisiones. Reporto cuando arranque y cuando termine.
