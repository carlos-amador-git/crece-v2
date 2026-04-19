# Auditoría Gemini — Sprint S0 Validación de Supuestos

**Fecha:** 2026-04-19
**Revisor:** Gemini CLI (audit operativo pre-arranque)
**Scope:** solo Sprint S0 y sus dependencias inmediatas (S1, bloque #05)

---

**VEREDICTO:** Aprobar Sprint S0 con ajustes específicos en T0.4 (Kappa) y T0.5 (Fidelity) para evitar bloqueos por falsos negativos.

---

### 1 · CRITERIOS DE ACCEPTANCE
1. **MEJORA** · **T0.2** · El criterio "recalibrar" es vago. **SUGERENCIA:** Definir que el output sea un archivo `settings_strata.json` que Sprint S1 T2 consuma directamente para evitar ingresos manuales erróneos.
2. **CRÍTICO** · **T0.3** · El criterio "detección CIB" no tiene umbral. **SUGERENCIA:** Declarar "Pass" si detecta >60% de los 200 comments marcados manualmente (baseline ITESO) con <15% falsos positivos.

### 2 · DEPENDENCIAS TEMPORALES
3. **MEJORA** · **T0.2 → S1.T2** · S1 depende de la calibración de S0. **SUGERENCIA:** Asegurar que el script de T0.2 genere el mapeo ID_DIRIGENTE -> ESTRATO exacto para el seed de S1.

### 3 · OUTPUTS VS INPUTS SPRINT S1
4. **CRÍTICO** · **T0.4** · S1 T5 usa Gemma para Topics, pero S0 solo valida Plutchik (Emociones). **SUGERENCIA:** Incluir en la validación ciega de T0.4 la extracción de 1-3 topics (del seed de 12) para validar precisión del prompt de S1 simultáneamente.

### 4 · UMBRAL KAPPA PLUTCHIK
5. **CRÍTICO** · **T0.4** · El umbral Kappa ≥ 0.75 es excesivo para 6 categorías en comments políticos cortos (ambigüedad sarcasmo/enojo). **SUGERENCIA:** Ajustar umbral a ≥ 0.65 (Acuerdo Sustancial) y exigir estrictamente 3 anotadores para permitir desempate (Majority Vote 2/3).
6. **MEJORA** · **T0.4** · 100 comments es estadísticamente al límite. **SUGERENCIA:** Si Kappa resulta entre 0.5 y 0.65, no bloquear S1 pero añadir "Tarea de Refinamiento de Prompt" como T1.9 en S1.

### 5 · TAREAS FALTANTES
7. **CRÍTICO** · **T0.5 (Nueva)** · Validación de lógica `data_fidelity_tier`. **SUGERENCIA:** Añadir T0.5: "Validar algoritmo de asignación T1/T2/T3 contra los 8 dirigentes (ej. Piña debe ser T1 por tener comments, un perfil sin comments debe caer a T2) y documentar en `FIDELITY_LOGIC.md`".
8. **MEJORA** · **T0.6 (Nueva)** · Smoke test failover. **SUGERENCIA:** Ejecutar un `curl` al endpoint de Ollama Coolify para confirmar latencia y disponibilidad antes de codificar el health-check en S1.

### 6 · TIME BOXING (6-8H)
9. **MEJORA** · **T0.4 Execution** · La anotación humana de 100 comments × 3 personas toma ~3h hombre. **SUGERENCIA:** Iniciar T0.4 en paralelo con T0.2 para que los humanos anoten mientras el script de ER corre; de lo contrario, el sprint desborda las 8h.

### 7 · REPRODUCIBILIDAD
10. **MEJORA** · **Documentación** · Los reportes en `backend/research/` suelen quedar huérfanos. **SUGERENCIA:** Cada reporte de S0 debe incluir el `system_prompt` exacto y la `temperature` (0.0 recomendada para validación) usada en Gemma para permitir auditoría posterior.

---
**ESTADO FINAL:** El sprint es operativamente sólido pero corre el riesgo de "fallar" T0.4 por un umbral Kappa idealista. Con los ajustes de umbral (0.65) y la inclusión de validación de topics, el Sprint S0 garantiza un arranque de S1 sin deudas técnicas de lógica.

---

_Generado: 2026-04-19T15:08:08Z_
