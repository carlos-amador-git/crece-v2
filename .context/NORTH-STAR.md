# CRECE v2 — NORTH STAR (briefing de apertura de sesión)

**Función:** carga rápida de contexto estratégico para cualquier sesión de Claude Code. NO es SSOT — el SSOT es `CRECE_PRODUCT_MASTER.md`. Este documento es el briefing de 2 minutos; el MASTER es la referencia detallada.

**Regla:** si hay divergencia entre NORTH-STAR y MASTER, gana el MASTER. Este doc se actualiza solo cuando cambia la visión estratégica de producto (~cada 2-3 semanas), no con cada sprint.

---

## ¿Qué es CRECE v2?

Plataforma de inteligencia digital para **políticos profesionales mexicanos** que convierte datos ruidosos de redes sociales en **3 decisiones accionables por semana**. Reemplaza analytics genéricos (IPD 0-10, sentimiento promedio) con 30 bloques específicos + Plan IA Start/Stop/Continue + compliance INE + arquitectura dual-mode por-dirigente.

**Cliente ancla:** Movimiento Ciudadano CDMX (relación MD Consultoría 4+ años).

---

## Los 4 perfiles de cliente

| Perfil | Horizonte | Necesidad central |
|---|---|---|
| 1. Político activo en representación | 3-6 años | Consolidar base + expandir sin sacrificar fieles |
| 2. Funcionario en gobierno | Período constitucional | Narrativa de gestión + anticipar crisis |
| 3. Figura en precampaña | 6-18 meses | Velocidad respuesta + compliance INE veda |
| 4. Empresario/figura en transición | Gradual | Formación + autoridad pública desde cero |

UI/vocabulario/onboarding/pricing adaptables por perfil. Arquitectura común.

---

## Arquitectura dual-mode (decisión defensible)

| Tier | Fuente | Cuándo |
|---|---|---|
| **T1** | Scraping público (Apify/Brightdata) | Baseline universal desde día uno |
| **T2** | Scraping + cookies burner dedicadas (@RafaRamos72) | Infraestructura actual, granularidad |
| **T3** | OAuth oficial Meta por-dirigente | **Post-venta**, cliente firmado |

El mismo dashboard se pinta en cualquier tier con badge `📊 Oficial` vs `📊 Estimación de mercado`. Upgrade es comercial, no técnico — demo gratuita convierte en argumento de venta.

---

## 3 killer features defensibles (ninguna en Brandwatch/Meltwater)

1. **Breakout Scale Brookings Cat 1-6 aplicado a política MX** — detección de cuándo un post cruza fronteras algorítmicas hacia no-seguidores. Proxy direccional en T1/T2, exacto en T3.
2. **Filtro de Realidad con CIB ITESO multinivel** — toggle Orgánico/Raw que apaga trolls coordinados y muestra aprobación real. Captura caso Gálvez 2024 ($75.2M MXN en digital, confundió CIB con apoyo, perdió por 30 puntos).
3. **Arquitectura dual-mode con upgrade comercial por-dirigente** — monetización diferenciada T1/T2 base vs T3 premium. Captura valor incluso cuando cliente no completa upgrade.

---

## Los 30 bloques del diagnóstico (resumen Tier 1)

Los 10 bloques Tier 1 son el MVP mínimo. Sin estos 10 funcionando E2E, no hay producto vendible:

1. ER normalizado por estrato político
2. Breakout Scale Brookings (Cat 1-6)
3. Matriz 2x2 Insignia/Crisis/Vanidad/Muerta
4. Benchmark vs 3-5 competidores directos
5. Sentiment composition Plutchik (6 emociones)
6. Crisis Spike Alert
7. Growth Attribution Time-Decay
8. Share of Voice por tema
9. Share-to-Like Ratio (movilización profunda)
10. Start/Stop/Continue con post modelo linkeado

Los 8 Tier 2 + 12 Tier 3 se desglosan en `MASTER §3`.

---

## Roadmap (3-4 semanas hasta MVP Tier 1+2)

```
Sprint 0 — Validación de supuestos (5-6h) ← EMPIEZA AQUÍ
Sprint 1 — Backend Foundations (4-5h)
Sprint 2 — Diagnóstico Tier 1 (1-2 sem)
Sprint 3 — Diferenciadores Tier 2 (1 sem)
Sprint 4 — Plan IA LLM (3-4 días)
Sprint 5 — OAuth activable (1-2 días, paralelo)
```

**Arranque duro:** Sprint 1 NO inicia hasta que existan NORTH-STAR (este doc) + PRD aprobado + Sprint 0 completo. Ver `MASTER §9.6`.

---

## Estado actual al 2026-04-19

- **Rama:** `feat/eval-benchmark-v1` · PR #12 abierto
- **Última fase cerrada:** triangulación NLP Layer 2 validada + investigación estratégica 4 fuentes cerrada
- **Próximo paso:** Sprint 0 tras aprobación PRD
- **Bloqueadores externos:** ninguno

---

## Ritual obligatorio al abrir sesión

1. Leer este NORTH-STAR (2 min)
2. Leer `MASTER §2` (estado actual) + `MASTER §6` (decisiones vivas) (5 min)
3. `git log --oneline -10` + `git status --short`
4. Reportar al CEO en un párrafo: "entiendo X, último paso Y, siguiente Z. ¿Procedo?"

**No arrancar código sin completar los 4 pasos.**

---

## Referencias

- **SSOT detallado:** `.context/CRECE_PRODUCT_MASTER.md`
- **Sprint activo:** `.context/SPRINT-CURRENT.md`
- **Decisiones:** `MASTER §6` (no usar DECISIONS.md histórico como primario)
- **Investigación:** `backend/research/2026-04-19/SINTESIS-4-FUENTES.md`
- **Plan Maestro externo:** `.context/external-review/PLAN-MAESTRO-CRECE-V2.docx` (documento ancla original Claude.ai Opus 4.7)

**Fin del NORTH-STAR.** Siguiente lectura: MASTER §2 y §6.
