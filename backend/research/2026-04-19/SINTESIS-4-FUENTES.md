# Síntesis definitiva — 4 fuentes de investigación (2026-04-19)

**Documento que reemplaza a `SINTESIS-3-FUENTES.md`** (aquel se mantiene como histórico pre-Gemini Deep Research).

**Las 4 fuentes:**

| # | Fuente | Líneas | Fuentes citadas | Inventario | Fortaleza principal |
|---|---|---:|---:|---:|---|
| 1 | `sc_research_response.md` (deep-research agent Claude) | 486 | 18 academic links | 20 bloques | Rigor académico + caso Sheinbaum vs Gálvez con números |
| 2 | `gemini_response.md` (gemini -p local) | 162 | 8 | 15 | Conceptos creativos (Humanización, Mapa Calidez, Gap Respuesta) |
| 3 | `perplexity_response.md` (pegado CEO) | 177 | 35 (MX-heavy) | takeaways dispersos | Fuentes institucionales MX (INE, SocialTIC, Congreso CDMX) |
| 4 | **`gemini_deep_research_response.md` (Deep Research externo CEO)** | **499** | **96** | **28 bloques** | **El más sólido**: Brookings, MIT, AAAI, Harvard, ITESO Signa_Lab |

---

## 1. LA 4TA FUENTE — APORTES ÚNICOS QUE CAMBIAN EL PLAN

Gemini Deep Research trae 15 elementos únicos de alto valor que no estaban en las 3 fuentes previas:

### 1.1 Frameworks académicos formales

| Concepto | Aporte |
|---|---|
| **Breakout Scale de Brookings** | 6 categorías formales (Cat 1-2 in-community · Cat 3 cross-platform · Cat 4-5 medios masivos · Cat 6 disrupción agenda pública). El salto **Cat 2→Cat 3 es el KPI principal de expansión política**. Mucho más estructurado que "non-follower reach %" |
| **Time-Decay Attribution Model** | Modelo explícito en Python/scikit-learn: impactos temporalmente cercanos a la conversión pesan más. Hasta 50% del crédito al post más reciente cuando hay cadena de interacciones |
| **Rage Click Effect (Tulane)** | Alto volumen de comentarios ≠ apoyo cívico. Algoritmos priorizan contenido divisivo → riesgo de confundir indignación amplificada con validación. Requiere flag explícito |
| **Elaboration-Likelihood Model** | Share-to-Like Ratio como proxy de movilización física. Ciudadano que comparte asume costo reputacional en su red privada — correlaciona con intención de voto/donación/asistencia |
| **Cross-Partisan Interactions (Science journal / MIT / arXiv)** | Interacciones cruzadas partidistas pueden ser despolarizantes si se estructuran con razonamiento causal + encuadre emocional positivo |
| **Topic Drift (TF-IDF comparativo)** | Caption del post vs corpus de comentarios generados. Si diverge >50-60%, la conversación se descarriló — métrica operacional concreta |

### 1.2 Contexto MX que solo esta fuente tiene

| Concepto | Aporte |
|---|---|
| **ITESO Signa_Lab — anatomía del CIB en México** | No son "bots" genéricos. Ecosistema sociotécnico estratificado: **"Maestros de Ceremonias"** (perfiles seudo-anónimos que dictan encuadre) + **"Cuentas Coro"** (algoritmos + militantes radicales que saturan algoritmo replicando directrices) |
| **Xóchitl Gálvez 2024 — análisis granular** | $75.2M MXN en digital, 56 mítines vs 212 del rival. Confundió CIB con apoyo. Ataque sistémico PERDIÓ por generar rechazo orgánico por virulencia artificial |
| **Verificado 2018 — fracaso por determinismo tecnológico** | Corregir datos ≠ desmantelar desinformación afectiva. Efecto Streisand al refutar ataques menores. Lección: IA debe evaluar si ataque está encapsulado en echo chamber marginal antes de sugerir respuesta |
| **Movimiento Ciudadano "mercenarios digitales" a Honduras (ContraLaCorrupcion)** | Red operada por consultoras Euzen/Indat con antecedentes de violación de veda. Compliance INE crítico para CRECE — bloqueo preventivo de publicaciones que infrinjan veda |
| **Obama 2012 Dashboard patentado** | Referencia histórica: sincronización datos territorio (voluntarios puerta a puerta) + datos digitales en tiempo real. Filosofía: **cruce digital-territorial** es diferenciador real |

### 1.3 Benchmarks ER por estrato político (tabla operacional)

**Único en esta fuente.** Todas las demás daban rangos por red genéricos; Gemini Deep Research los segmenta por tamaño de cuenta específicamente política:

| Estrato | Seguidores | ER esperado | Perfil |
|---|---|---|---|
| **Nano** | 1K-10K | 6.0-10.0% | Regidores, candidatos locales |
| **Micro** | 10K-50K | 3.5-6.0% | Diputados locales, alcaldes emergentes |
| **Mid-Tier** | 50K-100K | 2.0-4.0% | Diputados federales, alcaldes metropolitanos |
| **Macro** | 100K-500K | 1.5-2.5% | Senadores, gobernadores |
| **Mega** | 500K+ | 1.0-2.0% | Candidatos presidenciales, ejecutivo |

**Implicación:** el dashboard principal debe comparar al político contra benchmarks de SU estrato, no contra el promedio general.

### 1.4 Bloques únicos del inventario (ausentes en sc/gemini/perplexity)

| Bloque | Pregunta que responde |
|---|---|
| **Monitor de Desviación Temática (Topic Drift)** | Publiqué sobre infraestructura ¿por qué la conversación dominante es inseguridad? |
| **Filtro de Realidad (Vista Depurada)** | ¿Cuál sería mi IPD si apagáramos a los trolls? Toggle "Orgánico vs Raw" |
| **Recomendador de Horarios de Máxima Fricción Operativa** | ¿A qué hora publicar réplica para máximo daño orgánico sin pauta? Coincide con picos de mi audiencia y valles del adversario |
| **Análisis de Fatiga y Saturación Algorítmica** | ¿Me pasé al publicar 6 comunicados hoy? Detecta canibalización de alcance entre publicaciones propias |
| **Shadow Benchmarking Táctico** | ¿Qué tema específico está funcionándole al adversario que yo no estoy contraatacando? |
| **Rastreador de Promesas de Campaña** | ¿Cuál de mis promesas originales usan sistemáticamente como arma en mi contra? |
| **ROI / CPA Político** | $X autorizados en pauta, ¿fueron eficientes? Costo por nuevo simpatizante activo en MXN |
| **Churn Rate Político (Deserción orgánica)** | ¿Cuántos unfollows esta semana? ¿Qué publicación los detonó? |
| **Influencers Proxy de Alto Impacto** | ¿Qué periodista/cuenta >50K citó positivamente mi campaña? (Breakout Cat 4) |
| **Identificador de Zonas Muertas** | ¿Llevo 3 meses publicando informes legislativos y nadie interactúa? Auditoría esfuerzo vs retorno |
| **Simulador Algorítmico de Crisis (Pre-Mortem)** | Si apruebo reforma impopular mañana, ¿cuál será el daño digital basado en backtesting? |
| **Escaneo de Lenguaje Radical y Violencia Política** | ¿Los ataques cruzan línea a violencia de género / amenazas? Reportes automatizados para plataformas |
| **Message Stickiness** | ¿Mi slogan de campaña está arraigando en el lenguaje de terceros? |
| **Completion Rate Estimator** | ¿La gente ve completo mi video de 3 min o se sale a los 10 seg? |
| **Feedback Loop cognitivo (Reinforcement Learning)** | Botones 👍/👎 en cada recomendación IA para entrenar modelo personalizado al perfil del político |

---

## 2. CONVERGENCIAS CONSOLIDADAS — 4 FUENTES COINCIDEN

| Tema | sc | gemini -p | perplexity | gemini DR |
|---|---|---|---|---|
| ER normalizado > absoluto | ✅ | ✅ | ✅ | ✅ |
| Unconnected reach / Breakout como KPI estrella | ✅ (3x thresh) | ✅ (>60%) | ✅ (fórmula) | ✅ (Breakout Scale Brookings Cat 1-6) |
| Share of Voice vs competidores directos | ✅ | ✅ | ✅ | ✅ |
| Sentimiento multi-dimensional (no promedio) | ✅ Plutchik 6 | ✅ Ratio Tensión | ✅ Por tema | ✅ |
| Start/Stop/Continue con post modelo | ✅ | ✅ | ✅ | ✅ (único con ejemplos específicos MX) |
| Matriz 2x2 engagement × sentiment | ✅ | ✅ | ✅ | ✅ (con 4 cuadrantes nombrados: Insignia/Crisis/Vanidad/Muerta) |
| Detección CIB / bots coordinados | ✅ | ✅ | ✅ (umbrales) | ✅ (ITESO framework más sofisticado) |
| Prohibir vanity metrics | ✅ | ✅ | ✅ | ✅ (con "Vanity Penalty Factor") |
| Caso Gálvez 2024 como advertencia | ✅ (ER 365% perdió) | ❌ | ❌ | ✅ ($75.2M + 56 mítines + CIB) |
| Compliance INE / veda | ✅ | ❌ | ⚠️ | ✅ (filtro heurístico preventivo) |

**Veredicto:** convergencia total en fundamentals. Gemini DR es la fuente más completa y rigurosa; sc:research la segunda en rigor; perplexity aporta anclaje MX institucional; gemini CLI aporta elementos creativos.

---

## 3. DIVERGENCIAS QUE IMPORTAN

| Tema | Consenso | Acción |
|---|---|---|
| **ER "bueno" TikTok** | sc dice mediana global 3.70%, gemini CLI dice >10% bueno, Gemini DR dice Nano 6-10% / Micro 3.5-6% / Mid 2-4% | **Adoptar tabla Gemini DR por estrato político** — es la única segmentada así |
| **Umbral Breakout** | sc/perplexity: 3x seguidores. Gemini CLI: >60% non-follower reach. Gemini DR: Categoría Brookings 2→3 | **Adoptar Breakout Scale Brookings** — es framework académico, no heurística ad-hoc |
| **Detección CIB** | sc pipeline ML, perplexity umbrales duros, Gemini DR framework ITESO con MCs+Chorus | **Combinar**: umbrales perplexity para MVP, framework ITESO para v2 |
| **Attribution growth por post** | sc follow-window, gemini CLI conversion rate, Gemini DR Time-Decay scikit-learn | **Time-Decay (Gemini DR)** — más riguroso, implementable en Python |

---

## 4. INVENTARIO CONSOLIDADO FINAL — 30 bloques priorizados

Merge de los 4 inventarios (20 sc + 15 gemini CLI + takeaways perplexity + 28 Gemini DR). Deduplicados y priorizados por:
- **Valor** (impacto decisional para el político)
- **Viabilidad** (datos que ya tenemos vs gaps)
- **Singularidad** (diferenciación vs Brandwatch/Meltwater)

### TIER 1 — CORE del diagnóstico (MVP obligatorio, 10 bloques)

| # | Bloque | Pregunta para el político | Inputs SÍ | Inputs FALTAN | Fuente primaria |
|---|---|---|---|---|---|
| 01 | **ER normalizado por estrato político** | ¿Mi ER está en rango para mi tamaño? | posts, engagement, followers | benchmarks estrato políticos MX | Gemini DR (tabla estratos) |
| 02 | **Breakout Scale Brookings (Cat 1-6)** | ¿Mi post cruzó fronteras algorítmicas? | reach post | unconnected_reach (Meta OAuth) | Gemini DR (Brookings Institute) |
| 03 | **Matriz 2x2 Insignia/Crisis/Vanidad/Muerta** | ¿Qué tema amplificar/matar? | engagement, sentiment por tema | topic extraction LLM | Gemini DR + sc #02 |
| 04 | **Benchmark vs 3-5 competidores directos** | ¿Cómo me comparo con rivales reales? | scrapers multi-dirigente | segmentación "rival directo" | sc #03 + Gemini DR |
| 05 | **Sentiment composition (Plutchik 6 emociones)** | ¿Anger creciente? trust/fear ratio | pysentimiento | re-entrenar para 6 emociones | sc #04 |
| 06 | **Crisis Spike Alert (anomaly detection)** | ¿Crisis emergiendo AHORA? | volumen mentions hora | threshold calibrado | sc #05 + Gemini DR |
| 07 | **Growth Attribution Time-Decay (Python scikit-learn)** | ¿Qué post me trajo followers atribuibles? | followers_count DIARIO, posts timestamp | snapshot diario + modelo MTA | Gemini DR #9 (scikit-learn) |
| 08 | **Share of Voice por tema** | ¿Domino mis temas o me los roba el rival? | keywords + mentions | NER / topic extraction | sc #16 + Gemini DR |
| 09 | **Share-to-Like Ratio (Movilización Profunda)** | ¿Mi audiencia moverá el culo o solo da like? | shares + likes | separar por tipo de interacción | Gemini DR #3 (Elaboration-Likelihood Model) |
| 10 | **Start/Stop/Continue con post modelo linkeado** | ¿Qué hago esta semana? Con ejemplo concreto | todo lo anterior | LLM prompt template | sc #09 + Gemini DR #13 |

### TIER 2 — DIFERENCIADORES DEFENSIBLES (8 bloques)

| # | Bloque | Pregunta | Fuente |
|---|---|---|---|
| 11 | **Cross-Partisan Validation Score** | ¿La oposición me está validando? | sc #07 + Gemini DR #2 (MIT Sloan + arXiv) |
| 12 | **CIB Detector multi-nivel (MCs + Chorus)** | ¿Me atacan con granja coordinada? | ITESO Signa_Lab + perplexity umbrales |
| 13 | **Filtro de Realidad (toggle Orgánico/Raw)** | ¿Cuál es mi aprobación real sin trolls? | Gemini DR #7 |
| 14 | **Topic Drift Detector (TF-IDF)** | Publiqué sobre X pero hablan de Y | Gemini DR #8 |
| 15 | **Rage Click Flag** | ¿Alto engagement es apoyo o indignación? | Gemini DR #6 (Tulane) |
| 16 | **Rastreador de Promesas de Campaña** | ¿Qué promesa usan como arma en mi contra? | Gemini DR #18 |
| 17 | **Veda INE Compliance (bloqueo preventivo)** | ¿Publicación programada viola veda? | Gemini DR #17 + sc #18 |
| 18 | **Escaneo Violencia Política (amenazas, género)** | ¿Los ataques cruzan línea penal? | Gemini DR #25 |

### TIER 3 — CAPAS AVANZADAS / NICE TO HAVE (12 bloques)

| # | Bloque | Pregunta | Fuente |
|---|---|---|---|
| 19 | Termómetro Territorial Digital (heatmap geo) | ¿Dónde me quieren más? | gemini CLI + Gemini DR #16 |
| 20 | Humanización Score (IA Vision) | ¿Me veo muy político? | gemini CLI |
| 21 | Alerta de Oportunidad (gap trending) | ¿De qué no estamos hablando? | gemini CLI |
| 22 | Gap de Respuesta (reply rate / time) | ¿Ignoro a la gente? | gemini CLI + Gemini DR #12 |
| 23 | Eficiencia Táctica por Formato | Reels vs fotos vs carrusel | Gemini DR #11 |
| 24 | Recomendador Horarios Fricción Óptima | ¿Cuándo publicar para máximo daño sin pauta? | Gemini DR #12 |
| 25 | Análisis Fatiga / Saturación | ¿Me pasé con 6 publicaciones hoy? | Gemini DR #14 |
| 26 | Churn Rate Político | Unfollows + qué post los detonó | Gemini DR #21 |
| 27 | Influencers Proxy Alto Impacto | ¿Quién >50K me cita positivamente? | Gemini DR #22 |
| 28 | Pre-Mortem Simulator | Backtesting daño antes de publicar | Gemini DR #24 |
| 29 | Message Stickiness | ¿Mi slogan está arraigando en terceros? | Gemini DR #26 |
| 30 | ROI / CPA Político + Feedback Loop IA | $X en pauta ¿fue eficiente? + 👍/👎 para entrenar IA | Gemini DR #20 + #28 |

---

## 5. ARQUITECTURA DUAL-MODE POR DIRIGENTE (corrección 2026-04-19)

**Corrección al SINTESIS-3-FUENTES:** Meta OAuth no es bloqueador global, es feature de upgrade comercial por-dirigente.

### 5.1 Realidad del modelo piloto → producción

Cada dirigente en BD tiene flag `data_fidelity_tier` que determina qué fuentes alimentan su dashboard:

| Tier | Cuándo aplica | Fuentes | Estado actual |
|---|---|---|---|
| **T1 — Scraping público** | Baseline universal | Apify (posts + métricas públicas), Brightdata, oEmbed | ✅ Operativo |
| **T2 — Scraping + cookies burner** | Actual stack enriquecido | Scrapling + `@RafaRamos72` cookie, Chrome DevTools | ✅ Operativo |
| **T3 — Meta OAuth oficial** | Post-venta, cliente firmado que entrega Meta Login | Graph API (reach exacto, watch time, demographics, CPA) | 🟡 Doc listo (`docs/META-OAUTH-SETUP.md`), activable on-demand |

**Regla clave:** el piloto opera en T1+T2. El T3 **se activa por-dirigente cuando firman contrato** y hacen onboarding Meta. No es prerequisito global del producto.

### 5.2 Ningún dirigente piloto va a entregar credenciales hoy

Los 8 dirigentes del benchmark actual (Piña, Solano, Pineda, Nolasco, Jiménez, Cravioto, Ballesteros, Máynez) están siendo scrapeados públicamente sin su consentimiento explícito — no van a dar acceso OAuth a un sistema piloto que no ha firmado como proveedor. Eso llega después.

**Implicación comercial:** el piloto con T1+T2 se convierte en argumento de venta. Al cliente firmado:

> *"Mira lo que CRECE ya te dice con datos públicos. Con tu Meta Login conectado (T3), estos 5 KPIs se vuelven exactos (no proxy), tienes demografía real de tu audiencia y medimos CPA de tu pauta."*

Demostración > promesa.

### 5.3 Mismo dashboard en ambos modos, con badge de fidelity

- Dashboard idéntico visualmente en T1/T2/T3
- Badge discreto por KPI: `📊 Oficial` (T3) vs `📊 Estimación pública` (T1/T2)
- Upgrade es transparente: cuando Piña firma → su cuenta sube a T3, los demás siguen T1/T2
- Nunca hay "bloques desactivados" — siempre hay un valor (proxy o exacto según tier)

### 5.4 Inventario 30 bloques × fidelity por tier

Cada bloque funciona en T1/T2 con proxy y se **mejora** (no se desbloquea) con T3. Mapeo:

| # | Bloque Tier 1 (core) | T1/T2 scraping | T3 OAuth (upgrade) |
|---|---|---|---|
| 01 | ER normalizado por estrato | likes+comments público / followers | +reach exacto → ER verdadero |
| 02 | Breakout Scale Brookings | proxy: `views/followers` + ER spike 10× baseline (direccional) | `unconnected_reach` exacto, categoría Brookings precisa |
| 03 | Matriz 2x2 | engagement + sentiment scraped | +reach por post → cuadrantes exactos |
| 04 | Benchmark competidores | idéntico — scrapeamos rivales T1 también | idéntico (rival sigue en T1/T2 salvo que también firme) |
| 05 | Sentiment Plutchik | NLP sobre comments scraped | idéntico |
| 06 | Crisis Spike | volumen mentions público | +reach de mentions |
| 07 | Growth Attribution Time-Decay | snapshot diario follower_count público | +atribución reach-level (más granular) |
| 08 | Share of Voice por tema | mentions scraped | idéntico |
| 09 | Share-to-Like Ratio | X/TT/FB shares públicos, IG parcial (sin saves) | +saves IG → movilización real completa |
| 10 | Start/Stop/Continue | LLM sobre data disponible | LLM con data T3 → recomendaciones más precisas |

| # | Bloque Tier 2 (diferenciadores) | T1/T2 | T3 mejora |
|---|---|---|---|
| 11 | Cross-Partisan Validation | afiliación inferida por historial autor comment | idéntico (no requiere OAuth del sujeto) |
| 12 | CIB Detector multinivel | timing + similarity + account age scraped | idéntico |
| 13 | Filtro de Realidad | misma data que CIB | idéntico |
| 14 | Topic Drift TF-IDF | caption vs comments — ambos scraped | idéntico |
| 15 | Rage Click Flag | sentiment + velocity comments | idéntico |
| 16 | Promesas Campaña | seed manual | idéntico |
| 17 | Veda INE preventivo | texto de post | idéntico |
| 18 | Violencia Política | NLP sobre comments | idéntico |

| # | Bloque Tier 3 (nice-to-have) | T1/T2 | T3 mejora |
|---|---|---|---|
| 19 | Termómetro Territorial | geo inferida parcial autor comment | +audience demographics oficial Meta |
| 20 | Humanización Score | IA Vision sobre media pública | idéntico |
| 21 | Alerta Oportunidad (trending gap) | trending scraped | idéntico |
| 22 | Gap de Respuesta | replies scraped | idéntico |
| 23 | Eficiencia por Formato | engagement por tipo | +reach exacto por tipo |
| 24 | Horarios Fricción Óptima | engagement por hora | +reach por hora exacto |
| 25 | Fatiga Publicación | engagement inverso frecuencia | idéntico |
| 26 | Churn Rate Político | snapshot diario followers | idéntico |
| 27 | Influencers Proxy Alto Impacto | mentions filtradas por followers>50K | idéntico |
| 28 | Pre-Mortem Simulator | backtesting data propia + pública | +data T3 histórica → mejor modelo |
| 29 | Message Stickiness | frase exacta en corpus comments | idéntico |
| 30 | ~~ROI/CPA Político~~ | ❌ no funciona sin Ads API | ✅ requiere T3 + Facebook Ads API |

**Conclusión:** 29 de 30 bloques operan en modo piloto (T1/T2). Solo #30 es T3-only. De los 29, 10 tienen mejora marginal con T3, 19 son idénticos.

---

## 6. GAPS ESTRUCTURALES DEL BACKEND

Para Tier 1 + Tier 2 completos en modo piloto (T1/T2):

| Gap | Bloques afectados | Prioridad | Costo |
|---|---|---|---|
| **Flag `data_fidelity_tier` en dirigentes + lógica de routing** | todo el dashboard | 🔴 ALTA | 2h migration + service |
| **Snapshot DIARIO de followers_count público** | 07, 26 | 🔴 ALTA | 2-3h cron scraper |
| **Campo `estrato_politico` en dirigentes** | 01 | 🔴 ALTA | 30 min migration + seed |
| **Campo `competidor_directo_ids` en dirigentes** | 04, 15 | 🔴 ALTA | 1h migration + seed |
| **Mapear `views` de posts a BD (ya en output Apify)** | 02, 23, 24 | 🔴 ALTA | 30 min |
| **Re-entrenar NLP para 6 emociones Plutchik** | 05 | 🟡 MEDIA | 4-6h |
| **Topic extraction (NER + TF-IDF)** | 03, 08, 14 | 🟡 MEDIA | 3-4h |
| **Cluster afiliación autor comment** | 11 | 🟡 MEDIA | 6-8h |
| **Seed Promesas de Campaña (5 ejes × dirigente)** | 16 | 🟢 BAJA | 1h manual |
| **Modelo Time-Decay scikit-learn** | 07 | 🟡 MEDIA | 4h |
| **Diccionarios Hate Speech / Violencia Género MX** | 18 | 🟡 MEDIA | 3-4h + dataset |
| **Sprint Meta OAuth activable (ya diseñado)** | upgrade T3 | 🟢 BAJA piloto · 🔴 ALTA post-venta | 1-2 días implementación, 0 días piloto |

**Ningún bloqueador externo para el piloto.** El OAuth queda en código, listo para activarse cuando haya cliente firmado.

---

## 7. IMPLICACIONES ESTRATÉGICAS PARA CRECE v2

### 7.1 El IPD 0-10 debe morir definitivamente

Las 4 fuentes convergen. El reemplazo no es "mejor IPD" — es **dashboard de 10 KPIs Tier 1** con interpretación contextual.

### 7.2 El diferenciador defensible NO es el tech stack

Es la **composición mexicana integrada**:
- Benchmarks MX segmentados por estrato político (tabla Gemini DR)
- Competidores directos del mismo distrito/cargo
- Compliance INE integrado (veda preventiva, etiqueta IA, gastos)
- Matriz v3 política + framework CIB ITESO
- Narrativas mexicanas (Verificado 2018, caso Gálvez $75M+56 mítines, Sheinbaum institucional, MC mercenarios Honduras)

Brandwatch/Meltwater no hacen nada de esto.

### 7.3 Piloto funcional sin prerequisitos externos

- 29/30 bloques funcionan en modo T1/T2 (scraping actual)
- OAuth es **feature de upgrade comercial por-dirigente**, no prerequisito global
- Upgrade T1/T2 → T3 es gradual: cuando firman contrato, onboarding activa OAuth para ese dirigente
- Piloto actúa como **demo comercial** — los KPIs que ya muestra son el argumento de venta

### 7.4 Tres killer features que ningún competidor ofrece

1. **Breakout Scale Brookings Cat 1-6 aplicado a política MX** — con proxy honesto en T1/T2, exacto en T3
2. **Filtro de Realidad con CIB ITESO multinivel** — "apaga a los trolls y dime mi IPD real", captura caso Gálvez 2024
3. **Arquitectura dual-mode con upgrade commercial** — demo gratis con scraping, precisión con OAuth firmado. Monetización diferenciada.

---

## 8. Siguiente paso propuesto

**PRD v2 de Diagnóstico + Plan IA** con base en este inventario de 30 bloques + arquitectura dual-mode. Roadmap sin bloqueadores externos:

1. **Sprint Backend foundations (4-5h)** — flag `data_fidelity_tier`, `estrato_politico`, `competidor_directo_ids`, snapshot diario followers, mapear `views` Apify → BD, topic extraction básica
2. **Sprint Diagnóstico Tier 1 (1-2 semanas)** — 10 bloques core en modo T1/T2 con proxies documentados
3. **Sprint Diferenciadores Tier 2 (1 semana)** — CIB Detector ITESO + Filtro Realidad + Veda INE + Violencia Política
4. **Sprint Plan IA LLM (3-4 días)** — Start/Stop/Continue con RAG sobre histórico
5. **Sprint Meta OAuth activable (1-2 días, paralelo a 3+4)** — implementación feature onboarding, zero fricción piloto, listo para activar post-venta

**Timeline realista:** 3-4 semanas para MVP Tier 1+2 con compliance INE y OAuth preparado pero no disparado.

¿Te escribo el PRD formal (1h) o prefieres iterar más este resumen antes?
