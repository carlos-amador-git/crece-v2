# Political Framework — Matrix Defaults v1

**Versión:** v1
**Fecha:** 2026-04-13
**Escala:** +1 / 0 / -1 (suave, recomendación Gemini)
**Status:** PUBLICADO — cualquier cliente puede auditar estos valores

---

## Principios de diseño

1. **Transparencia radical:** Esta matriz es pública y auditable. Cualquier cliente ve con qué reglas lo medimos.
2. **No es métrica objetiva:** Es una herramienta estratégica interna. Cada cliente puede ajustar ±1 vs default.
3. **Escala suave:** Evitamos extremos (+2/-2) para no crear ilusión de certidumbre donde la política es ambigua.
4. **Matriz rule-based, no ML:** Explicable, auditable, conforme con transparencia algorítmica (INE/LFPDPPP).

## Matriz v1 — los 32 casos cubiertos

### Oposición (dirigente NO pertenece al partido gobernante en su ámbito)

| Tono | Target | Score | Razón |
|---|---|---|---|
| crítico | gobierno | **+1** | Fiscalización efectiva del gobierno en turno |
| crítico | ciudadanía | **-1** | Criticar ciudadanía daña imagen |
| crítico | oposición | **-1** | Disidencia interna opositora |
| crítico | medios | **-1** | Atacar medios es riesgoso |
| propositivo | gobierno | **0** | Propuesta al gobierno: neutral |
| propositivo | ciudadanía | **+1** | Proponer a la ciudadanía construye marca |
| celebratorio | autopromoción | **+1** | Construcción de marca personal |
| celebratorio | ciudadanía | **0** | Celebrar ciudadanía es neutral |
| informativo | tema_específico | **0** | Información neutral |
| solidario | ciudadanía | **+1** | Solidaridad con ciudadanía suma |
| ataque | gobierno | **+1** | Ataque directo al gobierno: efectivo para base |
| ataque | oposición | **-1** | Ataque a aliados opositores: divisivo |
| personal | autopromoción | **0** | Personal sin impacto político |

### Oficialismo (dirigente pertenece al partido gobernante)

| Tono | Target | Score | Razón |
|---|---|---|---|
| crítico | oposición | **+1** | Crítica a oposición desde el poder |
| crítico | gobierno | **-1** | Disidencia interna oficialista |
| crítico | ciudadanía | **-1** | Criticar ciudadanía daña imagen |
| propositivo | gobierno | **0** | Alineación con agenda oficial: esperable |
| propositivo | ciudadanía | **+1** | Propuesta a ciudadanía: suma |
| celebratorio | gobierno | **0** | Celebrar al gobierno propio: esperable |
| celebratorio | ciudadanía | **+1** | Celebración compartida |
| celebratorio | autopromoción | **+1** | Construcción de marca desde el poder |
| informativo | tema_específico | **0** | Información neutral |
| solidario | ciudadanía | **+1** | Solidaridad oficialista: suma |
| ataque | oposición | **+1** | Ataque efectivo a oposición |
| ataque | gobierno | **-1** | Atacar al gobierno propio: muy mal |
| personal | autopromoción | **0** | Personal: neutro |

### Independiente (sin alineación clara, o partido sin poder en el ámbito)

| Tono | Target | Score | Razón |
|---|---|---|---|
| crítico | gobierno | **0** | Crítica sin alineación clara |
| crítico | oposición | **0** | Crítica a oposición: neutral |
| propositivo | ciudadanía | **+1** | Propuesta construye marca |
| celebratorio | autopromoción | **+1** | Construcción de marca personal |
| solidario | ciudadanía | **+1** | Solidaridad construye imagen |
| personal | autopromoción | **0** | Personal: neutro |

---

## Guardrails aplicados

| Guardrail | Implementación |
|---|---|
| **Rangos acotados** | Override máximo ±1 del default. Intentar +2 ó -2 requiere admin MD Consultoría |
| **Audit log** | Cada cambio queda registrado en `framework_audit_log` (quién, cuándo, por qué) |
| **Transparencia UI** | Siempre se muestran **2 scores**: "Tu score" (overrides) + "Score estándar" (defaults) |
| **Permisos** | Solo `role=admin` puede editar. Analystas/dirigentes solo lectura |
| **Versioning** | Matriz tiene `version` — cambios de defaults crean v2, v3, etc. |
| **Validación externa** | (En desarrollo) Comparador contra encuestas Oraculus/Parametría. Alerta si divergencia > 30% |

---

## Ejemplo práctico

### Caso 1 — Piña tuitea "Prometieron no subir la tarifa y lo hicieron otra vez"

1. **Layer 1 NLP:** pysentimiento → sentiment_label=NEGATIVE, score=-0.96
2. **Layer 2 LLM:** Gemma3 → tono=crítico, target=gobierno (identifica que "ellos" = gobierno MORENA)
3. **Layer 3 Framework:**
   - `dirigentes.rol_politico` para Piña = `oposicion` (MC vs MORENA CDMX)
   - Lookup matriz (oposicion, crítico, gobierno) → **score_politico_ajustado = +1**
4. **UI muestra:**
   - Sentiment técnico: -0.96 (negativo)
   - Score político: **+1 "Fiscalización efectiva"**

### Caso 2 — Cravioto tuitea "Acompaño a nuestra Jefa de Gobierno Clara Brugada..."

1. **Layer 1:** sentiment_label=POSITIVE, score=+0.8
2. **Layer 2:** tono=celebratorio, target=gobierno
3. **Layer 3:**
   - `rol_politico` Cravioto = `oficialismo` (MORENA en CDMX donde MORENA gobierna)
   - (oficialismo, celebratorio, gobierno) → **score_politico_ajustado = 0**
4. **UI muestra:**
   - Sentiment técnico: +0.8
   - Score político: **0 "Esperable, no suma"**

### Caso 3 — Si MC-CDMX override

MC-CDMX como cliente decide: "celebrar al gobierno cuando eres oposición es traición".
- Actual default: `(oposicion, celebratorio, gobierno)` → **no existe regla** (caso no cubierto)
- Si MC decide agregar: `score = -1` con override, con razón "traición a la línea opositora"
- Se graba en audit log. Score diverge del default → aparece badge "Tu framework difiere del estándar en 1 regla"

---

## Cambios respecto a propuesta inicial

| Propuesta inicial | Decisión final | Razón |
|---|---|---|
| Escala ±2 agresiva | **±1/0 suave** | Gemini: evita falsa precisión |
| 100% configurable | **Bounded ±1 del default** | Gemini: previene auto-validación perversa |
| Solo score personalizado | **Siempre muestra ambos** | Transparencia, permite comparar |
| Sin auditoría | **Audit log obligatorio** | Trazabilidad para compliance |
| Sin validación externa | **Comparador vs encuestas públicas** | Gemini recommendation |

---

## Archivos relacionados

- **Migration:** `backend/migrations/versions/f7a8b9c0d1e2_political_framework.py`
- **Seed:** `backend/scripts/seed_political_framework.py`
- **Service:** `backend/app/services/political_framework.py`
- **API:** `backend/app/api/v1/endpoints/political_framework.py`
- **Decisión:** `.context/DECISIONS.md` D-NLP-01, D-NLP-02, D-NLP-03
