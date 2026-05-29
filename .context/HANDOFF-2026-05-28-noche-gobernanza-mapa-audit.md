# HANDOFF — Sesión 2026-05-28 noche · Gobernanza + MAPA + Auditoría

**Status:** Sesión productiva, punto de corte limpio. Próxima sesión retoma con SessionStart hook + esta página.
**Reason for handoff:** /compact + nueva sesión para tener contexto fresco antes de avanzar §2 del MAPA y resto de pendientes.

---

## ⚠️ LEER PRIMERO

1. **Marco de trabajo nuevo:** `.context/governance/MODELO-TRABAJO-AUDIT.md`. Antes de redactar cualquier doc o sección, aplicar checklist 7 pasos pre-redacción + plantilla evidencia (8 tipos de cita) + 6 principios duros (los 2 últimos son sub-reglas agregadas hoy tras auditoría: absolutos requieren query SQL, sesgo CRUD simétrico no se asume).
2. **Auditor independiente:** Gemini, invocable con prompt canónico de `.context/governance/PROMPT-AUDITOR-GEMINI.md`. Validado en producción esta sesión.
3. **Regla dura permanente:** [feedback_buscar_codigo_antes_proponer](../../.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/feedback_buscar_codigo_antes_proponer.md) — antes de proponer ANYTHING: grep en backend/+frontend/, leer si existe, declarar 0 matches si no, NUNCA antes.

---

## What was done — sesión 2026-05-28 (noche)

### Pipeline radar→crece residual (mañana/tarde de hoy, contexto)
- Hugo (Marx, peer radar) entregó 2 paquetes que se ingestaron a CRECE :5438:
  - 18 parents (3 reels FB + 9 YT + 6 X) — fix de `raw_data->>'url'` en CRECE permitió linkear 2,753 reactions vía `url_to_post` fallback.
  - 58 comments YT/X — pre-transformados con aliases para compatibilidad con `ingest_radar_comments_payload.py`, ingestados 53 nuevos (5 ya existían).
- Estado coverage: Balles 24,669 rx (100%), Piña 10,941 rx (96%), Saymi/Pepe/Gaby/Solano/Felipe completos.
- **Residual pendiente:** reel Piña 3982 = 495 rx (no es 1 url mismatch — son 12 posts FB distintos que comparten `platform_post_id_numeric=3982265445406416` por roll-up FB de feedback_id). Requiere FASE B con cookies CEO. Documentado en `.context/HANDOFF-2026-05-28-radar-ingest-pendiente.md`.

### Gobernanza documental (tarde/noche de hoy)
- **CEO marcó deuda organizacional reiterada** ("reiteradas veces pedido"): falta de manuales operativo/organizacional/normativo/producto en CRECE → patrón sistémico.
- Se creó `.context/governance/`:
  - `README.md` (manual de manuales · 2.4 KB)
  - `MODELO-TRABAJO-AUDIT.md` (template + checklist 7 pasos + plantilla evidencia 8 tipos cita + protocolo Gemini · 7.6 KB)
  - `PROMPT-AUDITOR-GEMINI.md` (prompt canónico copiable · 5 KB)
- Carpeta `.context/audits/` (ya existía con historial) recibe reportes Gemini.
- **Hallazgo:** `.context/` NO está totalmente gitignored — solo patterns específicos (`HANDOFF`, `apify_*.json`, `screenshot-*.png`, `exports/`, etc.). Mis `.md` SÍ son trackeables. Hay precedente: 6+ `AUDIT-*.md` ya en repo.
- En RADAR (radar peer): Marx replicó la estructura en `docs/governance/` (su `.context/` está gitignored). Commit bbfe60d en radar repo. Adoptó el checklist 7 pasos + el prompt canónico (que él no tenía).

### MAPA-FUNCIONAL Sección 1 — Aceptación + Fans/Perfiles
- Documento creado: `.context/MAPA-FUNCIONAL.md` con §1 sólida + §2-10 esqueletos honestos marcados `📝 A documentar`.
- §1 documenta: 3 vistas FE, 4 endpoints Índice Aceptación + 12 endpoints Watched Profiles + fórmula real de fantasmas + RBAC + cobertura columnas + deuda + 4 preguntas comunes con ruta a la respuesta.
- **Hallazgo principal** (revelación para mi error sistémico): el concepto "fantasma" YA EXISTE en código (`indice_aceptacion.py:313`, fórmula `pct_fantasma = 100 × (followers - unique_commenters) / followers`). 2 horas antes había propuesto enrichment innecesario a Hugo porque no había hecho grep. Costo real registrado en error notebook.

### Pipeline RADAR-CRECE (sección complementaria)
- `.context/PIPELINE-RADAR-CRECE.md` redactado con 2 mitades: RADAR-side (Marx aportó, verificado contra payloads reales) + CRECE-side (Linda, verificado contra adapters + DB + cobertura).
- Incluye gap analysis de 5 features: fans enriquecidos, ghost_score, B05 Plutchik, cobertura RADAR, B07 crecimiento.
- Marx tiene su mitad en `docs/governance/PIPELINE-RADAR-side.md` (radar repo).

### Auditoría Gemini cross-product (primer ciclo)
- Ejecutado vía `gemini --yolo -p "..."` (background, ~5 min, manejó 429 con retry interno).
- **DOC 1 (mío, MAPA-FUNCIONAL §1):** ⚠️ Pasa con ajustes — 2 hallazgos reales:
  - Hook inventado `useCreateWatched()` (sesgo CRUD: asumí porque hay POST endpoint, hay hook FE).
  - Endpoint omitido `POST /aceptacion/watched-profiles/ingest-reactions-bulk` (línea 949-950).
- **DOC 2 (Marx, PIPELINE-RADAR-side):** ✅ Pasa — precisión alta, hallazgo menor: `pepe_hybrid` tiene 82% cobertura de texto (no 0% como decía el doc).
- **Patrón sistémico cross-doc detectado por Gemini:** afirmaciones absolutas ("X nunca hace Y") vs realidad intermitente.
- Reportes guardados en `.context/audits/2026-05-28-{mapa-funcional-seccion-1, pipeline-radar-side}.md` (commiteados).

### Correcciones MAPA §1 (aplicadas post-audit)
- Línea con `useCreateWatched` → "⚠️ Sin hook FE — deuda detectada por auditoría Gemini 2026-05-28".
- Nueva fila en tabla §1.2 para `POST /ingest-reactions-bulk` con cita `:949-950`.
- §1.6 nuevo: historial de auditoría con hallazgos + falso positivo + sesgo declarado (5 dirigentes 4/6/7/58/59 no auditados).

### MODELO actualizado (post-patrón sistémico)
- Principio #5: afirmaciones absolutas requieren query de cobertura SQL, no solo lectura de código.
- Principio #6: sesgo CRUD simétrico — POST endpoint NO implica hook FE, verificar par independiente.

### Meta-lección apareció en cierre (pendiente formalizar en MODELO §5.4 próxima sesión)
Marx defendió razonadamente uno de los hallazgos de Gemini sobre PIPELINE-RADAR-side: el claim "pepe_hybrid no captura texto" era técnicamente correcto (0 texto nativo), Gemini lo interpretó como inexactitud porque DB muestra 82% cobertura, pero ese 82% es 100% del **backfill posterior**, no del engine pepe_hybrid nativo. Defensa con números: `texto_nativo=0`, `texto_post_backfill=82%`, `texto_SIN_backfill=0`. El hallazgo del auditor fue ambigüedad de redacción, NO error sustantivo. **Sub-regla a agregar al MODELO §5.4 (qué hace Linda con el reporte):** los hallazgos del auditor independiente NO se aceptan automáticamente; cada uno se evalúa con evidencia. Si el redactor tiene defensa razonada con datos, se aclara la redacción en vez de "corregir" un claim correcto.

### Memoria persistente registrada hoy
- `feedback_governance_docs_calidad_no_tiempo.md` (CEO pidió reiteradas veces, calidad > tiempo).
- `feedback_buscar_codigo_antes_proponer.md` (HARD RULE: grep antes de proponer).
- Pointers en `MEMORY.md` actualizados.

### Disk cleanup (mediodía)
- +18 GB liberados sin riesgo (docker prune, pnpm store, npm cache, ~/.cache/uv). De 42 GB → 60 GB libres.
- Pendientes mayores: Docker.raw 460 GB físicos con solo 79 GB lógicos (~380 GB recuperables con backup obligatorio + shrink). NO urgente.
- `cedula-docling` container 2.27 GB RAM, ajeno a CRECE, candidate a apagar.

---

## What's left to do (cola priorizada)

### 🔴 Pendiente con peers activos
1. **Ingest export Felipe FB** que Marx entregó hoy: `exports/felipe_handoff_20260528_2133/` (en radar). 197 posts totales (FB 76 únicos vs 85 entity_ids — 9 duplicados cross-scheme pfbid/base64 que mi adapter ON CONFLICT(platform_post_id) podría contar 2×), 184 comments, 129 reactors. **Tarea concreta:** correr `ingest_radar_yt_x_posts.py --platform FACEBOOK --dirigente-id 60 --json <fb-split> --commit` + `--platform TIKTOK` + `ingest_radar_ig.py`. **Verificar dedup por URL antes del INSERT** (mi adapter no dedupea por url default). Confirmar counts a Marx tras ingest.
2. **NLP de los +73 posts nuevos de Felipe** post-ingest: `sentiment_score` vía celery worker `analyze_sentiment.delay()` + tono/target/emotions/topics vía /gemini inline (patrón HANDOFF-nlp-pendientes-284-gemini).

### 🟡 MAPA-FUNCIONAL pendiente (con modelo + auditoría)
3. **§2 Recepción / Diagnóstico Tier 1 (B01-B18).** Servicios `app/services/diagnostico/{er,breakout,matrix_2x2,benchmark,sentiment_plutchik,crisis_spike,growth_attribution,sov,share_like_ratio,humanizacion}_service.py`. Endpoint `/diagnostico/{dirigente_id}`. Hook `useDiagnosticoTier1`. Página `/dashboard/diagnostico/[dirigenteId]/`. Aplicar checklist 7 pasos + sub-reglas #5 y #6.
4. **§3 FODA.** Endpoint `/diagnostico/foda/{dirigente_id}`. Tabla `planes_ia tipo=DIAGNOSTICO`. Página `/dashboard/diagnostico/[dirigenteId]/foda/`.
5. **§4 Planes IA (Estrategia + Contenido).** Generadores `regen_consolidacion_v2.py`, `regen_contenido_v2.py`. Tabs FE en `/dashboard/planes/`.
6. **§5 Clima Político.** `useClimaPolitico`, página `/dashboard/social/clima/`.
7. **§6 Recomendaciones · Mi Evaluación · Reels.**
8. **§7 Overview + Dirigentes.**
9. **§8 Diagnóstico Tier 2** (8 servicios: filtro_realidad, cib_detector, cross_partisan, violencia_politica, rage_click, topic_drift, veda_compliance, promesas).
10. **§9 Configuración + Sistema.**
11. **§10 Admin (no-cliente).**

Cada §X debe pasar por: redacción → auditoría Gemini (`PROMPT-AUDITOR-GEMINI.md` actualizado con ruta y §) → corrección si hay hallazgos → commit.

### 🟢 Otros docs de gobernanza pendientes (orden propuesto)
12. **`ORGANIZACION.md`** — Manual de organización: roles (Linda, Marx/Hugo, Carlos, Joy, CEO), peers `claude-peers` con IDs históricos, handoff protocols, escalation, mapping persona/responsabilidad por área.
13. **`REGLAS.md`** — Consolidar: LFPDPPP compliance + reglas de ingeniería (D-1, D-2, etc.) + error notebook + ADRs disponibles en `.context/audits/D-*.md` + decisiones del CEO no escritas todavía.
14. **`PRODUCTO.md`** — Misión + visión + roadmap + clientes (MC CDMX, posibles Gobierno Oaxaca, etc.) + posicionamiento. Necesita input directo del CEO (no derivable de código).

### 🟡 Residuales radar→crece (Marx async)
15. **Reel Piña 3982 (495 rx)** — Marx tiene 12 pfbid URLs guardados, espera FASE B con Camoufox+cookies CEO para scrape. Si se prioriza, juntar con ingest Felipe en misma ventana.
16. **Ajustar PIPELINE-RADAR-side.md** del lado Marx: corregir afirmación `pepe_hybrid` no captura texto (DB: 82% cobertura).

### 🟢 Misceláneos
17. **Docker.raw shrink** (~380 GB recuperables) — requiere backup obligatorio de volúmenes crece-db, radar-postgres, etc. NO urgente.
18. **`cedula-docling` container** apagar si no se usa (2.27 GB RAM).
19. **PR #56** ya mergeado a main (cb2f422) hoy. Branch `feat/post-ingest-hugo-2026-05-20` activa para continuar.

---

## Key decisions / state

- **Modelo de trabajo definitivo:** `MODELO-TRABAJO-AUDIT.md` rige toda redacción de docs de gobernanza, con 6 principios duros + checklist 7 pasos + plantilla evidencia 8 tipos.
- **Auditoría obligatoria por sección** del MAPA antes de avanzar a la siguiente. Gemini auditor independiente.
- **CRECE `.context/` parcialmente tracked.** Mis archivos `.md` se commitean normalmente. RADAR `.context/` gitignored → Marx usa `docs/`.
- **Estructuras espejadas:** ambos repos tienen `governance/` con los mismos 5 docs base (Marx tiene README + 5 docs + MODELO copiado).
- **HARD RULE permanente:** grep antes de proponer. Sin excepciones.
- **CEO redirigió "calidad > tiempo":** no aceptar compromisos parciales tipo "30% mejor que 0%". Si una tarea requiere 2 sesiones, se hace en 2.

---

## Files modified / created (commits 2026-05-28 noche)

| Commit | Archivos |
|---|---|
| `docs(governance): manual de manuales + modelo + prompt + MAPA + PIPELINE` | `.context/governance/{README, MODELO-TRABAJO-AUDIT, PROMPT-AUDITOR-GEMINI}.md`, `.context/MAPA-FUNCIONAL.md`, `.context/PIPELINE-RADAR-CRECE.md` |
| `docs(governance): correcciones MAPA §1 post-auditoría Gemini + 2 sub-reglas MODELO` | `.context/MAPA-FUNCIONAL.md`, `.context/governance/MODELO-TRABAJO-AUDIT.md`, `.context/audits/2026-05-28-{mapa-funcional-seccion-1, pipeline-radar-side}.md` |

Rama: `feat/post-ingest-hugo-2026-05-20` (mergeada a main esta tarde como `cb2f422`, branch sigue activa para más trabajo).

---

## Open questions / unresolved

- **¿Avanzar §2 MAPA o ingest Felipe primero?** Próxima sesión arranca eligiendo. Ambos son trabajo serio. Si CEO no indica → preferir §2 MAPA porque mantiene el flujo de gobernanza en marcha y el ingest Felipe puede coordinarse con Marx después.
- **¿PRODUCTO.md tendrá input directo del CEO o se redacta solo?** Necesita su voz para misión/visión.
- **¿FASE B (reel Piña 3982 + Felipe deep FB) — cuándo?** El CEO autorizó deep Felipe hoy; reel Piña queda pendiente de su luz verde.

---

## Coordinación con peers

- **Marx (radar, peer ID dinámico `v7luclno`, cwd `~/Projects/radar`):**
  - Está al tanto del MAPA + MODELO + auditoría cross-product.
  - Su `docs/governance/PIPELINE-RADAR-side.md` pasó auditoría Gemini ✅ con ajuste menor pendiente (pepe_hybrid 82%).
  - Próximos pings posibles: cuando se haga ingest Felipe del export que él entregó hoy, cuando se decida FASE B reels.
  - Su commit governance radar: `bbfe60d`.
- **Carlos Amador:** PR #56 ya está en main (cb2f422). Deploy Coolify cuando él decida.
- **Joy:** Sesión paralela CRECE-Negocios B2B, no afecta hoy.

---

## Cómo retomar (próxima sesión)

1. SessionStart hook cargará: MEMORY.md (con pointers nuevos), error notebook (con 2 reglas nuevas), context anchor (`.context/STATUS.md` + `DECISIONS.md` + `BLOCKERS.md` + `PLAN-current.md`).
2. Leer este handoff (auto-detectado por nombre `HANDOFF-2026-05-28-noche-*`).
3. Leer `.context/governance/README.md` y `MODELO-TRABAJO-AUDIT.md` antes de cualquier redacción.
4. Si vas por §2 MAPA: aplicar checklist 7 pasos pre-redacción (grep B01-B18 + leer diagnostico endpoint + hook + páginas + DB + handoffs). Sin atajos.
5. Cualquier propuesta: grep primero, leer el código, declarar 0 matches si no existe. NUNCA antes de eso.
6. Para auditar §2: ajustar `PROMPT-AUDITOR-GEMINI.md` con la ruta y sección nueva, invocar `gemini --yolo -p "$(cat <prompt-file>)"` en background con `nohup`.
