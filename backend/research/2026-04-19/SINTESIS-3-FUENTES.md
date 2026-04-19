# Síntesis — 3 fuentes de investigación (2026-04-19)

**Fuentes:**
1. `sc_research_response.md` — deep-research agent Claude (486 líneas, 18 fuentes verificables con links académicos)
2. `gemini_response.md` — Gemini CLI local (162 líneas, 8 fuentes, 15 elementos candidatos)
3. `perplexity_response.md` — Perplexity externo entregado por CEO (177 líneas, 35 fuentes MX-heavy, truncado en 5.2)

---

## 1. CONVERGENCIAS (las 3 coinciden)

| Tema | sc:research | gemini | perplexity |
|---|---|---|---|
| **ER por alcance > ER por seguidores > absoluto** | ✅ | ✅ | ✅ |
| **Breakout / unconnected reach es el KPI principal** | ✅ fórmula + threshold 3x | ✅ >60% non-follower | ✅ Breakout Score (alcance-seguidores)/seguidores×100 |
| **Share of Voice vs competidores directos** | ✅ (Brandwatch Benchmark) | ✅ "Dueño de la Conversación" | ✅ SoV político |
| **Sentimiento como composición, NO promedio** | ✅ 6 emociones Plutchik | ✅ Ratio Tensión | ✅ evolución por tema |
| **Framework Start/Stop/Continue** | ✅ con post modelo linkeado | ✅ con ejemplos | ✅ |
| **Matriz 2x2 contenido × engagement** | ✅ engagement × out-of-base reach | ✅ 2x2 | ✅ 2x2 |
| **Detección de bots / coordinación** | ✅ CIB Detector | ✅ Astroturfing | ✅ índice sospecha |
| **Prohibir vanity metrics** | ✅ (regla operativa) | ✅ | ✅ |
| **Gálvez 365% ER pero perdió** | ✅ (dato central) | ❌ | ❌ |
| **Samuel García / Alfaro como modelos MX** | ✅ ambos detallados | ✅ ambos | ⚠️ mencionados |

**Veredicto:** las 3 convergen en los fundamentals. No hay contradicción mayor entre ellas. sc:research es la más granular con evidencia cuantitativa; gemini la más "creativa"; perplexity la más MX-anclada pero menos profunda.

---

## 2. APORTES ÚNICOS DE CADA FUENTE

### sc:research aporta (único):
- Benchmarks industry 2026 concretos: TikTok 3.70%, IG 0.48%, FB 0.15%, X 0.12%
- Caso Sheinbaum vs Gálvez con números internos (engagement/views/followers)
- Oxford Internet Institute Mexico 2018 como fuente académica (AMLO)
- Framework de crisis detection tipo "Storm Alert" (Meltwater)
- Distinción `trust/anger` como KPI primario (Sheinbaum ganó con trust, Gálvez con anger)
- Defense Post Detector (Benoit functional theory)
- LLM Propaganda Detector (ScienceDirect TecMty 2025)
- Propaganda Score por tweet — uso de Gemma/Claude como classifier
- Compliance INE veda banner integrado al plan

### gemini aporta (único):
- **Humanización Score** — "80% Humanizado / 20% Institucional" basado en IA Vision + tagging
- **Mapa de Calidez Geográfica** — heat map por distritos/municipios
- **Eficiencia de Pauta** — CPM/Engagement paid vs organic
- **Gap de Respuesta** — reply rate del político a followers + tiempo promedio
- **Alerta de Oportunidad** — "Nadie habla de X en CDMX hoy" (gap analysis vs trending topics)
- **Efecto Bumerán** — warning si uso bots para atacar oposición degrada sentiment propio
- Lenguaje ejecutivo: "3 minutos de lectura, dicta agenda del día siguiente"

### perplexity aporta (único):
- Fuentes MX institucionales (INE "Conectados pero desinformados", Congreso CDMX, SocialTIC)
- Benchmarks específicos de influencers vs marcas MX: 1.8-1.0% vs 0.2-0.5%
- Detección de coordinación con umbrales específicos: >50% comments 1ra hora + >70% users <100 followers
- Contexto académico mexicano (Revistas UP, IPN, produccioncientificaluz.org)
- Indicador de Expansividad definido por "cuentas que no siguen a otros políticos de la misma coalición"

---

## 3. DIVERGENCIAS REALES

| Tema | Qué dice cada uno | Mi lectura |
|---|---|---|
| **ER "bueno" en México** | sc: TikTok 3.70% mediana global · gemini: TikTok >10% bueno · perplexity: IG 1.1-2.5% orgánico | **gemini es demasiado optimista**. Los números de sc:research y perplexity son consistentes con Rival IQ + Social Insider 2026 |
| **Umbral breakout** | sc: >60% non-follower reach · gemini: idem · perplexity: alcance > 3× seguidores | Mismo concepto, dos fórmulas. Operativamente ambas funcionan; elegir una en producción |
| **Detección coordinación** | sc: lexical similarity + temporal + author age · gemini: pattern timing/accounts · perplexity: umbrales duros (>50% 1ra hora + >70% <100 followers) | perplexity propone thresholds más accionables; sc propone pipeline más robusto. Combinar: perplexity para MVP, sc para v2 |

**No hay contradicción grave.** Las divergencias son de granularidad, no de dirección.

---

## 4. INVENTARIO CONSOLIDADO — 24 bloques priorizados

Selección y merge de los 3 inventarios (20 sc + 15 gemini + elementos implícitos perplexity), priorizados por:
- **Valor**: impacto decisional para el político
- **Viabilidad**: datos que ya tenemos vs datos que faltan
- **Singularidad**: diferenciación vs competencia (Brandwatch, Meltwater)

### Tier 1 — CORE del diagnóstico (MVP sí o sí)

| # | Elemento | Pregunta | Inputs que SÍ tenemos | Inputs que FALTAN | Fuente |
|---|---|---|---|---|---|
| 01 | **Breakout Posts semana** | ¿Qué post cruzó mi base? | reach post, followers | alcance no-follower (no disponible sin Meta OAuth) | sc + gemini + perplexity |
| 02 | **Matriz 2x2 engagement × out-of-base** | ¿Qué posts amplificar/matar? | engagement, reach | unconnected_reach | sc #02 |
| 03 | **Benchmark vs 3-5 competidores directos** | ¿Cómo me comparo? | scrapers ya tienen multi-dirigente | segmentación "rival directo" vs "MC nacional" | sc #03 |
| 04 | **Sentiment composition (Plutchik 6)** | ¿Anger creciente? | pysentimiento | re-entrenar NLP para 6 emociones | sc #04 |
| 05 | **Crisis Spike Alert** | ¿Crisis emergiendo? | volumen mentions hora × hora | threshold calibrado | sc #05 + gemini |
| 06 | **Growth Attribution 24/48/72h** | ¿Qué post trajo followers? | followers_count DIARIO | snapshot diario automatizado | sc #06 + gemini + perplexity |
| 07 | **Start/Stop/Continue + post modelo** | ¿Qué hago mañana? | todo lo anterior | LLM prompt template | sc #09 + gemini |
| 08 | **Share of Voice por tema** | ¿Domino mis temas? | keywords + mentions | topic extraction | sc #16 + perplexity |

### Tier 2 — DIFERENCIADORES (ventana competitiva CRECE)

| # | Elemento | Pregunta | Inputs SÍ | Inputs FALTAN | Fuente |
|---|---|---|---|---|---|
| 09 | **Out-of-base Validation Score** | ¿Me validan de fuera de mi base? | comments, sentiment | cluster afiliación autor comment | sc #07 + perplexity |
| 10 | **CIB Detector coordinación** | ¿Me atacan con bots? | comments timing + similarity | author metadata (account age, follower count) | sc #08 + gemini + perplexity |
| 11 | **Propaganda Score por tweet** | ¿Es propaganda organizada? | tweets negativos dirigidos | Gemma/Claude classifier | sc #10 |
| 12 | **Defense Post Detector** | ¿Respondo a ataques bien? | posts tagged defense | tagging automático | sc #12 |
| 13 | **Humanización Score** | ¿Me veo muy político? | ❌ | IA Vision tagging (lifestyle vs admin) | gemini |
| 14 | **Mapa de Calidez Geográfica** | ¿Dónde me quieren más? | geoloc partial | geolocalización autor comment | gemini |
| 15 | **Alerta de Oportunidad (gap trending)** | ¿De qué no estamos hablando? | trending topics | scraper trending por región | gemini |

### Tier 3 — NICE TO HAVE (iteraciones posteriores)

| # | Elemento | Pregunta | Fuente |
|---|---|---|---|
| 16 | Narrativa Score (tema/framing) | ¿Qué temas me funcionan? | sc #14 |
| 17 | Cluster de seguidores demografía inferida | ¿Crece mi base en segmentos clave? | sc #15 |
| 18 | Hora/Día óptimos publicación (heatmap) | ¿Cuándo publicar? | sc #13 |
| 19 | Comparativa Plataforma Óptima (radar) | ¿Dónde invertir tiempo? | sc #19 |
| 20 | ER Benchmark por tamaño de cuenta (gauge) | ¿Mi ER es bueno para mi tamaño? | sc #11 |
| 21 | Gap de Respuesta (reply rate) | ¿Ignoro a la gente? | gemini |
| 22 | Eficiencia de Pauta (CPM vs organic) | ¿Tiro dinero en ads? | gemini |
| 23 | Reporte Semanal Ejecutivo IA | ¿PDF 1 página auto-generado? | sc #17 |
| 24 | Veda INE Compliance Banner | ¿Cumplo INE? | sc #18 |

### Rechazados / no replicables

- **Verified MX** (perplexity): sin valor comprobable, mencionado pero sin evidencia
- **Cambridge Analytica-style microtargeting**: prohibido por ética + LFPDPPP
- **Vanity dashboard widgets** (total likes, total followers): regla Tier -1 = fuera del dashboard principal

---

## 5. GAPS ESTRUCTURALES DEL BACKEND

Para ejecutar Tier 1 (8 bloques core) necesitamos que existan en BD:

| Gap | Prioridad | Costo |
|---|---|---|
| **Snapshot diario de followers_count** | 🔴 ALTA (bloquea Growth Attribution) | 2-3h — cron que lea API pública o Meta Graph API tras OAuth |
| **Re-entrenar NLP para 6 emociones Plutchik** | 🟡 MEDIA (bloquea sentiment composition) | 4-6h — pysentimiento ya soporta, ajustar pipeline |
| **Campo `competidor_directo_ids` en dirigentes** | 🔴 ALTA (bloquea Benchmark Tier 1) | 1h — migration + seed manual |
| **`unconnected_reach` por post** | 🔴 ALTA (bloquea Breakout + Matriz 2x2) | bloqueado hasta Meta OAuth (recordatorio: docs/META-OAUTH-SETUP.md) |
| **Cluster afiliación de autor comment** | 🟡 MEDIA (bloquea Out-of-base) | 6-8h — inferir afiliación por historial de interacciones |
| **Topic extraction automática** | 🟡 MEDIA (bloquea SoV por tema) | 3-4h — LLM classifier + 8-12 temas fijos (economía, seguridad, salud, etc.) |

**Hallazgo operativo:** sin Meta OAuth (docs/META-OAUTH-SETUP.md) no hay `unconnected_reach` real. Esto afecta **4 de 8 bloques Tier 1**. Decisión arquitectónica implícita: o (a) desbloqueamos Meta OAuth antes del redesign, o (b) usamos proxies no oficiales (ej.: views/seguidores como aproximación a unconnected_reach) con caveat documentado.

---

## 6. 3 hallazgos que cambian el plan

1. **Los 3 investigadores convergen en que "IPD 0-10 genérico" debe morir** y ser reemplazado por 7-8 KPIs específicos. No es "mejora del IPD", es "retirarlo".

2. **Meta OAuth es ahora pre-requisito técnico del nuevo diagnóstico**, no un nice-to-have. 4 de 8 bloques Tier 1 dependen de `unconnected_reach` — sin OAuth entregamos un producto similar al actual con más chrome encima.

3. **El diferenciador defensible vs Brandwatch/Meltwater no es el tech stack, es la composición MX** — benchmarks de dirigentes MX por tamaño + competidores directos del mismo distrito + compliance INE + matriz v3 política. Todo esto no lo hace ningún competidor.

---

## 7. Siguiente paso propuesto

**PRD v2 de Diagnóstico + Plan IA** basado en este inventario consolidado. 8 bloques Tier 1 + 2-3 bloques Tier 2 como diferenciador. Con los gaps del backend documentados como pre-requisitos.

Estimación: 1h escribir PRD + 30 min revisión CEO.

Tras aprobación del PRD: priorizar Meta OAuth (bloqueador) → snapshots diarios → migration competidor_directo → implementación Tier 1.
