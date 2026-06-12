# HANDOVER-AI — Decisiones extraídas por Sonnet
## Sesión: 58114 | Compactación: 2026-06-04_17:22:00

## Extracto de sesión 2026-06-04

---

### 1. ARCHITECTURAL DECISIONS

**D1 — Misael VIP override sube a 400 (ADR-0007)**
- Decisión: `vip-overrides.ts` Misael reactions 320 → 400. Pedro Carlock llegó a 378 real post-ingest, dejando el override por debajo.
- Razón: 400 > 378 (Misael #1 indisputable) y 400 < 765 (techo de posts FB de Saymi — matemáticamente defendible). ADR-0005 marcado Superseded.

**D2 — Apps tienen roles distintos (confirmado por medición)**
- Vercel (`frontend-zeta-sepia-46`) → backend LOCAL vía túnel persistente → data de hoy. La que usan CEO + Carlos para VER.
- Coolify (`crece.mdconsultoria-ti.org`) → instancia separada de Carlos → data vieja (05-27). Solo demo.
- CRECE local debe permanecer ARRIBA o la Vercel pierde la vista de hoy.

**D3 — Release privado sin GPG aceptado (CEO)**
- Consistente con decisión del 05-30. Riesgo PII conocido y aceptado.

**D4 — `docker exec` para pg_dump NUNCA con `-t`**
- El flag `-t` asigna TTY → CR/LF corrompe el binario `-Fc` → TABLE DATA=0 en el dump. El dump correcto: sin `-t`.

---

### 2. REJECTED ALTERNATIVES

- **`audit-full` pre-deploy:** descartado. Redundante porque CI automático (governance-gate + E2E Smoke) ya corre en cada push. Costo alto injustificado.
- **Skill "deployment-validation-*":** revisadas, descartadas — son prosa/guías, no checks ejecutables.
- **Override Misael en BD:** nunca se toca la BD para overrides VIP (ADR-0002 vigente).

---

### 3. ASSUMPTIONS TO VERIFY

- **Magnitud de duplicados (~228):** el conteo por prefijo de contenido sobre-cuenta. El número real de dups same-platform está sin medir. **No actuar hasta análisis preciso por `platform_post_id`.**
- **Coolify de Carlos:** se asumió que tenía data vieja (confirmado por medición: FODA id=96/05-27). Carlos debe re-restaurar Release `data-snapshot-2026-06-04` — **no verificado si ya lo hizo**.
- **Túnel persistente estable:** el LaunchAgent auto-syncroniza la URL a Vercel cada hora. Si el quick-tunnel rota y el sync falla, la Vercel queda apuntando a una URL muerta.

---

### 4. BLOCKERS / OPEN QUESTIONS

**🔴 B-SAYMI-DUP / B-FELIPE-FB-DUP-9 (nuevo)**
Posts duplicados mismo-plataforma en BD (ej. 12-may aparece 2× en cards "Recepción"). Ejemplos confirmados: `5609/5314` (FB-FB), `7531/9697` (IG-IG). Sprint dedicado requerido antes de DELETE.

**🟡 NLP eficiente en tokens (prioridad CEO)**
El enrich es LLM-por-item (~3-6s × cientos × 7 dirigentes) = gasto alto. Sin solución definida aún (clasificador batch/local, modelo barato, solo-delta son candidatos).

**🟡 Reactors IG de Piña no enlazaron** (`events_in_db=0`, formato media_id). Métrica secundaria, flagueado, sin sprint asignado.

**🟡 SOP-INGEST-RADAR-HANDOFF.md** pendiente de auditoría Gemini independiente (regla MODELO §5).

**🟡 Coolify de Carlos** requiere restaurar Release `06-04`. Cancha de Carlos, coordinado por CEO.

---

### 5. KEY PEER MESSAGES

Ninguna comunicación peer-to-peer (claude-peers-mcp) identificada en esta sesión. Carlos (el otro peer) opera de forma asíncrona coordinado directamente por el CEO, no vía mensajes de agente.

---

### 6. NEXT STEPS (planned, not yet executed)

1. **Sprint dedup:** análisis preciso de duplicados same-platform por `platform_post_id` → distinguir dup-real vs prefijo-colisión vs cross-plataforma (legítimo) → backup → OK CEO → DELETE redundantes (keep 1).
2. **Sprint NLP eficiente:** investigar clasificador batch/local o modelo barato para reducir gasto LLM-por-item. Prioridad CEO.
3. **Carlos restaura Coolify:** `git pull` + pre-vuelo extensiones + backup previo + restore Release `data-snapshot-2026-06-04` + smoke test + borrar Release (PII). Runbook en `DEPLOY-COOLIFY-CARLOS.md`.
4. **Audit Gemini de SOP-INGEST-RADAR-HANDOFF.md** (independiente, regla MODELO §5).
5. **Reactors IG Piña:** investigar formato `media_id` vs `platform_post_id` para que los 3 reactors IG enlazen.
