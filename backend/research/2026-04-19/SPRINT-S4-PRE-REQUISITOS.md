# Sprint S4 Plan IA · Pre-requisitos §9.8 · 2026-04-19

**Solicitado por CEO** para revisión §9.8 previa al arranque autónomo Sprint-Implement del S4. S4 es crítico del MVP (cierra D-17). 3 pre-requisitos resolverse antes de fire agents + 2 observaciones operativas incorporadas al scope.

---

## T-1.1 · Seed promesas_dirigente (desbloquea B16)

**Qué:** poblar tabla `promesas_dirigente` para los 8 dirigentes piloto con 5-15 promesas verificables c/u (contexto público + fuente).

**Diseño:**
- Script `backend/scripts/seed_promesas_piloto_s4.py` — idempotente · estructura cada fila: `{dirigente_id, texto_promesa, fecha_compromiso, estado: 'pendiente', evidencia_url}`
- Endpoint admin `POST /api/v1/admin/promesas` (minimal) para que MD pueda añadir/editar post-seed · scope S4 no sprint separado
- Fuente inicial: promesas extraídas manualmente de declaraciones públicas de los 8 dirigentes (research 30-45 min CEO o delegable a un agent)

**Criterio acceptance:** al re-correr B16 endpoint `GET /api/v1/diagnostico_tier2/1` Piña debe pasar de `insufficient_data` a `ok` con conteos reales.

**Decisión pendiente CEO:** ¿MD genera las 40-120 promesas iniciales o se difiere a Onboarding S5 donde el cliente las declara? **Recomendación Joy:** MD seed de arranque (10 promesas Piña mínimo para demo comercial) + Onboarding edita/añade post-venta. Alineado con D-22 pero con fixture mínimo explícito.

---

## T-1.2 · Calibrar 3 umbrales operativos

Umbrales empíricos del Sprint S3 que Plan IA S4 necesita como entradas binarias/categóricas:

### (a) Topic Drift threshold (normal vs anómalo)

- B14 produce `drift_score` 0-1. Actualmente saturado (~0.997 por Jaccard bigram sobre captions cortos).
- **Decisión operativa:** hasta que B14 migre a TF-IDF cosine (gap S4), usar threshold por **delta vs baseline dirigente** en lugar de absoluto:
  - `normal`: drift_score dentro de ±15% del promedio últimos 30 días del dirigente
  - `anomalo`: drift_score >15% por encima del baseline del dirigente
- Plan IA recomienda revisión solo si `anomalo` en ventana 7 días consecutivos

### (b) CIB confidence mínimo para recomendación Plan IA

- B12 devuelve `confidence_score` 0-1 + lista `flagged` por heurística (maestros ceremonias + coro + account age).
- **Decisión:** Plan IA solo menciona CIB en recomendaciones si `confidence >= 0.70` (umbral conservador).
- Por debajo de 0.70, la señal queda en dashboard pero NO genera recomendación accionable.
- **Observación CEO integrada:** ninguna recomendación acciona bloqueo/reporte de cuentas flagged sin human-in-the-loop explícito §3.6. Plan IA SUGIERE revisión, MD review confirma, cliente decide. NO auto-block.

### (c) Humanización target por perfil §1.5

| Perfil | Score target | Umbral "needs action" |
|---|---|---|
| `politico_activo` | 45-65 (balance institucional/humano) | < 35 · Plan IA sugiere más contenido personal |
| `funcionario_gobierno` | 25-45 (preferencia institucional) | < 15 o > 55 · ajuste direccional |
| `figura_precampaña` | 50-70 (humanización alta para conexión) | < 40 · crítico pre-electoral |
| `empresario_transicion` | 35-55 (autoridad + calidez) | < 25 o > 65 · desbalance |

Piña actual = 15.14 · perfil `politico_activo` → **needs action** (<35). Plan IA debe sugerir acciones concretas post-drill-down T0.5.

**Entregable:** `backend/research/2026-04-19/UMBRALES-OPERATIVOS-S4.md` con los 3 umbrales formalizados + justificación + path de calibración cuando haya más data piloto.

---

## T-1.3 · Estructura formal del prompt LLM Gemma 3:12b (decisión arquitectural del corazón del producto)

**Qué:** diseño del prompt que Plan IA ejecuta para generar recomendaciones Start/Stop/Continue con anatomía §2.6.7 obligatoria consumiendo los 18 bloques del diagnóstico.

**Localización propuesta:** subsección nueva `§3.6.X Estructura del prompt Plan IA` en MASTER + archivo vivo `backend/research/2026-04-19/PROMPT-PLAN-IA-v1.md` para iteración.

**Estructura propuesta (secciones del prompt):**

```
1. ROL + RESTRICCIONES DURAS
   - Rol: consultor de comunicación política MX para {dirigente.full_name} ({cargo})
   - Perfil §1.5: {perfil}
   - Restricciones: veda INE activa {veda_bool} · NO lenguaje partidista extremo
     · NO personal attacks · NO recomendar block/report CIB sin human-in-the-loop

2. CONTEXTO DEL DIRIGENTE
   - estrato, followers, data_fidelity_tier por plataforma (18 bloques inputs)
   - competidor_directo_ids: {proxies o client-declared per D-22}

3. DIAGNÓSTICO ACTUAL (18 bloques inyectados como JSON estructurado)
   - 10 Tier 1 + 8 Tier 2 · cada uno con status {ok|insufficient_data} + data
   - Incluir el contexto D-19 explícito ("benchmark IM comercial sobre-estima
     ~100× ER político MX")

4. EVIDENCIA COMERCIAL OBSERVACIÓN CEO §9.8
   - Si B13 Filtro Realidad delta ≥ 10%, el prompt INCLUYE narrative:
     "Tu ER orgánico sin CIB es X% vs Y% baseline (CIB infla tus métricas
     Z%, esto es evidencia para tu estrategia)"

5. BEHAVIORAL LIBRARY INJECTION §2.6.7
   - 5-7 principios de economía conductual relevantes al diagnóstico
   - Kahneman System 1/2 · Cialdini reciprocidad/prueba social · Haidt
     foundations · Bail backfire · Tajfel identity

6. TAREA
   - Generar 3-5 recomendaciones con anatomía obligatoria:
     * acción (start|stop|continue) + texto específico
     * ventana temporal (default 14d · configurable)
     * criterio éxito medible JSON
     * principio conductual citado
     * evidencia del post modelo (FK a social_posts si aplica)

7. FORMATO DE SALIDA (JSON estricto)
   - Schema exacto mapeado a tabla recomendaciones_plan_ia §6.3.2
   - temperature=0.2 (balance entre creatividad y consistencia)
   - seed=42 para reproducibilidad en tests
```

**Criterios de calidad del prompt (benchmark S4 T-1.3):**
- Length: 2000-3500 tokens input (dentro de context window Gemma 3:12b)
- Output esperado: 3-5 recomendaciones × ~200 tokens = 600-1000 tokens output
- Tiempo estimado: 30-90s por generación (gemma3:12b warm)
- Success criterion: 80% de outputs parsean como JSON válido sin `_err`

**Human-in-the-loop obligatorio §3.6 MASTER:**
- Todas las recomendaciones generadas entran con `estado='propuesta'`
- Admin panel MD review aprueba/rechaza/modifica antes de exponer al cliente
- Sin este admin gate, Plan IA no sale a producción (criterio acceptance S4)

**Entregable:**
1. `backend/research/2026-04-19/PROMPT-PLAN-IA-v1.md` — prompt completo con los 7 bloques + schema JSON + ejemplo sample
2. Subsección `§3.6.1` nueva en MASTER (o actualización de §3.1 #10) documentando estructura como decisión arquitectural D-24

---

## 2 observaciones operativas CEO integradas al scope S4

1. **B13 Filtro Realidad como narrative comercial** — prompt Plan IA (sección 4 arriba) debe inyectar la diferencia ER orgánico vs ER con CIB como argumento narrativo explícito. Evidencia: Piña delta 16%, dato concreto para convencer al cliente del valor del producto.

2. **Ninguna recomendación acciona bloqueo B12 CIB sin HITL** — integrado en prompt sección 1 (restricciones duras). La recomendación máxima que Plan IA puede generar sobre CIB es "revisar con MD equipo las N cuentas flagged con confidence >=0.70 antes de decidir acción". Nunca "bloquear automáticamente" ni "reportar a plataforma".

---

## Estimación Sprint S4 revisada

- **Pre-requisitos T-1 (1 día):** seed promesas + umbrales + prompt doc
- **S4 core (6-8 días per D-17):** pipeline LLM · prompt engineering · RAG · generación persistente · admin panel MD review · UI cliente decisión · vinculación post ejecutor · seguimiento 14d · cierre automático · bloque #10.7 memoria · reporte semanal
- **Total:** 7-9 días wall-clock

## Criterio cierre §9.8 previo

Los 3 entregables T-1 (seed promesas + umbrales doc + prompt doc) en **PR único** para revisión CEO **antes** de arrancar `/sprint-implement` S4 core. Si el PR se aprueba, arranca ejecución autónoma del S4 core sin checkpoints adicionales hasta el cierre §9.8 final.

---

**Recomendación ejecutiva para CEO:** aprobar T-1 como PR de preparación · al merge de ese PR, arranque inmediato Sprint S4 core en modo Sprint-Implement autónomo. Si algún T-1 requiere input CEO no-delegable (p.ej. qué promesas exactas de los dirigentes), documentar el input en el mismo PR antes de mergear.
