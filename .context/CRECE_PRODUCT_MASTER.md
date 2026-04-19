# CRECE v2 — Product Master Document

**Fuente única de verdad. Versionado en git. Actualizado a 2026-04-19.**

Este documento reemplaza a cualquier otro documento de planificación en el repo. Si hay contradicción entre este archivo y otro, **este gana**. Los demás son históricos o referencias técnicas.

**Mantenedor primario:** CEO (Marx Chávez) + sesión Claude Code activa.
**Licencia:** documento interno MD Consultoría.

---

## §0 — BOOTSTRAP OBLIGATORIO PARA CUALQUIER SESIÓN

Si eres una sesión nueva de Claude Code operando sobre CRECE v2, **haz esto antes de cualquier otra cosa**:

1. **Lee las secciones §2 (Estado actual) y §6 (Decisiones vivas) de este documento.** No saltes. Las dos combinadas tardan ~3 minutos.
2. **Ejecuta en paralelo:**
   ```
   git log --oneline -10
   git status --short
   ```
3. **Reporta al CEO en un solo párrafo**: "Entiendo que estamos en [fase X], último sprint cerrado fue [Y], siguiente paso documentado es [Z], rama actual [branch]. ¿Procedo con ese siguiente paso o cambió la prioridad?"
4. **Espera respuesta antes de ejecutar.**

**No trates de reconstruir contexto leyendo chat history pasado.** Este documento + git + MEMORY.md es todo lo que necesitas. Si algo no está aquí, es porque no es relevante o porque aún no se ha decidido — preguntar.

---

## §1 — VISIÓN DEL PRODUCTO

**CRECE v2 es una plataforma de inteligencia digital para políticos profesionales mexicanos** (diputados, secretarios, coordinadores, gobernadores) que reemplaza sistemas de analytics genéricos (IPD 0-10, sentimiento promedio) con un **dashboard de 30 bloques accionables + plan IA Start/Stop/Continue + compliance INE + arquitectura dual-mode por-dirigente** (scraping público T1/T2 → Meta OAuth oficial T3 post-venta).

**Cliente primario:** Movimiento Ciudadano CDMX + dirigentes políticos mexicanos firmados por MD Consultoría.
**Qué reemplaza:** sistema Oracle APEX legacy de MC + dashboards de analytics genéricos.
**Diferenciador defensible:** composición mexicana integrada (benchmarks por estrato político, competidores del mismo distrito, compliance INE, framework CIB ITESO, matriz política v3). Brandwatch/Meltwater no hacen nada de esto en México.

**Principio rector:** cada métrica del dashboard debe poder responder "qué decisión dispara". Las que no, se eliminan (regla anti-vanity metrics).

### §1.5 — Cuatro perfiles de cliente (UI adaptable, arquitectura común)

CRECE v2 no atiende a "el político" en singular. Sirve a cuatro perfiles distintos con arquitectura común pero UI/vocabulario/onboarding adaptables. Esta distinción afecta el diseño del dashboard (qué KPIs destaca por default), el lenguaje del Plan IA (tono, urgencia, ventana temporal), y el modelo de pricing.

| Perfil | Contexto | Horizonte temporal | Necesidad central | Comprador operativo |
|---|---|---|---|---|
| **1. Político activo** (representación) | Diputado federal/local, senador, coordinador parlamentario | 3-6 años (reelección o salto) | Consolidar base + expandir adyacente sin sacrificar fieles | Jefe de prensa / coordinador digital |
| **2. Funcionario en gobierno** | Alcalde, secretario, gobernador | Período constitucional del cargo | Narrativa de gestión + anticipar crisis + reputación institucional | Equipo estructurado — reportes formales para gabinete |
| **3. Figura en precampaña** | 6-18 meses antes de elección | Corto, intolerante al error | Velocidad respuesta + compliance INE veda + trazabilidad legal | Jefe de campaña |
| **4. Empresario/figura independiente en transición** | Profesional/empresario construyendo vida pública desde cero | Construcción gradual | Formación paulatina (qué métricas importan) + autoridad pública sin capital negativo | El cliente directamente, sin estructura partidaria |

**Implicaciones para el producto:**
- Dashboard default prioriza diferentes bloques del inventario según perfil (ej.: precampaña enfatiza Veda INE #17 + Crisis Spike #06; empresario en transición enfatiza Humanización Score #20 + Message Stickiness #29)
- El Plan IA LLM prompt adapta tono: precampaña urgente/directivo, funcionario institucional/medido, empresario formativo/pedagógico
- Onboarding Wizard del Sprint S5 detecta perfil y ajusta preguntas + expectativas de data fidelity desde el primer minuto

**Decisión pendiente de validación CEO:** confirmar que estos 4 perfiles son los correctos antes de codificarlos como enum en BD (ver §6).

---

## §2 — ESTADO ACTUAL (status board — actualizar al cerrar cada sesión)

**Última actualización:** 2026-04-19 por Joy (sesión CRECE v2).

### §2.1 Snapshot operativo

| Dimensión | Estado |
|---|---|
| **Rama actual** | `feat/eval-benchmark-v1` |
| **Último commit main** | `3921f10` (calibración XLS) · `a919c5f` (cierre 5 redes scrapers) |
| **PR abierto** | #12 — Sprint B eval/benchmark + encuestas scrapers (no mergeado aún) |
| **Fase del proyecto** | **Pre-PRD técnico**: MASTER v2.3 estratégico aprobado por **dos puertas independientes** (Claude.ai Opus 4.7 Puerta 1 + Gemini CLI Puerta 2) con 3 decisiones nuevas D-16/D-17/D-18 + 6 ajustes críticos Gemini integrados. Pendiente: redactar PRD técnico separado con esquemas SQL/endpoints/tests, luego Sprint S0 |
| **Último trabajo cerrado** | Triangulación NLP Layer 2 (3-way Claude+Gemini+Gemma sobre 60 comments) — Gemma3:12b validado para producción |
| **Investigación estratégica cerrada** | 4 fuentes: `sc:research`, `gemini -p`, Perplexity, Gemini Deep Research (96 fuentes académicas). Síntesis en `backend/research/2026-04-19/SINTESIS-4-FUENTES.md` |
| **Próximo paso documentado** | Ejecutar Sprint 0 (validación de supuestos), luego roadmap §5 |
| **Bloqueadores externos** | Ninguno. OAuth es upgrade comercial post-venta, no prerequisito piloto |
| **Gemma local status** | Corriendo como producción aceptada por CEO 2026-04-14. Batch 1,146 comments NLP Layer 2 completo. Ritmo ~10s/item |
| **Credenciales demo** | admin@consultoriamd.com / crece2026! · pina@crece.mx / demo2026! · solano@crece.mx / demo2026! |
| **Backend local** | FastAPI :8002 · PG+PostGIS+pgvector :5438 · Ollama :11434 (gemma3:12b + gemma4) |
| **Coolify deploy** | Pendiente Carlos admin — no bloquea desarrollo |
| **Peer sessions activas** | Potencialmente Rem en `feat/eval-benchmark-v1` (compartida — riesgo worktrees) |

### §2.2 Lo que YA funciona (no reconstruir, extender)

**Infraestructura base operativa:**
- Backend FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + PostGIS 3.4 en Docker puerto 8002 (DB :5438, Redis :6383)
- Frontend Next.js 14 App Router + Tailwind desplegado en Vercel `frontend-zeta-sepia-46.vercel.app`
- Celery workers + Redis para scrapers + pipeline NLP
- Túnel Cloudflare efímero para exponer backend local durante demos

**Arquitectura multi-tenant 3 orgs (verificada):**
- MC-CDMX (id 1) · GOB-OAXACA (id 2) · CDMX-IND (id 3)
- Aislamiento por `org_id` application-level (decisión D-MT-01) + RLS policies listas
- Tenant switcher admin con header X-Org-Id + localStorage
- 9 usuarios con roles admin/analista/operador/dirigente

**Capa de datos políticos reales:**
- 3,833 posts sociales ingestados · 3,709 con pipeline NLP completo (97%)
- 11 columnas nuevas en `social_posts`: tono_politico, target, sentimiento_ajustado, controversy_score, toxicity_score, topics, version_modelo, etc.
- Framework político 3 capas: pysentimiento + Claude Opus 4.6 + matriz rule-based (32 reglas en 5 contextos federal/CDMX/Oaxaca/NL/Jalisco)
- 387 posts clasificados manualmente vía admin panel cadencia semanal (dataset validación)
- 200 comments TikTok de Piña (post 7357909824622890245) ingestados vía Brightdata — dataset piloto Índice Aceptación (11.5% aprobación vs 20% rechazo)

**Módulos diagnóstico avanzados:**
- Índice de Aceptación por publicación (IA scores aprobación/rechazo/neutralidad sobre 200 comments reales, test E2E validado)
- Radar IPD 5 ejes + switcher Treemap/Stream/Sunburst + semáforo crecimiento por plataforma + alerta automática 48h data_source manual_host_ingest

**Planes IA grounded v3:**
- 6 planes CONSOLIDACION generados para 6 dirigentes piloto (Piña, Solano, Pineda, Nolasco, Jiménez, Cravioto)
- Framework FODA sobre los 3,709 posts NLP
- 29 tareas por plan con campo `fundamento_foda` en historial
- Migración suave preserva planes v2 como `superseded`
- Benchmark prompts v1-v3 vs Gemma 3:12b local convergió baseline v1 con score 86.5/100

**Compliance LFPDPPP MVP:**
- Aviso privacidad público `/legal/privacidad`
- Derechos ARCO con hash SHA256
- Celery beat `retention_tasks` ejecuta 86400s cleanup comments política 180 días

### §2.3 Lo que está A MEDIO CAMINO

- **Scraper masivo comments 6 dirigentes × 4 plataformas:** solo 200 TikTok Piña completo; otros con snapshots en curso sin output visible >10 min. Rotación Brightdata/Crawlbase/ScraperAPI/Apify/PhantomBuster diseñada pero sin orquestación operativa real
- **Widgets Índice Aceptación existen** como React components con React Query hooks · **falta wiring** en páginas perfil dirigente + detalle post
- **Trends Motor Sprint S4:** 9/11 tareas. `topic_trends` tabla con vector 384-dim HNSW cosine migrada · RLS auditada 3 tests verdes · 136 cuentas semilla YAML (target 150) · location_inference con DB backing 10 tests · `/trends/geo` endpoint live. **Pendientes:** spaCy `es_core_news_md` install · persistencia RSS feeds requiere migración para agregar NEWS a `platform_enum` · backfill embeddings 381 posts existentes
- **Wizard onboarding Sprint S5:** 6/6 core componentes · auto-login real como deuda menor
- **E2E Playwright kanban planes:** 4 tests mocks stateful escritos, no ejecutados contra frontend dev server levantado

### §2.4 Lo que NO existe todavía

- **Arquitectura dual-mode con flag `data_fidelity_tier` a nivel dirigente** — scrapers actuales operan en T2 (cookie burner dedicada `@RafaRamos72` para X + similares para IG/FB/TT). OAuth T3 documentado en `docs/META-OAUTH-SETUP.md` pero no codificado
- **CIB Detector nivel ITESO con Maestros de Ceremonias + Cuentas Coro** — infraestructura NLP actual tiene sentimiento + controversy + toxicity pero NO scoring autenticidad por cuenta + probabilidad amplificación artificial
- **Tabla benchmarks por estrato político mexicano (Nano/Micro/Mid-Tier/Macro/Mega)** — framework_matrix_defaults poblado pero rangos ER por estrato son externos al sistema
- **Campo `estrato_politico` + `competidor_directo_ids` en tabla dirigentes** — gap documentado en SINTESIS-4-FUENTES
- **Breakout Scale Brookings (Cat 1-6) aplicado a política MX** — concepto `unconnected_reach` como proxy con `views` + ER spike 10× baseline discutido pero no codificado

### §2.5 Lo que va a MORIR o PIVOTAR

- **IPD 0-10 como métrica headline** — NO se mata de golpe, se **degrada a métrica secundaria** durante 2 sprints de migración suave. El radar IPD permanece visible pero deja de ser el foco del dashboard principal, reemplazado por los 10 KPIs Tier 1. Las vistas existentes no se rompen; el número IPD queda en sidebar como referencia histórica (decisión D-2026-04-19-01, ver §6)
- **Wizard pasos Sprint S5** — debe revisarse a la luz de arquitectura dual-mode. Onboarding actual asume modelo unitario; nueva arquitectura requiere detectar si dirigente opera T1/T2 (scraping) o T3 (OAuth) y adaptar preguntas + expectativas desde el primer minuto
- **Claude API provider del Plan IA** — placeholder según DIAGNOSTICO-UNIFICADO 05-abril. Consolida a **Gemma 3:12b local Ollama como provider primario** (costo $0, privacidad, 4-6 min/iter Mac M4 validado benchmark S2.6). Claude API o Gemini quedan como fallback opcional cuando cliente lo contrate

---

## §2.6 — Economía del comportamiento aplicada al receptor

*Fuente: Claude.ai Opus 4.7, sesión del 2026-04-19. Inserción verbatim (renumerada §2.5.x → §2.6.x para mantener consistencia con esquema del MASTER).*

La audiencia política no consume contenido como analista racional sino como ser humano con sesgos cognitivos bien documentados. Ignorar este marco es la principal causa de que las recomendaciones de los productos de analytics internacionales resulten genéricas en el mercado mexicano: optimizan para métricas de plataforma sin entender cómo el cerebro del votante procesa la información política. CRECE v2 integra cinco marcos teóricos como fundamento de las recomendaciones del Plan IA y de la interpretación de señales en el dashboard. Esta sección los formaliza para que cualquier sesión de Claude Code que genere output hacia el cliente pueda fundamentar las sugerencias con evidencia y no con opinión.

### §2.6.1 — Kahneman y Tversky: Sistema 1 y Sistema 2, Prospect Theory

Kahneman distingue entre el Sistema 1 de procesamiento rápido, emocional y automático, y el Sistema 2 de procesamiento lento, deliberativo y costoso. El consumo de contenido político en redes sociales ocurre casi exclusivamente en Sistema 1: el usuario promedio decide en menos de dos segundos si dar like, compartir o seguir scrolleando. Las publicaciones políticas que apelan a razonamiento elaborado sin antes ganar atención emocional no son procesadas. Prospect Theory agrega que las personas reaccionan más fuerte a pérdidas potenciales que a ganancias equivalentes, con un factor de asimetría documentado entre 2 y 2.5.

En contexto político mexicano, esto explica por qué la campaña de Sheinbaum en 2024 enmarcó el segundo piso de la transformación como continuidad de beneficios ya obtenidos y no como nuevas promesas abstractas. La narrativa activa aversión a la pérdida: votar por la oposición implica perder derechos adquiridos. Gálvez intentó el encuadre opuesto, prometer ganancias nuevas, que según Prospect Theory tiene menor fuerza movilizadora a igualdad de mérito argumental.

**Aplicación en CRECE v2:** el Plan IA del Sprint S4 debe privilegiar recomendaciones de encuadre en modo pérdida sobre modo ganancia cuando el objetivo sea movilización de base. El bloque #15 Rage Click Flag detecta cuando el Sistema 1 del receptor se activa por indignación sin generar conversión real.

### §2.6.2 — Cialdini: seis principios de influencia

Cialdini documenta seis armas de influencia que operan bajo el umbral consciente: reciprocidad, compromiso y coherencia, prueba social, autoridad, simpatía, y escasez. En contenido político digital, la prueba social es la más explotable: mostrar que mucha gente como el receptor apoya una posición es más persuasivo que el argumento racional para la posición. La autoridad funciona cuando se cita una fuente institucional que el receptor respeta, lo cual convierte a INEGI, IMSS y Banco de México en anclas retóricas defensibles frente a cualquier adversario.

En política mexicana, Milei en 2023 operó intensivamente el principio de autoridad citando estadísticas económicas como blindaje argumental, y la reciprocidad mediante respuesta personal a seguidores en los primeros noventa minutos post publicación. Bukele consolidó su culto digital con repetición disciplinada de tres o cuatro frases bandera durante meses, explotando el principio de compromiso y coherencia: una vez que el seguidor valida públicamente una postura del líder, la refuerza cada vez que la repite.

**Aplicación en CRECE v2:** el bloque #09 Share-to-Like Ratio mide movilización profunda porque compartir activa compromiso y coherencia (el seguidor asume costo reputacional en su red privada). El bloque #10 Start/Stop/Continue debe incorporar recomendaciones específicas de activación de prueba social ("destaca testimonios de votantes ordinarios en los primeros tres comentarios") y autoridad ("responde al primer crítico serio con cifra de fuente oficial INEGI o IMSS").

### §2.6.3 — Haidt: Moral Foundations Theory

Haidt documenta seis fundamentos morales que activan respuestas emocionales automáticas: cuidado versus daño, equidad versus injusticia, lealtad versus traición, autoridad versus subversión, pureza versus degradación, y libertad versus opresión. Los progresistas responden principalmente a cuidado y equidad; los conservadores responden a los seis con distribución más equilibrada. Un mensaje político que activa tres fundamentos morales simultáneamente supera sistemáticamente a uno que activa solo uno.

En contexto mexicano, el 4T activa cuidado (programas sociales), equidad (desigualdad histórica) y lealtad (identidad popular). La oposición tradicional activa principalmente autoridad (instituciones) y pureza (anticorrupción). Máynez con Movimiento Ciudadano intentó activar libertad y equidad simultáneamente, dirigido al votante joven que no se siente representado por los dos bloques históricos. La moral outrage, la indignación moral visible en comments con lenguaje de pureza y traición, es predictor fuerte de viralización pero no de persuasión: genera engagement sin cambiar posiciones.

**Aplicación en CRECE v2:** el bloque #05 Sentiment Plutchik debe extenderse para detectar clustering de lenguaje moralizado en comments siguiendo el léxico de Haidt. El bloque #15 Rage Click Flag captura específicamente la moral outrage como señal de engagement tóxico. El Plan IA debe recomendar construcción de mensajes que activen dos o tres fundamentos morales compatibles con la base del dirigente, no apelaciones genéricas de un solo fundamento.

### §2.6.4 — Bail 2018: Exposición a opiniones opuestas aumenta polarización

Bail y colegas publicaron en PNAS en 2018 un experimento con 1,239 usuarios de Twitter donde republicanos expuestos sistemáticamente a un bot liberal se volvieron más conservadores, y demócratas expuestos a un bot conservador se volvieron levemente más liberales. El hallazgo contradice la intuición tecno-optimista de que exponer a la gente a opiniones distintas reduce polarización. La realidad es el backfire effect: la exposición activa defensa identitaria y refuerza la postura previa.

En política mexicana, esto tiene consecuencia operativa crítica: atacar frontalmente a un rival en redes consolida su base, no la erosiona. El rival óptimo es el que se ignora o el que se rodea con contenido que reencuadra el debate, no el que se confronta directamente. Gálvez en 2024 invirtió recursos sustanciales en réplica directa a Sheinbaum, lo cual según Bail consolida a la base de Sheinbaum en lugar de erosionarla, mientras agota a la propia.

**Aplicación en CRECE v2:** el Plan IA del Sprint S4 debe incluir regla explícita de no recomendar confrontación frontal con adversario de mayor audiencia, porque amplifica. El bloque #11 Cross-Partisan Validation Score mide endorsement genuino fuera de la base como indicador de expansión real. El bloque #12 CIB Detector ITESO diferencia ataque coordinado artificial de crítica orgánica para ajustar la respuesta estratégica.

### §2.6.5 — Tajfel: Social Identity Theory

Tajfel y Turner establecen que el comportamiento político es tribalismo antes que cálculo racional de políticas públicas. Todo mensaje político activa un "nosotros versus ellos" aunque no lo intente explícitamente, y el receptor procesa la información filtrando primero por pertenencia identitaria: si el emisor pertenece al endogrupo, el mensaje es validado antes de ser evaluado; si pertenece al exogrupo, es descartado antes de ser evaluado.

En México, la polarización 4T versus oposición opera como identidad social antes que como preferencia programática. Un votante morenista y un votante panista pueden coincidir en ochenta por ciento de posiciones concretas pero votar en bloques opuestos porque su identidad tribal está activada. La densidad de pronombres "nosotros" y "ellos" en comments, el uso de emojis de bandera tribal (banderas nacionales versus puños morados), y la intimidad parasocial (llamar al líder "mi Claudia" o "Samuelito") son señales conductuales detectables que predicen resistencia a escándalos y capacidad de movilización offline.

**Aplicación en CRECE v2:** el pipeline NLP Layer 2 debe incluir detector de densidad de pronombres identitarios endogrupo versus exogrupo en comments. El bloque #11 Cross-Partisan Validation detecta cuando un post recibe validación de cuentas clasificadas en el exogrupo ideológico, señal rara y valiosa. La intimidad parasocial detectada en comments se convierte en señal de cohesión de base que debe preservarse y no sobreexplotarse con contenido institucional frío.

### §2.6.6 — Tabla de mapeo: principio conductual → bloque del inventario

| Principio conductual | Bloque(s) del inventario CRECE v2 | Cómo se aplica |
|---|---|---|
| Kahneman Sistema 1 vs Sistema 2 | #10 Start/Stop/Continue · #15 Rage Click Flag | Plan IA privilegia hooks emocionales en primeros 3 segundos. Rage Flag detecta Sistema 1 tóxico |
| Prospect Theory aversión a la pérdida | #10 Start/Stop/Continue · #16 Rastreador Promesas | Recomendaciones en modo pérdida. Promesas se enmarcan como "evitar perder" |
| Cialdini prueba social | #09 Share-to-Like Ratio · #11 Cross-Partisan Validation | Shares demuestran validación pública. Cross-partisan amplifica prueba social |
| Cialdini autoridad | #10 Start/Stop/Continue | Plan IA sugiere respuesta a críticos con fuente INEGI/IMSS/Banco de México |
| Cialdini reciprocidad | #22 Gap de Respuesta (Tier 3) | Respuesta en menos de 60 min genera lealtad desproporcionada |
| Cialdini compromiso y coherencia | #09 Share-to-Like Ratio · #29 Message Stickiness | Share activa compromiso. Stickiness mide arraigo de slogan en terceros |
| Haidt Moral Foundations | #05 Sentiment Plutchik (extendido) · #15 Rage Click Flag | Detecta clustering moral en comments. Rage Flag captura moral outrage |
| Bail backfire effect | Regla Plan IA + #11 Cross-Partisan · #12 CIB Detector | No recomendar confrontación frontal. Distinguir ataque coordinado de crítica orgánica |
| Tajfel Social Identity | NLP Layer 2 extendido · #11 Cross-Partisan Validation | Densidad de pronombres nosotros/ellos. Endorsement cruzado como señal de expansión |

### §2.6.7 — Regla transversal para el Plan IA

Toda recomendación generada por el Plan IA del Sprint S4 debe poder justificarse con al menos un principio conductual de los cinco marcos anteriores. Las recomendaciones genéricas tipo "mejora tu narrativa" o "conecta con tu audiencia" quedan explícitamente prohibidas. El formato de recomendación aceptable sigue la plantilla: acción específica, ventana temporal, criterio de éxito medible, principio conductual que aprovecha, y evidencia empírica de respaldo (post modelo del propio dirigente o de un caso comparable documentado).

**Ejemplo de recomendación aceptable:** "Responde al primer crítico serio del post del martes con cifra exacta de INEGI sobre ocupación en el sector. Ventana: primeras 2 horas post ataque. Éxito: ratio replies/likes del hilo baja de 0.8 a menos de 0.4 en 24 horas. Principio: Cialdini autoridad ancla el debate en evidencia institucional. Evidencia: tu respuesta del 15 de marzo al ataque de @adversario obtuvo esta misma caída de ratio."

**Ejemplo de recomendación rechazable:** "Mejora tu comunicación con la base electoral activando más emociones positivas." Sin acción específica, sin ventana, sin criterio medible, sin principio explícito, sin evidencia. Este tipo de output no puede escapar del Plan IA hacia el cliente.

---

## §3 — PRD: LOS 30 BLOQUES DEL DIAGNÓSTICO

Cada bloque tiene: **nombre · pregunta · tier fidelity · inputs · ejemplo visual · fuente primaria**.

**Tier fidelity:**
- **T1** = scraping público (todos los dirigentes)
- **T2** = scraping + cookies burner (@RafaRamos72, etc. — actual stack)
- **T3** = Meta OAuth oficial post-venta (solo dirigentes firmados)

### 3.1 TIER 1 — CORE del diagnóstico (MVP obligatorio, 10 bloques)

**Nota sobre fidelity "T1 funciona pleno":** en los bloques Tier 1, la expresión *"T1 funciona pleno"* significa que el bloque es plenamente funcional una vez completado el Sprint S1 Backend Foundations — que introduce migraciones pendientes como `estrato_politico`, `competidor_directo_ids`, `data_fidelity_tier` en la tabla `dirigentes` y el cron de snapshot diario de followers. Antes del cierre de S1, ningún bloque Tier 1 es ejecutable directamente. El orden del roadmap §5 lo garantiza (S0 → S1 → S2).


#### #01 — ER normalizado por estrato político
- **Pregunta:** ¿Mi ER está en rango para mi tamaño de cuenta?
- **Fidelity:** T1 funciona pleno · T3 mejora con reach exacto
- **Inputs:** posts.likes + posts.comments + profile.followers + dirigente.estrato_politico
- **Ejemplo:** "ER: 4.2% 🟢 (15% arriba de la media para Senadores)"
- **Fuente:** Gemini DR tabla estratos (Nano/Micro/Mid/Macro/Mega)

#### #02 — Breakout Scale Brookings (Cat 1-6)
- **Pregunta:** ¿Mi post cruzó fronteras algorítmicas hacia no-seguidores?
- **Fidelity:** T1 con proxy (`views/followers` en videos + ER spike 10× baseline) · T3 exacto con unconnected_reach
- **Inputs:** posts.views (videos), posts.engagement_rate, baseline_er, profile.followers
- **Ejemplo:** "🚀 Breakout Nivel 3: 85% de views no eran seguidores previos"
- **Fuente:** Brookings Institute Breakout Scale (Gemini DR)

#### #03 — Matriz 2x2 de contenido (4 cuadrantes nombrados)
- **Pregunta:** ¿Qué posts amplificar, contener, recortar, matar?
- **Fidelity:** T1 funciona pleno
- **Inputs:** posts.engagement_rate + sentiment + topic (NER)
- **Ejemplo:** scatter plot con 4 cuadrantes — Insignia (alto+positivo), Crisis (alto+negativo), Vanidad (bajo+positivo), Muerta (bajo+negativo)
- **Fuente:** Gemini DR §4.1 + sc:research #02

#### #04 — Benchmark vs 3-5 competidores directos
- **Pregunta:** ¿Cómo me comparo con mis rivales del mismo distrito/cargo?
- **Fidelity:** T1 funciona pleno (scrapeamos rivales también)
- **Inputs:** dirigente.competidor_directo_ids + últimas 4 semanas posts de cada uno
- **Ejemplo:** tabla 5 filas × 6 columnas (followers, ER, posts/sem, breakout ratio, SoV, trust/anger ratio)
- **Fuente:** Brandwatch Benchmark product + sc:research #03

#### #05 — Sentiment composition Plutchik (6 emociones discretas)
- **Pregunta:** ¿Está subiendo el enojo en mis comments? ¿Ratio trust/anger bajo?
- **Fidelity:** T1 funciona pleno (NLP sobre comments scraped)
- **Inputs:** comments con tags emotion (trust/anger/joy/fear/sadness/disgust)
- **Ejemplo:** stacked bar 7 días × 6 emociones · warning si anger >30% o ratio trust/anger <1
- **Fuente:** sc:research #04 (Ekman/Plutchik) + caso Sheinbaum vs Gálvez 2024

#### #06 — Crisis Spike Alert (anomaly detection)
- **Pregunta:** ¿Está emergiendo una crisis AHORA?
- **Fidelity:** T1 funciona pleno
- **Inputs:** volumen mentions hora × hora + media móvil 7d + sentiment
- **Ejemplo:** banner rojo "SPIKE: +340% mentions últimas 2h, sentimiento -70%, tema: #seguridad"
- **Fuente:** Meltwater Storm Alert + Gemini DR §1.3

#### #07 — Growth Attribution Time-Decay (scikit-learn)
- **Pregunta:** ¿Qué post me trajo los followers reales de esta semana?
- **Fidelity:** T1 con snapshot diario público · T3 enriquece con reach-level attribution
- **Inputs:** followers_count DIARIO + posts timestamp + modelo MTA Time-Decay
- **Ejemplo:** "+450 seguidores atribuibles al Reel 'Iztapalapa recorrido' (48h post-publicación)"
- **Fuente:** Gemini DR §2.3 + Time-Decay en scikit-learn

#### #08 — Share of Voice por tema clave
- **Pregunta:** ¿Domino la conversación en los temas que importan a mi candidatura?
- **Fidelity:** T1 funciona pleno
- **Inputs:** keywords estratégicos + mentions propio vs competidores + NER topic extraction
- **Ejemplo:** stacked area chart por tema (seguridad/economía/salud) con % SoV · gap alert si mío <20%
- **Fuente:** Brandwatch Benchmark + sc:research #16

#### #09 — Share-to-Like Ratio (movilización profunda)
- **Pregunta:** Si convoco a mitin ¿mi audiencia mueve o solo da like?
- **Fidelity:** T1 funciona en X (retweets) + TikTok + FB (shares públicos); IG parcial sin saves (T3 completa con saves)
- **Inputs:** posts.shares + posts.likes (por plataforma)
- **Ejemplo:** semáforo — "🔴 95% engagement son likes pasivos. Capacidad movilizadora BAJA"
- **Fuente:** Elaboration-Likelihood Model (Gemini DR #3)

#### #10 — Start/Stop/Continue con post modelo linkeado
- **Pregunta:** ¿Qué hago esta semana? (con ejemplo concreto, no abstracciones)
- **Fidelity:** T1 funciona pleno
- **Inputs:** todo lo anterior + LLM prompt (Gemma 3:12b local primario por D-16) + retrieval de posts propio y competidor
- **Ejemplo:** 3 cards (verde/rojo/azul) — cada acción linkeada a post modelo + métrica respaldo + ventana temporal + recursos necesarios + principio conductual §2.6
- **Fuente:** Framework OKR/Atlassian (Gemini DR §4.1) + práctica Alfaro/García consultoras
- **Flujo ampliado por D-17:** toda recomendación se persiste en tabla `recomendaciones_plan_ia` (ver §6.3.3) y sigue ciclo de 5 fases (generación → decisión → ejecución → seguimiento → cierre) cubierto por bloques #10.5 y #10.7 abajo

#### #10.5 — Seguimiento de Recomendaciones Activas *(añadido por D-17)*
- **Pregunta:** ¿Cómo evoluciona el post que publiqué siguiendo la recomendación de la semana pasada?
- **Fidelity:** T1 funciona con métricas públicas (likes, comments, shares, views). T3 enriquece con reach exacto, watch time y demographics de cohorte
- **Inputs:** tabla `recomendaciones_plan_ia` + `social_posts.id` del post ejecutor + snapshot diario de métricas + ventana temporal declarada (default 14 días, configurable por recomendación — decisión CEO parámetro 3 D-17)
- **Ejemplo:** sección permanente del dashboard con tarjetas de recomendaciones activas. Cada tarjeta muestra el texto de la recomendación original, el post ejecutor vinculado como preview embebido, gráfico temporal de métrica predicha vs observada durante la ventana, días restantes de evaluación, y semáforo de cumplimiento preliminar actualizado diariamente
- **Fuente:** D-17 CEO 2026-04-19
- **Componentes React:** adaptación `KanbanBoard` 🟢 agnóstico + nuevo `RecommendationFollowUpCard`

#### #10.7 — Memoria del Plan IA *(añadido por D-17)*
- **Pregunta:** ¿De las últimas recomendaciones ejecutadas, cuáles funcionaron y cuáles no? ¿Qué patrones emergen?
- **Fidelity:** T1 funciona con data acumulada de seguimiento. Mejora cualitativa en T3 por precisión de métricas subyacentes
- **Inputs:** histórico completo de tabla `recomendaciones_plan_ia` con veredicto final, categorizado por tipo de acción, tema, plataforma y principio conductual §2.6 que activó
- **Ejemplo:** dashboard histórico agregado con tasa de éxito por categoría. *"Recomendaciones de video vertical sobre infraestructura: 8/10 exitosas. Réplica a crítico con fuente INEGI: 5/7 exitosas. Post humanizante: 2/6 exitosas."* Drill-down por recomendación individual con evolución histórica + edición manual de veredicto (preserva `veredicto_original`)
- **Fuente:** D-17 CEO 2026-04-19
- **Función comercial crítica:** alimenta la conversación de venta con evidencia documentada de desempeño acumulado — cumple métrica de tracción comercial 90d §7.4

### 3.2 TIER 2 — DIFERENCIADORES DEFENSIBLES (8 bloques)

#### #11 — Cross-Partisan Validation Score
- **Pregunta:** ¿La oposición me valida o solo me escuchan mis fieles?
- **Fidelity:** T1 funciona pleno (clasificación autor comment por historial de interacciones)
- **Inputs:** comments + cluster afiliación autor (oposición/base/neutral) + sentiment
- **Ejemplo:** gauge 0-100% · >15% non-base positive es outlier → drill-down a comments
- **Fuente:** MIT Sloan + arXiv CPI (Gemini DR #2)

#### #12 — CIB Detector multinivel (MCs + Cuentas Coro)
- **Pregunta:** ¿Me atacan con granja coordinada de Morena/PRI/PAN?
- **Fidelity:** T1 funciona pleno
- **Inputs:** comments timing + similaridad semántica + account age + topología red
- **Ejemplo:** banner "⚠️ Ataque coordinado: 65% interacciones negativas de cuentas <72h. MCs identificados: @X, @Y. Recomendación: silencio estratégico"
- **Fuente:** Framework ITESO Signa_Lab (Gemini DR §2.4)

#### #13 — Filtro de Realidad (toggle Orgánico/Raw)
- **Pregunta:** ¿Cuál sería mi aprobación si apagáramos a los trolls?
- **Fidelity:** T1 funciona pleno (misma data CIB)
- **Inputs:** misma que #12 + umbral automation probability >85%
- **Ejemplo:** interruptor `[Raw | Orgánico]` · al activar Orgánico: IPD pasa de 4.5 a 7.2
- **Fuente:** Gemini DR #7

#### #14 — Topic Drift Detector (TF-IDF comparativo)
- **Pregunta:** Publiqué sobre infraestructura ¿por qué hablan de inseguridad en mis comments?
- **Fidelity:** T1 funciona pleno
- **Inputs:** post.caption + comments corpus + TF-IDF comparativo
- **Ejemplo:** "⚠️ Desvío 60%: Publicaste sobre Infraestructura, conversación dominante es Inseguridad"
- **Fuente:** Gemini DR #8

#### #15 — Rage Click Flag
- **Pregunta:** ¿Alto engagement = apoyo cívico o indignación amplificada?
- **Fidelity:** T1 funciona pleno
- **Inputs:** sentiment extremo negativo + velocity de comments
- **Ejemplo:** "🔥 Post Inflamatorio: alto volumen por indignación (Rage Clicks). Cuidado con erosión de alianzas moderadas"
- **Fuente:** Universidad de Tulane (Gemini DR §3.1)

#### #16 — Rastreador de Promesas de Campaña
- **Pregunta:** ¿Cuál de mis 5 promesas usan como arma en mi contra?
- **Fidelity:** T1 funciona pleno
- **Inputs:** seed manual de 5 promesas eje por dirigente + NLP co-ocurrencia con sentiment negativo
- **Ejemplo:** "Menciones tóxicas esta semana: 40% mencionan 'Hospitales al 100%'. Flanco capitalizado por adversario"
- **Fuente:** Gemini DR #18

#### #17 — Veda INE Compliance (bloqueo preventivo)
- **Pregunta:** ¿La publicación programada nos va a costar una multa INE?
- **Fidelity:** T1 funciona pleno
- **Inputs:** calendario INE veda + texto post + queue publicación
- **Ejemplo:** "🛑 Post programado 14:00 contiene lenguaje punible en veda. BLOQUEADO preventivamente"
- **Fuente:** Gemini DR §5.4

#### #18 — Escaneo Violencia Política (amenazas, género)
- **Pregunta:** ¿Los ataques cruzan línea penal hacia violencia de género / amenazas?
- **Fidelity:** T1 funciona pleno
- **Inputs:** diccionarios hate speech MX + comments
- **Ejemplo:** "🚨 Lenguaje amenazante sostenido en 3% comments hoy. Reportes automatizados listos para plataforma"
- **Fuente:** Prevención violencia política género MX + Gemini DR #25

### 3.3 TIER 3 — CAPAS AVANZADAS / NICE TO HAVE (12 bloques)

| # | Bloque | Pregunta | Fidelity | Fuente |
|---|---|---|---|---|
| 19 | Termómetro Territorial Digital | ¿Dónde me quieren más? heatmap geo | T1 parcial (geo inferida) · T3 demographics Meta | Gemini DR #16 |
| 20 | Humanización Score (IA Vision) | ¿Me veo muy "político"? 80% humanizado / 20% institucional | T1 funciona (IA Vision sobre media pública) | gemini CLI |
| 21 | Alerta de Oportunidad (gap trending) | ¿De qué no estamos hablando y todos hablan? | T1 funciona | gemini CLI |
| 22 | Gap de Respuesta | ¿Ignoro a la gente? reply rate + tiempo promedio | T1 funciona | gemini CLI + Gemini DR #12 |
| 23 | Eficiencia Táctica por Formato | Reels vs fotos vs carrusel · "Reels 300% más alcance que infografías" | T1 funciona · T3 reach exacto | Gemini DR #11 |
| 24 | Recomendador Horarios Fricción Óptima | ¿A qué hora publicar réplica para máximo daño sin pauta? | T1 funciona | Gemini DR #12 |
| 25 | Análisis Fatiga / Saturación Algorítmica | ¿Me pasé con 6 publicaciones hoy? canibalización | T1 funciona | Gemini DR #14 |
| 26 | Churn Rate Político | Unfollows + post que los detonó | T1 funciona con snapshot diario | Gemini DR #21 |
| 27 | Influencers Proxy Alto Impacto | ¿Quién >50K me cita? (Breakout Cat 4) | T1 funciona | Gemini DR #22 |
| 28 | Pre-Mortem Simulator | Backtesting daño antes de publicar reforma impopular | T1 funciona | Gemini DR #24 |
| 29 | Message Stickiness | ¿Mi slogan está arraigando en terceros? | T1 funciona | Gemini DR #26 |
| 30 | ROI/CPA Político + Feedback Loop IA | $X en pauta ¿fue eficiente? + 👍/👎 IA training | **T3 only** (requiere Facebook Ads API) | Gemini DR #20 + #28 |

### 3.4 Requisito transversal — Badge de fidelity visible en cada KPI

**Este NO es un bloque, es una regla de diseño del dashboard** que aplica a los 30 bloques.

Cada card/widget del dashboard debe renderizar un badge discreto que declare la fuente del dato:
- `📊 Oficial` cuando el dirigente opera en tier T3 (Graph API Meta autorizada)
- `📊 Estimación de mercado` cuando opera en T1/T2 (scraping público o burner)

**Criterio de aceptance transversal:** test E2E que verifica que ningún bloque renderiza sin badge (test fallante bloquea merge a main). Esta promesa es central al posicionamiento ético del producto y al argumento comercial del upgrade T1/T2 → T3. Sin el badge implementado como feature funcional, el producto no cumple con la promesa documentada en §4.3 y §9.3.

**Dónde se implementa:** componente compartido `<DataFidelityBadge tier={dirigente.data_fidelity_tier} />` consumido por todos los widgets del dashboard. Responsable de testing: Sprint S2 Diagnóstico Tier 1 (test del primer bloque obliga el patrón).

### 3.5 Componentes React reutilizables (inventario real del repo)

**Fuente:** `frontend/src/components/` escaneado 2026-04-19 — total 62 `.tsx`, los relevantes para el PRD son 23-25.

**Marcado:**
- 🟢 Agnóstico al modelo de métricas (reutilizable directo)
- 🟡 Asume vocabulario IPD viejo (requiere refactor leve para MVP Tier 1)
- 🔴 Acoplado a legacy — evaluar rewrite vs extensión

| Componente | Archivo | Función | Status |
|---|---|---|---|
| `IpdRadarChart` | `ipd-radar-chart.tsx` | Radar 0-10 presencia digital por plataforma | 🟡 Renombrar + adaptar para ser usado como métrica secundaria post-migración suave. Core visual útil |
| `IpdScoreBadge` | `ipd-score-badge.tsx` | Badge con score IPD numérico | 🟡 Reutilizable si se degrada IPD a sidebar; si muere por completo, deprecar |
| `SentimentLineChart` | `sentiment-line-chart.tsx` | Líneas positivo/neutral/negativo en tiempo | 🟡 Core útil, requiere adaptar a 6 emociones Plutchik (bloque #05) o mantener como vista agregada |
| `SentimentPieChart` | `sentiment-pie-chart.tsx` | Donut distribución sentimiento | 🟡 Similar — agregado útil, extender a Plutchik o coexistir |
| `SentimentBadge` | `sentiment-badge.tsx` | Badge colorizado de tono | 🟢 Agnóstico |
| `EngagementBarChart` | `engagement-bar-chart.tsx` | Barras engagement por plataforma | 🟢 Agnóstico — base para bloques #01, #04, #11 |
| `KpiCard` | `kpi-card.tsx` | Card métrica con icono + delta | 🟢 Agnóstico — core para todos los bloques Tier 1 |
| `StatCard` | `stat-card.tsx` | Card estadística (Sprint D integration) | 🟢 Agnóstico |
| `BentoGrid`/`BentoCard` | dentro del frontend | Layout modular dashboard | 🟢 Agnóstico |
| `FilterSelect` | `filter-select.tsx` | Select genérico con opción Todos | 🟢 Agnóstico |
| `MobileFilterSheet` | `mobile-filter-sheet.tsx` | Sheet de filtros mobile | 🟢 Agnóstico |
| `PostCard` | `post-card.tsx` | Card publicación multi-plataforma | 🟢 Agnóstico — base para Matriz 2x2 (#03) + ranking posts |
| `IndiceAceptacionCard` | `indice-aceptacion-card.tsx` | Stacked bar aprobación/neutral/rechazo + tono breakdown | 🟡 Útil, migrar a schema v2 simplificado (3 tonos × 5 targets) |
| `IASummaryCard` | `ia-summary-card.tsx` | Top aprobación/rechazo por dirigente | 🟡 Similar migración a v2 simplificado |
| `CrisisAlertList` | `crisis-alert-list.tsx` | Lista de alertas activas | 🟢 Agnóstico — base bloque #06 Crisis Spike |
| `CrisisAlertBanner` | `crisis-alert-banner.tsx` | Banner crítico de crisis | 🟢 Agnóstico |
| `CanvassingGeoMap` | `canvassing-geo-map.tsx` | MapLibre con clustering 9,631 ciudadanos reales | 🟢 Agnóstico — base para bloque #19 Termómetro Territorial |
| `CompetitividadMap` | `competitividad-map.tsx` | Mapa de competitividad electoral | 🟢 Agnóstico — útil benchmark #04 |
| `CompetitorSnapshotCard` | `competitor-snapshot-card.tsx` | Demo MC vs Batres/Taboada (estado demo) | 🟡 Útil, requiere wiring con `competidor_directo_ids` real |
| `ElectoralMap` | `electoral-map.tsx` | Mapa electoral resultados | 🟢 Agnóstico |
| `KanbanBoard` | `kanban-board.tsx` | 3 columnas edit inline captura métrica historial | 🟢 Agnóstico — base Plan IA tareas (#10) |
| `PlanTareasList` | `plan-tareas-list.tsx` | Lista tareas de plan IA | 🟢 Agnóstico |
| `SemaforoCrecimiento` | `semaforo-crecimiento.tsx` | Semáforo crecimiento por plataforma | 🟢 Agnóstico — base benchmark |
| `TrendingAlcaldiaCard` | `trending-alcaldia-card.tsx` | Topics por alcaldía (Sprint S4) | 🟢 Agnóstico — base bloque #08 SoV por tema |
| `TendenciaPorRedWidget` | `tendencia-por-red-widget.tsx` | Tendencia por red social | 🟢 Agnóstico |

**Regla:** Sprint S2 Diagnóstico Tier 1 debe reutilizar estos 25 componentes antes de construir nuevos. Cualquier componente nuevo requiere justificación explícita en HANDOFF del sprint.

**Componente nuevo aprobado por D-17:** `RecommendationFollowUpCard` específico para bloques #10.5 y #10.7 (construcción en Sprint S4 Plan IA LLM).

### 3.6 Requisito transversal — Human-in-the-loop obligatorio en Plan IA

**Este NO es un bloque, es una regla de gobernanza del Plan IA** (Sprint S4) que aplica a bloques #10, #10.5 y #10.7.

**Riesgo mitigado** (Gemini audit Puerta 2, hallazgo #08, 2026-04-19): Gemma 3:12b puede generar recomendaciones que violen veda electoral INE, tono institucional apropiado al cargo, o compliance LFPDPPP, sin que el modelo tenga capacidad para autodetectar el error. En un producto para políticos profesionales mexicanos, una sola recomendación automatizada que cruce la línea legal destruye la reputación del cliente y de MD Consultoría simultáneamente.

**Mitigación obligatoria:** ninguna recomendación generada por el Plan IA es visible al cliente final sin pasar previamente por review del equipo operativo de MD Consultoría. El flujo es:

```
Plan IA genera recomendación (estado='propuesta')
  ↓
Review MD Consultoría (human-in-the-loop obligatorio)
  ↓
Si aprobada: estado='aprobada' → visible al cliente
Si rechazada: estado='rechazada' → feedback al prompt engineering
Si requiere ajuste: estado='modificada' → vuelve a review
```

**Criterio de aceptance transversal:** el endpoint que expone recomendaciones al cliente final filtra obligatoriamente por `estado IN ('aprobada', 'modificada', 'ejecutada', 'completada')` y **nunca** entrega `estado='propuesta'`. Test E2E bloquea merge si el filtro no existe.

**Implementación:** admin panel `/dashboard/admin/plan-ia-review` con cola de recomendaciones pendientes. Responsable de testing: Sprint S4. **Sin este filtro implementado, el Plan IA no puede ir a producción** — es condición dura de arranque.

**Referencia:** D-17 (ciclo de recomendaciones) + Gemini audit hallazgo #08.

---

## §4 — ARQUITECTURA DUAL-MODE POR DIRIGENTE

### 4.1 Flag primario

Cada registro en tabla `dirigentes` tiene:

```sql
data_fidelity_tier VARCHAR(2) NOT NULL DEFAULT 'T1' CHECK (data_fidelity_tier IN ('T1', 'T2', 'T3'));
oauth_meta_token TEXT NULL;  -- si T3: token Graph API encriptado
oauth_meta_expires_at TIMESTAMP NULL;
```

### 4.2 Routing de datos por tier

- **T1 baseline:** scrapers Apify + Brightdata + oEmbed públicos. Aplica a todos los dirigentes sin esfuerzo adicional.
- **T2 enriquecido:** scrapers con cookies burner (@RafaRamos72 para X, cuentas similares para IG/FB/TT). Activable para cualquier dirigente que el equipo MD decida scrapear con autenticación adicional.
- **T3 oficial:** Meta OAuth por-dirigente vía flujo `docs/META-OAUTH-SETUP.md`. **Solo se activa cuando el dirigente firma contrato** con MD Consultoría y hace onboarding voluntario.

### 4.3 Reglas visuales en el dashboard

- Dashboard idéntico en los 3 tiers — no hay bloques "desactivados"
- Badge discreto por KPI:
  - `📊 Oficial` → T3 (Graph API)
  - `📊 Estimación de mercado` → T1/T2 (scraping)
- Al hover: tooltip explica qué cambia si se conecta Meta Login

### 4.4 Upgrade T1/T2 → T3 (sales flow)

1. Dirigente firma contrato con MD Consultoría
2. Email de onboarding con link a `/dashboard/configuracion/redes`
3. Dirigente autoriza Meta OAuth (Business app "CRECE v2", 5 permisos básicos)
4. Backend guarda token, marca `data_fidelity_tier = 'T3'`
5. Backfill de históricos exactos (reach, watch time) via Graph API Insights
6. Dashboard muestra badge `📊 Oficial` en lugar de `📊 Estimación`

### 4.5 Reconciliación de series de tiempo post-upgrade (`data_origin_checkpoint`)

**Riesgo identificado** (Gemini audit Puerta 2, hallazgo #05): cuando un dirigente pasa T1/T2 → T3, los valores absolutos de métricas (reach, views, CTR estimado) cambian de proxy scrapeado a oficial Graph API Insights. Las series de tiempo del dashboard mostrarían un quiebre visual que un cliente sofisticado interpretaría como métricas inventadas si no se marca el cambio de origen.

**Mitigación obligatoria:** cada fila de la tabla de métricas de series de tiempo incluye campo `data_origin` (T1/T2/T3) + se genera evento `data_origin_checkpoint` en el timestamp exacto del upgrade. El frontend renderiza una línea vertical discontinua en los charts temporales con tooltip *"A partir de aquí: datos oficiales Graph API (previo: estimación de mercado)"*. Esta transparencia preserva credibilidad del producto.

**Implementación:** migración Alembic añade columna `data_origin` a las tablas de snapshots/métricas históricas. Frontend `SentimentLineChart`, `EngagementBarChart`, cualquier chart temporal debe renderizar el checkpoint si existe. Sprint S1 Backend Foundations agrega la columna, Sprint S2 Diagnóstico Tier 1 implementa el renderizado.

---

## §5 — ROADMAP DE SPRINTS

**6 sprints** secuenciales (+1 paralelo). Total **4-5 semanas** para MVP Tier 1+2 (**expansión aprobada CEO 2026-04-19 parámetro 1 D-17** para incluir cierre de ciclo del Plan IA). Sprint 0 de validación previa aprobado CEO 2026-04-19.

### Sprint S0 — Validación de Supuestos (6-8h, expandido por Gemini #09)
- **Status:** ⏸ Pending · **próximo en ejecutar** tras aprobación PRD
- **Razón de existir:** saltárselo es el error clásico de empezar a construir sobre fundamentos no validados. Si los benchmarks ER por estrato de Gemini Deep Research no corresponden a nuestra data real, todo el Sprint S2 arranca sobre falsa premisa. Además, si Gemma 3:12b no clasifica las 6 emociones Plutchik con precisión aceptable, el bloque #05 requiere rediseño antes de Sprint S2
- **Trade-off rigor vs velocidad:** 6-8h de investigación evitan días de retrabajo. **Decisión CEO 2026-04-19: ejecutar sin reservas**
- **Tareas (4):**
  1. **Crear documentos canónicos faltantes** en `.context/`:
     - `NORTH-STAR.md` — ✅ creado 2026-04-19
     - `SPRINT-CURRENT.md` — ✅ creado 2026-04-19
     - `HANDOFF.md` — ✅ creado 2026-04-19
  2. **Validar benchmarks ER por estrato contra data real:** tomar los 8 dirigentes actualmente scrapeados (Piña, Solano, Pineda, Nolasco, Jiménez, Cravioto, Ballesteros, Máynez) y calcular sus ER reales últimos 90 días en cada plataforma, comparar contra tabla Gemini DR (Nano 6-10% · Micro 3.5-6% · Mid-Tier 2-4% · Macro 1.5-2.5% · Mega 1-2%). Si hay desviación >30%, recalibrar antes de Sprint S2
  3. **Correr pipeline CIB básico contra post Piña 7357909824622890245** (donde ya existen 200 comments clasificados) para medir si los patrones ITESO de Maestros de Ceremonias + Cuentas Coro son detectables con infraestructura NLP actual o requieren desarrollo adicional. Output: `backend/research/2026-04-19/cib_pilot_test.md` con 200 rows marcados + tasa detección + falsos positivos estimados
  4. **T0.4 Validación ciega Plutchik Gemma vs humano** *(añadida por Gemini audit #09)*: tomar 100 comments aleatorios del dataset de 3,709 posts con NLP ya procesado, hacer clasificación ciega a 6 emociones Plutchik por (a) Gemma 3:12b con prompt Plutchik + (b) 2-3 anotadores humanos MD. Calcular Cohen's kappa Gemma vs majority vote humano. **Criterio aceptance ≥75% coincidencia en emoción dominante.** Si falla, el bloque #05 requiere re-prompt o modelo superior antes de Sprint S2. Output: `backend/research/2026-04-19/plutchik_validation.md` con matriz de confusión + kappa + recomendación
- **Criterio acceptance del sprint:** 3 documentos canónicos creados ✅ · tabla calibrada ER por estrato para 8 dirigentes · reporte piloto CIB con % detección y baseline de falsos positivos · reporte validación Plutchik Gemma vs humano con kappa ≥0.75
- **Dependencias:** ninguna. Bloquea Sprint S1

### Sprint S1 — Backend Foundations (5-6h, expandido por D-17 + D-18)
- **Status:** ⏸ Pending (arrancar tras aprobación del PRD + Sprint S0 completo)
- **Objetivo:** Preparar schema + gaps estructurales antes de construir los bloques
- **Tareas:**
  1. Migration: añadir `data_fidelity_tier`, `estrato_politico`, `competidor_directo_ids`, `data_origin` a tabla `dirigentes` y snapshots
  2. Seed manual: asignar estrato (Nano/Micro/Mid/Macro/Mega) y competidores directos a los 8 dirigentes existentes
  3. Cron daily: snapshot `followers_count` por plataforma en tabla `social_profile_snapshots` (ya existe)
  4. Mapear campo `views` de output Apify a tabla `social_posts` (ya está en scraper, falta persistir)
  5. Topic extraction básica: servicio LLM (**Gemma 3:12b local por D-16** — NO Claude API como default) que extrae 1-3 topics por post (seed 8-12 topics fijos: seguridad, economía, salud, educación, movilidad, gobernanza, denuncia, autopromocion, personal)
  6. **Migration Alembic adicional** *(por D-17)*: crear tabla `recomendaciones_plan_ia` con schema completo descrito en §6.3.3 (18 columnas + 3 índices compuestos). Prepara el terreno para Sprint S4
  7. **Endpoint ARCO LFPDPPP** *(por D-18, Gemini audit #04)*: `POST /api/v1/admin/compliance/purge-hash` que elimina recursivamente comments + embeddings + vectores asociados a un hash SHA256 de autor. Audit log obligatorio de cada purga. Satisface derechos ARCO selectivos (obligación legal pendiente)
  8. **Ollama clúster failover** *(por Gemini audit #06)*: health-check desde backend hacia Ollama local Mac M4 cada 60s. Si falla >3 min, switch automático a Ollama Coolify (VPS, CPU-only, degradado) para mantener Plan IA disponible. Evita SPOF de hardware único
- **Criterio acceptance:** los 8 dirigentes tienen `data_fidelity_tier='T1'` + estrato + competidores. Cron corre 1 vez manual y escribe snapshot. Muestra de 50 posts con topics asignados. Tabla `recomendaciones_plan_ia` creada. Endpoint purge-hash con al menos 1 test de purga completa. Failover Ollama con health-check activo.
- **Estimación:** 5-6h (+1h D-17 + 1-2h D-18 + 30min failover)
- **Dependencias:** Sprint S0 completo

### Sprint S2 — Diagnóstico Tier 1 (Core MVP)
- **Status:** ⏸ Pending (arranca tras S1)
- **Objetivo:** Implementar los 10 bloques core del diagnóstico
- **Tareas:**
  1. Backend: endpoints REST por bloque (`/diagnostico/{dirigente_id}/er_normalizado`, `/breakout_scale`, etc.)
  2. Servicios: `er_service.py`, `breakout_service.py`, `matrix_2x2_service.py`, `benchmark_service.py`, `sentiment_plutchik_service.py`, `crisis_spike_service.py`, `growth_attribution_service.py` (con Time-Decay sklearn), `sov_service.py`, `share_like_ratio_service.py`
  3. NLP: re-entrenar pipeline Layer 2 para 6 emociones Plutchik (hoy solo polaridad/tono)
  4. Frontend: 10 cards en `/dashboard/diagnostico` con badge fidelity, gráficos (Recharts o similar), responsive
  5. Tests: 1 test E2E por bloque contra data piloto
- **Criterio acceptance:** dashboard muestra 10 cards vivas para dirigente Piña con data real de scrapers. CEO puede navegar y ver números coherentes.
- **Estimación:** 1-2 semanas
- **Dependencias:** S1 completo

### Sprint S3 — Diferenciadores Tier 2 (Killer Features)
- **Status:** ⏸ Pending (arranca tras S2)
- **Objetivo:** Los 8 bloques que diferencian CRECE de Brandwatch/Meltwater
- **Tareas:**
  1. CIB Detector multinivel (framework ITESO): servicio `cib_detector_service.py` con ML clustering temporal + similarity + topology
  2. Filtro de Realidad: toggle UI + recalculo metricas excluyendo cuentas CIB
  3. Topic Drift: servicio TF-IDF caption vs comments
  4. Cross-Partisan Validation: clasificador de afiliación de autor comment + scoring out-of-base
  5. Rage Click Flag: heurística sentiment × velocity
  6. Promesas Campaña: tabla `promesas_dirigente` + NLP co-ocurrencia
  7. Veda INE Compliance: filtro heurístico sobre queue de publicación
  8. Escaneo Violencia Política: diccionarios hate speech MX + detector
- **Criterio acceptance:** los 8 bloques operativos con muestra de casos reales del piloto. Filtro de Realidad cambia IPD visible (demo del valor).
- **Estimación:** 1 semana
- **Dependencias:** S2 completo

### Sprint S4 — Plan IA con LLM + Cierre de Ciclo (expandido 6-8 días por D-17)
- **Status:** ⏸ Pending (arranca tras S3 o paralelo si hay capacidad)
- **Objetivo:** Plan accionable semanal auto-generado **con ciclo completo de 5 fases** (generación → decisión → ejecución → seguimiento → cierre)
- **Tareas:**
  1. **Pipeline LLM Gemma 3:12b local** *(provider primario D-16, NO Claude API)* que consume todos los bloques T1+T2 + `behavioral_logic_library.json` diferido (Gemini audit #07, iteración posterior)
  2. Prompt engineering: template Start/Stop/Continue con anatomía §2.6.7 obligatoria (acción específica + ventana temporal + criterio medible + principio conductual + evidencia post modelo)
  3. RAG sobre histórico propio + competidores + memoria del Plan IA §3.1 #10.7
  4. **Generación persistible en tabla `recomendaciones_plan_ia`** con estado inicial `propuesta` (schema §6.3.3)
  5. **Admin panel `/dashboard/admin/plan-ia-review`** con cola de recomendaciones pendientes + flujo Human-in-the-loop obligatorio §3.6 (sin este admin panel el Plan IA no sale a producción)
  6. **UI cliente `/dashboard/recomendaciones`** con flujo decisión: aprobar, rechazar o modificar cada recomendación
  7. **Vinculación post ejecutor:** cuando cliente publica contenido tras recomendación aprobada, UI permite vincular `post_ejecutor_id` FK a social_posts
  8. **Servicio seguimiento:** durante ventana temporal (default 14d, configurable D-17 parámetro 3), cron diario captura métricas observadas vs predichas y actualiza la UI del bloque #10.5
  9. **Servicio cierre automático:** al vencer ventana, calcula veredicto (`exitosa`/`parcial`/`fallida`) por cumplimiento numérico del criterio + permite edición cliente preservando `veredicto_original` (D-17 parámetro 4)
  10. **Bloque #10.7 Memoria del Plan IA:** dashboard agregado con tasa de éxito por categoría + drill-down histórico
  11. Reporte semanal MD/PDF (1 página) + envío email configurable
  12. Pre-Mortem simulator (bloque #28) opcional como bonus
- **Criterio acceptance:** CEO recibe reporte semanal + flujo completo end-to-end: 1 recomendación generada → aprobada por MD review → aprobada por cliente → post publicado vinculado → seguimiento 14d con métricas diarias → veredicto automático + opción edición → aparece en memoria histórica.
- **Estimación:** 6-8 días (expansión aprobada D-17 parámetro 1)
- **Dependencias:** S2 mínimo, S3 opcional, tabla `recomendaciones_plan_ia` del S1

### Sprint S5 — Meta OAuth Activable (paralelizable con S3/S4)
- **Status:** ⏸ Pending (no bloquea piloto — se activa post-venta)
- **Objetivo:** Implementar el flujo `docs/META-OAUTH-SETUP.md` como feature de upgrade, listo para el primer cliente que firme
- **Tareas:**
  1. Registrar app "CRECE v2" en Meta Business (requiere cuenta MD Consultoría)
  2. Backend endpoint `/api/v1/auth/callback/meta` + token storage encriptado
  3. Frontend page `/dashboard/configuracion/redes` con botón "Conectar Meta"
  4. Backfill service: cuando `data_fidelity_tier` cambia T1/T2 → T3, corre Graph API Insights para últimos 90 días
  5. URLs legales: `/legal/terminos`, `/legal/eliminacion-datos` (`/legal/privacidad` ya existe Sprint C)
- **Criterio acceptance:** 1 dirigente test (Piña voluntario) puede conectar Meta desde UI, su dashboard cambia a badges `📊 Oficial`.
- **Estimación:** 1-2 días
- **Dependencias:** S1 (flag tier en BD). Meta Business Manager aprobado por CEO.

---

## §6 — DECISIONES VIVAS (Decision Log)

**Formato:** Fecha · Decisión · Razón · Quién · Status · Referencia

**Leyenda status:**
- 🟢 **APROBADA** — CEO confirmó explícitamente
- 🟡 **PROPUESTA** — recomendación o inferencia de Joy/Claude.ai pendiente validación CEO
- 🟠 **CONDICIONADA** — aprobada con condición explícita que debe cumplirse
- 🔴 **SUPERSEDED** — reemplazada por decisión posterior (nunca borrar, solo marcar)

| # | Fecha | Decisión | Razón | Status | Ref |
|---|---|---|---|---|---|
| D-01 | 2026-04-19 | Matriz v3 = schema v2 simplificado (3 tonos × 5 targets, ~15 reglas) en vez de las 53 v2 actuales | Benchmark eval 2026-04-14 demostró que schema v2 simplificado: (a) rescata a persona_4_marx de "falso outlier" 9.3%→74.1% agreement; (b) genera 82% ground truth con majority vote ≥3/4; (c) Claude_opus 95.5% accuracy, Gemma3:4b 79.5% | 🟢 APROBADA | `backend/eval/layer2_benchmark/reports/v2_2026-04-14/comparison_final.md` |
| D-02 | 2026-04-19 | OAuth Meta = upgrade comercial post-venta por-dirigente. NO bloqueador piloto | Políticos piloto no entregan credenciales sin contrato firmado. T3 se activa cuando firman. Piloto opera T1/T2 (scraping público + burner dedicado) | 🟢 APROBADA | §4 este doc · `docs/META-OAUTH-SETUP.md` |
| D-03 | 2026-04-19 | **IPD 0-10 se DEGRADA a métrica secundaria durante 2 sprints de migración suave** — no se mata de golpe, se reubica | CEO 2026-04-19: "reubicar, no matar. El radar IPD permanece visible pero deja de ser el foco del dashboard principal." Las vistas existentes no se rompen; el número IPD queda en sidebar como referencia histórica. Reemplazo primario son los 10 KPIs Tier 1 | 🟢 APROBADA con matiz | §2.5 este doc · §3.1 |
| D-04 | 2026-04-19 | Arquitectura dual-mode con 3 tiers fidelity (T1 público · T2 burner · T3 OAuth oficial) | Permite piloto sin bloqueadores + upgrade comercial diferenciado + demo > promesa al cliente | 🟢 APROBADA | §4 este doc |
| D-05 | 2026-04-19 | 4 anotadores humanos del eval 2026-04-14 como gold standard | Schema v2 simplificado normaliza acuerdo entre ellos. Hipótesis: persona_4_marx NO es outlier — el schema v1 era demasiado granular | 🟠 CONDICIONADA · **pendiente análisis outliers formal + revisión CEO del resultado antes de sellar** | `backend/eval/layer2_benchmark/` |
| D-06 | 2026-04-19 | Sprint 0 de validación de supuestos antes de Sprint S1 | Validar benchmarks ER por estrato contra data real + pipeline CIB piloto + crear documentos canónicos faltantes. 5-6h de inversión evitan retrabajo mayor | 🟢 APROBADA (sin reservas) | §5 Sprint S0 |
| D-07 | 2026-04-19 | 4 perfiles de cliente (político activo · funcionario · precampaña · empresario en transición) | Producto sirve a 4 perfiles con arquitectura común pero UI/vocabulario/onboarding adaptables. Afecta diseño dashboard, lenguaje Plan IA, pricing | 🟢 APROBADA | §1.5 |
| D-08 | 2026-04-19 | Economía del comportamiento como marco teórico transversal | Kahneman/Cialdini/Haidt/Bail/Tajfel. Fundamenta bloques #09, #10, #11, #12, #15, #16, #22, #29 + regla transversal Plan IA. Sección §2.6 redactada por Claude.ai Opus 4.7 + inserción verbatim en MASTER v2 | 🟢 APROBADA · **§2.6 insertada 2026-04-19** | §2.6 + §8.7 |
| D-09 | 2026-04-18 | Gemma3:12b concurrency4 apto para producción NLP Layer 2 | Triangulación 3-way Claude+Gemini+Gemma: Fleiss 0.761 tono · 0.803 intensidad · 0 errores de parseo · convergencia con Gemini 0.80+ | 🟢 APROBADA | `backend/evaluations/2026-04-18/output/REPORTE-TRIANGULACION.md` |
| D-10 | 2026-04-18 | Stack scrapers oficial: Apify primary + Scrapling/burner fallback + Brightdata validador | Cierre 5 redes integral $2.29 free tier, 2041 items. Producción semanal $2.54/sem | 🟢 APROBADA | `docs/SCRAPERS-VEREDICTO-COMPLETO.md` |
| D-11 | 2026-04-18 | Cuenta burner dedicada `@RafaRamos72` (NO personal reutilizada) para scraping T2 de X | Cuenta dedicada al scraping, no identidad personal reutilizada. Decryptada vía `pycookiecheat`. Planes burner successor `@RafaRamos73/74` listos si baneo | 🟢 APROBADA | `reference_burner_x_account.md` (memoria) |
| D-12 | 2026-04-14 | Ollama gemma3:12b env vars: NUM_PARALLEL=4, KEEP_ALIVE=24h, FLASH_ATTENTION=1 | Benchmark: 1.42× speedup. Proyección 31.4 min / 400 comments. Aceptado como producción | 🟢 APROBADA | MCP entity `gemma-ollama-benchmark-2026-04-14` |
| D-13 | 2026-04-14 | Multi-tenant 3 orgs: MC-CDMX (real) · GOB-OAXACA (sintético INEGI) · CDMX-IND (sintético INEGI) | Aislamiento estricto + seed independiente por org + watermark DATOS SIMULACIÓN en sintéticos | 🟢 APROBADA | `.context/PLAN-current.md` (histórico) |
| D-14 | 2026-04-14 | MD administra usuarios vía seed. Sin signup público. Sin UI admin CRUD | Cliente B2B político — usuarios gestionados por MD directamente | 🟢 APROBADA | `.context/PLAN-current.md` (histórico) |
| D-15 | 2026-04-19 | Gemma 3:12b local vía Ollama como LLM provider primario del Plan IA (Sprint S4) — NO Claude API/Gemini como default | Razones: (a) costo $0 vs costo marginal Claude/Gemini API; (b) privacidad del cliente — datos sensibles nunca salen del Mac M4; (c) velocidad validada benchmark S2.6 a 4-6 min/iter; (d) output quality aceptable con prompt engineering (score 86.5/100 baseline). Claude API y Gemini quedan como fallback opcional cuando cliente firmado lo contrate específicamente como feature premium | 🟢 APROBADA (formaliza lo documentado en §2.5 como decisión explícita) | §2.5 · benchmark `backend/app/nlp/prompts/diagnostico_winner.md` |
| D-16 | 2026-04-19 | Unificar provider LLM: Gemma 3:12b local baseline de desarrollo + Claude API exclusivamente como "Expert Auditor" de seguridad/compliance (NO para generación de producto) | Gemini audit Puerta 2 #02 detectó ambigüedad entre bloque #10 ("Claude/Gemma") y D-15 ("Gemma primario"). Deriva de costos imprevista si desarrollo cae en Claude API. Unificación elimina ambigüedad operativa — todo dev usa Gemma, Claude solo para auditoría estructurada | 🟢 APROBADA | §3.1 #10 · `.context/audits/gemini-master-v2.2-audit-2026-04-19.md` |
| D-17 | 2026-04-19 | **Cierre de ciclo del Plan IA con seguimiento de recomendaciones activas.** Añadir bloques #10.5 (Seguimiento) y #10.7 (Memoria) al inventario + tabla `recomendaciones_plan_ia` BD + flujo completo 5 fases (generación → decisión → ejecución → seguimiento → cierre). 4 parámetros CEO fijados: (1) expansión MVP 3-4s → 4-5s aprobada; (2) numeración 10.5/10.7 sin renumerar inventario; (3) ventana 14 días default configurable; (4) veredicto automático con opción edición cliente | Diseño original S4 generaba recomendaciones sin rastrear ejecución/resultado real. Sin cierre: (a) imposible distinguir exitosas vs fallidas empíricamente; (b) sistema no aprende del histórico; (c) conversación comercial limitada a promesas cualitativas — bloqueaba métrica tracción 90d §7.4. Cierre de ciclo convierte producto de dashboard pasivo a workflow activo con hábito de uso semanal | 🟢 APROBADA con matices · MVP expandido · 4 parámetros fijados | §6.3 desarrollo extendido · §3.1 #10.5 #10.7 · §5 S1+S4 |
| D-18 | 2026-04-19 | Endpoint ARCO selectivo `POST /api/v1/admin/compliance/purge-hash` obligatorio antes de producción — borrado recursivo de comments + embeddings + vectores asociados a hash SHA256 de autor | Gemini audit Puerta 2 #04: obligación legal bajo LFPDPPP no exenta por hash SHA256 actual. Retención 180d actual no cubre solicitud ARCO específica (acceso, cancelación, oposición) por titular individual. Riesgo multa INAI + daño reputacional. Endpoint + audit log por purga = satisfacción legal demostrable | 🟢 APROBADA · obligatorio Sprint S1 | `docs/AVISO-PRIVACIDAD-CRECE.md` · §5 S1 tarea 7 |

### §6.3 Desarrollo extendido de D-17 (cierre de ciclo Plan IA)

**Problema identificado por CEO (chat directo 2026-04-19 post-PR #16):**

El diseño original del Plan IA en Sprint S4 generaba recomendaciones con anatomía completa §2.6.7, pero no cerraba el ciclo entre recomendación generada, acción ejecutada y medición de resultado real.

**Ejemplo textual del CEO para anclar el diseño:** si el Plan IA recomienda publicar un video vertical de TikTok sobre fallas del Metro con estructura narrativa similar a un video de Instagram exitoso del pasado, el cliente espera ver durante los días posteriores cómo evoluciona ese post específico en seguidores ganados, penetración real y comentarios específicos, no solo recibir la recomendación y olvidarla.

**Tres limitaciones graves del diseño sin cierre de ciclo (ya resueltas por D-17):**

1. Imposibilidad de distinguir empíricamente recomendaciones exitosas de fallidas
2. Sistema incapaz de aprender del histórico para calibrar recomendaciones futuras
3. Conversación comercial limitada a promesas cualitativas sin evidencia cuantitativa de desempeño acumulado (bloqueaba la métrica de tracción comercial a 90 días §7.4)

**Diseño aprobado del ciclo en cinco fases:**

1. **Generación:** Plan IA produce recomendación con anatomía §2.6.7 y la persiste en tabla `recomendaciones_plan_ia` con estado `propuesta`
2. **Decisión:** cliente acepta, rechaza o modifica desde UI dedicada. Estado → `aprobada`/`rechazada`/`modificada`
3. **Ejecución:** cliente publica el contenido. Sistema vincula `post_ejecutor_id` FK al post publicado. Estado → `ejecutada`
4. **Seguimiento:** durante la ventana temporal (default 14 días) el sistema rastrea métricas predichas vs observadas, mostrando evolución contra baseline en UI bloque #10.5
5. **Cierre:** al vencer la ventana, el sistema calcula veredicto automático (`exitosa`/`parcial`/`fallida`) por cumplimiento numérico del criterio. Estado → `completada`. El cliente puede editar el veredicto si lo solicita (se preserva `veredicto_original`). Resultado alimenta memoria del Plan IA (bloque #10.7)

### §6.3.1 Cuatro parámetros CEO fijados

**Parámetro 1 — Expansión MVP:** 3-4 semanas → 4-5 semanas aprobada. Un Plan IA sin seguimiento tiene techo comercial bajo; cliente sofisticado detecta limitación en primera conversación de venta.

**Parámetro 2 — Numeración bloques:** 10.5 y 10.7 sin renumerar inventario de 30. Preserva numeración referenciada en research y comunicación interna. Nueva suma: 32 bloques efectivos.

**Parámetro 3 — Ventana seguimiento:** configurable por recomendación, default 14 días. Anchor cognitivo (Kahneman §2.6.1) apropiado para mayoría de recomendaciones consolidación digital. Suficientemente largo para capturar evolución orgánica, suficientemente corto para cadencia semanal. Configurabilidad preserva agencia cliente (ej. 7d posts virales, 30d narrativas estructurales).

**Parámetro 4 — Mecánica veredicto:** automático por cumplimiento numérico + opción edición manual preservando `veredicto_original`. Elimina carga cognitiva Sistema 2 (Kahneman §2.6.1) sin sacrificar objetividad. Opción edición preserva autoridad profesional del cliente. Trazabilidad automático vs editado alimenta #10.7 para detectar patrones de discrepancia sistemática.

### §6.3.2 Schema BD `recomendaciones_plan_ia`

```sql
CREATE TABLE recomendaciones_plan_ia (
  id SERIAL PRIMARY KEY,
  plan_ia_id INTEGER REFERENCES planes_ia(id),
  dirigente_id INTEGER REFERENCES dirigentes(id),
  org_id INTEGER REFERENCES organizaciones(id),
  tipo VARCHAR(20) CHECK (tipo IN ('start', 'stop', 'continue')),
  accion_texto TEXT NOT NULL,
  ventana_inicio TIMESTAMP,
  ventana_fin TIMESTAMP,
  ventana_duracion_dias INTEGER DEFAULT 14,
  criterio_exito JSONB,
  principio_conductual VARCHAR(100),
  evidencia_respaldo JSONB,
  estado VARCHAR(20) DEFAULT 'propuesta' CHECK (estado IN (
    'propuesta', 'aprobada', 'rechazada', 'modificada',
    'ejecutada', 'completada', 'fallida'
  )),
  post_ejecutor_id INTEGER REFERENCES social_posts(id) NULL,
  metricas_predichas JSONB,
  metricas_observadas JSONB,
  veredicto VARCHAR(20) NULL CHECK (veredicto IN ('exitosa', 'parcial', 'fallida') OR veredicto IS NULL),
  veredicto_editado_por_cliente BOOLEAN DEFAULT FALSE,
  veredicto_original VARCHAR(20) NULL,
  notas_cliente TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_recom_dirigente_estado ON recomendaciones_plan_ia(dirigente_id, estado);
CREATE INDEX idx_recom_ventana_activa ON recomendaciones_plan_ia(ventana_fin) WHERE estado = 'ejecutada';
CREATE INDEX idx_recom_veredicto ON recomendaciones_plan_ia(dirigente_id, veredicto) WHERE estado = 'completada';
```

### §6.4 Mejoras diferidas (Gemini audit Puerta 2, iteración posterior)

Hallazgos de Gemini audit marcados como **🟦 DIFERIDO** — NO se omiten, se documentan explícitamente para que próximas sesiones no los olviden.

| # | Hallazgo | Dimensión | Razón de diferir | Fecha objetivo revisión |
|---|---|---|---|---|
| DIFERIDO-01 | Renombrar `IpdRadarChart` → `SecondaryContextRadar` + crear `Tier1CoreGrid` como componente principal | Cosmética de componentes React | No bloquea MVP. Sprint S2 puede usar componentes tal cual; rename como housekeeping post-MVP | Post-S4 cierre (semana 5 aprox) |
| DIFERIDO-02 | Hito "Meta App Review Submission" en Sprint S5 para transición Dev Mode → Live antes del dirigente 26 | Escalabilidad comercial | Dev Mode soporta 25 admins sin App Review. Piloto opera 8 dirigentes — margen amplio. App Review toma 4-8 semanas post-submission; arrancar cuando lleguemos a 15-20 dirigentes contratados | Cuando clientes firmados lleguen a 15 |
| DIFERIDO-03 | `behavioral_logic_library.json` como RAG injectable para forzar justificación conductual §2.6.7 sistemáticamente | Ingeniería de prompts Plan IA | Sprint S4 ya incluye prompt con §2.6.7 obligatoria. Library separada es optimización. Si auditorías del MD review encuentran recomendaciones sin principio claro >20%, promover a Sprint | Tras primeras 100 recomendaciones aprobadas por MD review |

### §6.1 Decisiones pendientes CEO (input explícito requerido)

- [ ] **Arrancar Sprint S0 Validación de supuestos** — requiere comando directo del CEO
- [ ] **Resolver D-05 CONDICIONADA:** ejecutar análisis formal de outliers sobre los 4 anotadores humanos del eval 14-abr + CEO revisa resultado antes de sellar como gold standard
- [ ] **Budget ground truth humano adicional** — ¿anotar 100-500 rows extra este mes? Opciones: 3 anotadores MD internos · Upwork hispanohablante MX · postponer. Abierta tras D-01 schema v2 simplificado
- [ ] **UI vocab dashboard durante transición matriz v3** — apoyo/rechazo/neutral (recomendación Joy) vs vocab runner original vs dual labels
- [ ] **Priorizar cuál dirigente tendrá primer rollout OAuth** cuando firme contrato (test voluntario) — candidato lógico: Piña (ya es dataset piloto)
- [x] ~~Integrar §2.6 economía del comportamiento~~ — ✅ insertada verbatim 2026-04-19 (Claude.ai Opus 4.7)

---

## §7 — RIESGOS ESTRATÉGICOS Y LIMITACIONES

### §7.1 Riesgos estratégicos (formato Plan Maestro)

| Riesgo | Impacto si se materializa | Mitigación específica |
|---|---|---|
| **CIB Detector marca como troll a crítico legítimo** | Nota periodística viral destruye reputación del producto Y del cliente ancla MC CDMX | **Calibración MÍNIMA de 200 casos manualmente etiquetados antes de activar en producción** · Documentación algorítmica visible al cliente · Review manual del equipo del cliente sobre marcas dudosas · Disclaimer probabilístico visible en UI · Gobernanza auditable |
| **Scraping T2 con cuentas burner colapsa por cambios TOS Meta/X** | 60% de los bloques dependen de T2. Pérdida de servicio por días o semanas | Plan continuidad: rotación entre Brightdata/Crawlbase/ScraperAPI/Apify/PhantomBuster · T1 scraping público como fallback garantizado aunque degradado · Aceleración OAuth T3 para clientes afectados · Cuentas burner successor listas (@RafaRamos73/74) |
| **Veda electoral INE cambia criterio y obsoleta compliance preventivo** | Clientes candidatos formales dejan de percibir valor central del producto | Monitoreo activo acuerdos INE trimestral · Base de reglas como datos configurables en BD (no hardcoded) · Contrato con especialista legal para calibración anual |
| **Gemma 3:12b local degrada calidad vs Claude/ChatGPT** | Cliente compara output con ChatGPT directo y percibe inferior | Benchmark S2.6 ya demostró viabilidad (86.5/100 baseline) · Fallback a Claude API como feature premium opcional · Prompt engineering iterativo documentado en `backend/app/nlp/prompts/diagnostico_winner.md` |
| **Falla de memoria Claude Code genera deriva de sprint** | Sprints se alargan indefinidamente, MVP se pospone, ventana mercado se cierra | Disciplina documental §9 · NORTH-STAR.md obligatorio al inicio sesión · Gemini CLI como Puerta 2 pre-merge · Sesiones cortas 45-90 min con handoff forzado |
| **Percepción de producto como herramienta manipulación tipo Cambridge Analytica** | Pérdida contratos institucionales, daño reputacional MD Consultoría | Posicionamiento "inteligencia defensiva y ofensiva transparente" · Badge de fidelity visible (§3.4) · Compliance LFPDPPP y INE auditables · Aviso privacidad público · NO hacer psychographic profiling sin consentimiento |
| **SPOF hardware único — Mac M4 local corriendo Ollama Gemma 3:12b como producción** *(Gemini audit Puerta 2 #06)* | Fallo de disco, luz o red en el Mac M4 detiene el Plan IA de TODOS los clientes simultáneamente. Para un SaaS esto es inaceptable | **Ollama clúster Coolify como failover automático** (§8.6 Ollama Coolify VPS ya existe pero CPU-only lento). Backend hace health-check al Ollama local cada 60s; si falla >3 min, switch automático a Coolify (degradado pero funcional) con banner visible al usuario "modo degradado". Sprint S1 implementa la lógica. A 6 meses: evaluar migrar Gemma a GPU en Coolify (costo ~$200/mes EC2 con A10) |
| **Plan IA genera recomendación que viola veda INE, LFPDPPP o tono institucional** *(Gemini audit Puerta 2 #08)* | Una sola recomendación automatizada mal clasificada que cruce línea legal destruye reputación cliente + MD simultáneamente. Riesgo especialmente alto en precampaña y veda electoral | **Human-in-the-loop obligatorio §3.6** — ninguna recomendación sale al cliente sin review MD Consultoría. Endpoint cliente filtra obligatoriamente `estado IN ('aprobada', 'modificada', ...)` y NUNCA entrega `estado='propuesta'`. Test E2E bloquea merge si filtro no existe |

### §7.2 Riesgos operacionales secundarios

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Apify free tier $5/mes insuficiente al escalar | MEDIA | MEDIO | Costo actual $2.29. Proyección semanal $2.54. A 3-5 dirigentes extra se sobrepasa → plan BRONZE Apify ~$30/mes |
| Compliance INE violado accidentalmente | BAJA | MUY ALTO (multas) | Bloque #17 veda preventiva automática + audit log + escalación CEO pre-publicación |
| LFPDPPP datos PII expuestos | BAJA | MUY ALTO | PII encryption pgcrypto implementado Sprint C · PII_ENCRYPTION_KEY rotar pre-prod |
| Sesiones peer concurrentes colisionan filesystem | MEDIA | MEDIO | Reglas worktrees CLAUDE.md global · Verificar antes de abrir 2ª sesión |

### §7.3 Limitaciones de data en modo piloto (T1/T2)

Sin Meta OAuth no tenemos:
- Impresiones / reach exacto (aproximable solo con `views` en videos)
- Audience demographics detallado (solo inferido por autor de comments)
- Watch time / completion rate (Studio de cada plataforma post-login)
- CPA de pauta pagada (requiere Facebook Ads API)
- Saves en Instagram (privados, solo owner ve)

**Regla dura de transparencia:** el badge §3.4 `📊 Estimación de mercado` vs `📊 Oficial` es feature funcional obligatorio, no nota al pie. Cada card/widget lo muestra. Test E2E bloquea merge si falta.

### §7.4 Métricas de éxito del MVP (horizontes temporales)

**Sprint (cada 2-4 días) — 3 métricas binarias:**
1. El sprint cumplió los bloques declarados en SPRINT-CURRENT.md con demo E2E funcional → sí/no
2. Los tests de regresión sobre bloques previos siguen verdes → sí/no
3. HANDOFF.md quedó escrito con las 5 preguntas respondidas antes del cierre → sí/no

Tres síes, o se declara sprint fallido y se replanifica antes de continuar.

**MVP (4-5 semanas, cierre S0-S4, timeline expandido por D-17) — 5 métricas:**
1. Los **20 bloques Tier 1 + Tier 2** operando E2E (10 Tier 1 originales + #10.5 + #10.7 + 8 Tier 2) en modo T1/T2 con los 8 dirigentes piloto + badge transparencia visible
2. Un dirigente del piloto dispuesto a validar en sesión 45 min que las recomendaciones del Plan IA son accionables sin reinterpretación del equipo
3. Un candidato a cliente externo (fuera de los 8 piloto) haciendo demo de venta sobre su propia cuenta con data T1/T2 + queda para conversación de upgrade
4. Código OAuth activable implementado + testeado contra al menos 1 cuenta real de dirigente voluntario, aunque no desplegado en producción
5. **Ciclo completo del Plan IA demostrable E2E** *(nueva por D-17):* 1 recomendación generada → aprobada por MD review → aprobada por cliente → post publicado vinculado → seguimiento 14d con métricas diarias → veredicto automático + opción edición → aparece en memoria histórica #10.7

**Tracción comercial (90 días) — 3 métricas duras de validación de mercado:**
1. **3 pilotos reales** con figuras públicas de perfiles distintos ejecutados durante 90 días completos (contratos con fecha cierre, no gratis indefinidos): 1 político activo + 1 funcionario en ejercicio + (1 empresario en transición O 1 político en precampaña)
2. Al menos **1 caso documentado de recomendación de Plan IA efectivamente ejecutada** por el cliente con resultado medible (movimiento de SoV, breakout de post, reducción de rage click en tema controversial)
3. Al menos **1 conversión T1/T2 → T3** con OAuth firmado como validación de que el upgrade comercial funciona en práctica

**Criterio definitivo de éxito:** si en 90 días se logra mover una aguja real en un caso real → hay producto vendible y caso de estudio autovendible. Si no → el producto está construido sobre supuestos que necesitan recalibración antes de invertir más.

### §7.5 Deuda técnica acumulada (no bloqueante, retomar post-MVP)

- `@dnd-kit` Kanban Fase 2 (deuda ALTA Enrique, design review)
- PostHog API key producción pendiente CEO
- Docker DB se rompe ocasionalmente (Jess incidente) — requiere `alembic upgrade head + seed.py` al recrear
- Vercel frontend no puede autenticarse vs backend local (solo Docker localhost:3005)
- Playwright headless login falla si backend no levantado
- 246 TikToks sin texto pendientes de pipeline whisper+OCR (Pam md-research documentó)

---

## §8 — REFERENCIAS CRUZADAS

### 8.1 Documentos vivos de este repo

- **Este documento:** `.context/CRECE_PRODUCT_MASTER.md` (SSOT)
- **Síntesis de research 4 fuentes:** `backend/research/2026-04-19/SINTESIS-4-FUENTES.md`
- **Outputs research individuales:** `backend/research/2026-04-19/{sc_research,gemini,perplexity,gemini_deep_research}_response.md`
- **Reporte triangulación NLP:** `backend/evaluations/2026-04-18/output/REPORTE-TRIANGULACION.md`
- **Propuesta matriz v3:** `backend/evaluations/2026-04-18/output/PROPUESTA-MATRIZ-V3.md` (contexto, la decisión final está en §6)
- **Benchmark humano 2026-04-14:** `backend/eval/layer2_benchmark/reports/v2_2026-04-14/comparison_final.md`
- **Setup Meta OAuth (para Sprint S5):** `docs/META-OAUTH-SETUP.md`
- **Matriz polaridad v2 (pre-simplificación):** `docs/POLITICAL-FRAMEWORK-DEFAULTS.md`
- **Scrapers veredicto:** `docs/SCRAPERS-VEREDICTO-COMPLETO.md` · `docs/SCRAPERS-X-VEREDICTO.md`
- **Aviso privacidad LFPDPPP:** `docs/AVISO-PRIVACIDAD-CRECE.md`
- **Propuesta Índice Aceptación (pendiente decisión CEO):** `docs/PROPUESTA-INDICE-ACEPTACION.md`

### 8.2 Obsidian vault (knowledge base persistente)

- **Producto home:** `~/obsidian-md/productos/gobierno/crece-v2.md`
- **Bitácora triangulación:** `~/obsidian-md/productos/gobierno/crece-v2/bitacora/2026-04-18-triangulacion.md`
- **Research memory v2 matriz polaridad:** `~/obsidian-md/research/memory/2026-04-14-matriz-polaridad-v2-comments.md`
- **Research memory triangulación:** `~/obsidian-md/research/memory/2026-04-18-triangulacion-nlp-layer2.md`
- **Hallazgos día 14-abril:** `~/obsidian-md/productos/gobierno/crece-v2/bitacora/2026-04-14-hallazgos.md`

### 8.3 MCP memory (entidades JSON globales)

- `triangulacion-nlp-crece-2026-04-18` — resumen triangulación
- `gemma-ollama-benchmark-2026-04-14` — benchmark Ollama gemma3:12b aceptado producción
- `memory-stack-audit-2026-04-14` — audit stack memoria + Context Mode + Gbrain
- `pilot-eval-2026-04-21` — evaluación piloto programada

### 8.4 Auto-memory CRECE (Claude Code)

- **Índice:** `~/.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/MEMORY.md`
- **Memorias clave:** `project_triangulation_layer2_2026_04_18.md` · `project_5redes_veredicto.md` · `project_x_scrapers_veredicto.md` · `feedback_session_rem_errors.md`

### 8.5 GitHub

- **Repo:** https://github.com/MarxCha/crece-v2
- **PR abierto:** #12 (feat/eval-benchmark-v1)
- **Rama main HEAD:** `0681153`

### 8.6 Servicios externos

- **n8n prod:** https://n8n.mdconsultoria-ti.org
- **Chatwoot MX:** https://chatmx.mdconsultoria-ti.org
- **Ollama Coolify:** http://163.245.208.96:11434 (gemma3:12b — CPU-only, lento)
- **Ollama local Mac:** http://localhost:11434 (producción Gemma)

### 8.7 Fundamentación académica (150+ citas en `backend/research/2026-04-19/`)

Cada fuente primaria está disponible en los 4 documentos de research con link verificable. Esta sub-sección agrupa las referencias más relevantes **por área temática** para facilitar citas en comunicación comercial y defensa metodológica del producto.

**Framework Breakout Scale (bloque #02):**
- Brookings Institution — *The Breakout Scale: Measuring the Impact of Influence Operations* (Nimmo 2020, PDF brookings.edu). Framework original 6 categorías adaptado a política MX legítima.

**Comportamiento Inauténtico Coordinado / CIB (bloques #12, #13):**
- ITESO Signa_Lab — framework MCs + Cuentas Coro en México (tandfonline.com/doi/full/10.1080/25729861.2022.2035935)
- KJZZ — *Study In Mexico Reveals Unusual Patterns In Social Media Trolling*
- ResearchGate — *Political Social Media Bot Detection: ML Feature Selection*
- Facebook April 2021 CIB Report (baseline industry)
- MDPI — *Analyzing Political Polarization by Deleting Bot Spamming*

**Engagement Rate benchmarks políticos (bloque #01):**
- Hootsuite 2026 — Engagement rate benchmarks formulas (blog.hootsuite.com/calculate-engagement-rate)
- Rival IQ 2025 — *Social Media Industry Benchmark Report*
- Emplifi 2025 — Social Media Benchmarks (tabla por industria y tamaño)
- Sprout Social 2025 — Social media benchmarks by industry
- Gemini DR §2.2 — tabla Nano/Micro/Mid/Macro/Mega específica política

**Atribución de crecimiento — Time-Decay (bloque #07):**
- Adobe for Business — *Marketing attribution models and best practices*
- DiGGrowth — *Attribution Analysis Python* (scikit-learn + regresión)
- Sprinklr — *Social Media Attribution: Measuring, Models and Tactics*
- Socialinsider — *Social Media Attribution: How to Track ROI*

**Rage Click / polarización afectiva (bloque #15):**
- Tulane University (Freeman news) — *Rage clicks: Study shows how political outrage fuels social media engagement* (2024)
- ScienceDirect — *Negativity Spreads Faster*
- Northeastern Global News — *Algorithms' hidden political power* (2025)

**Cross-Partisan Interactions / validación cruzada (bloque #11):**
- MIT Sloan — *Strong evidence of political bias in formation of social media ties*
- arXiv 2603.20549 — *From Attention to Dialogue: Audience Engagement Reinforce Constructive Cross-Party Communication*
- PMC Springer — *Physical partisan proximity outweighs online ties*
- Princeton — *Political polarization and its echo chambers*

**Propaganda LLM detection y casos MX (bloque #10, #15):**
- ScienceDirect TecMty 2025 — *LLM Propaganda Detection Twitter Mexico*
- Tandfonline 2025 — *Political Communication MX/BR/CO Instagram*
- SAGE Journals — *WhatsApp Brazil Bolsonaro* (microtargeting + estrategias militia digital)
- AAAI ICWSM — *Strategies and Attacks of Digital Militias in WhatsApp Political Groups*

**Casos presidenciales analizados:**
- Merca2.0 — *Tiktómetro Sheinbaum Gálvez* (engagement granular 2024)
- Milenio — *Sheinbaum aventaja Facebook YouTube Instagram Xóchitl Gálvez*
- Oxford Internet Institute — *Mapping 2018 Mexican Election on Twitter and Facebook* (PDF demtech.oii.ox.ac.uk)
- AS/COA — *Approval Tracker Mexico President Claudia Sheinbaum*
- DFRLab — *Mexico's president weaponizes narratives against media*
- CFR — *WhatsApp's Influence in the Brazilian Election*
- Harvard Misinformation Review — *Brazilian Capitol attack*

**Compliance, transparencia, ética:**
- INE Mexico — *Conectados pero desinformados* (PDF ine.mx/wp-content/uploads/2025/11/)
- Rendición de Cuentas — *Partidos Políticos Mexicanos tus datos*
- ContraLaCorrupcion — *Movimiento Ciudadano exportó mercenarios digitales a Honduras*
- SPR Informa — *Estrategia digital Xóchitl Gálvez fracaso* (análisis $75.2M MXN + CIB)
- SocialTIC — *Tecnología y activismo para elecciones México 2024*

**Economía del comportamiento (mapea a §2.6):**
- **Kahneman & Tversky 1979** — *Prospect Theory: An Analysis of Decision under Risk*, Econometrica 47(2). Base teórica para el encuadre en modo pérdida vs ganancia (§2.6.1)
- **Kahneman 2011** — *Thinking, Fast and Slow*, Farrar Straus & Giroux. Distinción Sistema 1 / Sistema 2 aplicada al consumo político en redes sociales
- **Cialdini 2006** — *Influence: The Psychology of Persuasion* (Revised Edition), HarperCollins. Los 6 principios aplicados en el dashboard y Plan IA (§2.6.2)
- **Haidt 2012** — *The Righteous Mind: Why Good People Are Divided by Politics and Religion*, Pantheon. Moral Foundations Theory para bloque #05 y #15 (§2.6.3)
- **Bail et al. 2018** — *Exposure to opposing views on social media can increase political polarization*, PNAS 115(37) · DOI 10.1073/pnas.1804840115. Backfire effect y regla anti-confrontación frontal en Plan IA (§2.6.4)
- **Tajfel & Turner 1979** — *An integrative theory of intergroup conflict*, en Austin & Worchel (eds.) *The Social Psychology of Intergroup Relations*. Social Identity Theory aplicada a polarización mexicana 4T vs oposición (§2.6.5)

**Frameworks de reporte y dashboard (bloque #10, §4):**
- Atlassian Confluence — *Start-Stop-Continue Template*
- Tempo Software — *Start, Stop, Continue: Examples and feedback tips*
- Quorum — *How to Use Dashboards for a More Impactful Public Affairs Operation*
- Elections Group — *Data Visualization Basics for Election Administrators*

Para citas completas con links verificables, ver:
- `backend/research/2026-04-19/gemini_deep_research_response.md` (96 referencias con links)
- `backend/research/2026-04-19/sc_research_response.md` (18 referencias académicas)
- `backend/research/2026-04-19/perplexity_response.md` (35 referencias MX-heavy)
- `backend/research/2026-04-19/gemini_response.md` (8 referencias consolidadas)
- `backend/research/2026-04-19/SINTESIS-4-FUENTES.md` (síntesis cruzada)

---

## §9 — PROTOCOLO DE ACTUALIZACIÓN

### 9.1 Al abrir sesión (obligatorio)

1. Leer §0, §2, §6 de este documento
2. `git log --oneline -10` + `git status --short`
3. Reportar entendimiento al CEO en un párrafo + preguntar si procede

### 9.2 Durante la sesión

- **Toda decisión CEO → escribir inmediatamente en §6** (no confiar en que la conversación sobreviva)
- **Cambio de prioridad del roadmap → actualizar §5 antes de ejecutar**
- **Nueva limitación / riesgo detectado → añadir a §7**
- **Nuevo documento / recurso relevante → añadir a §8**
- **Si algo contradice con este documento → preguntar, NO asumir**
- **Si el CEO cambia algo verbalmente pero no se documenta → recordárselo: "¿quieres que lo persistir en §6?"**

### 9.3 Al cerrar sesión (obligatorio)

1. Actualizar §2 (estado actual) con los cambios del día
2. Si se cerró un sprint: actualizar §5 status (pending → in_progress → completed)
3. Reportar al CEO: "actualicé secciones X, Y, Z. Próximo paso documentado: [W]. ¿Commit?"
4. **No auto-commitear** — recomendarlo al CEO, que él decida

### 9.4 Reglas de higiene

- **Mantener este documento < 1,200 líneas.** Si crece más, extraer secciones muy estables a subdocumentos en `.context/archive/`
- **Nunca borrar decisiones de §6** — solo marcar como superseded con fecha
- **Un archivo `.context/PLAN-*.md` NO es SSOT. Este documento lo es.** Si hay divergencia, este gana.
- **`MEMORY.md` índice = facts puntuales** (credenciales, caveats). Este documento = estado + producto.

### 9.5 Convenciones de git commit para cambios en este doc

```
docs(master): actualiza §2 estado post-sprint S1

- Sprint S1 Backend Foundations cerrado
- 8 dirigentes con estrato + competidores
- Snapshot diario followers corriendo
- Próximo: Sprint S2 Diagnóstico Tier 1
```

### 9.6 Criterio de arranque duro (regla pre-Sprint S1)

**Aclaración importante sobre los documentos:** el MASTER (este documento) es el **documento estratégico + funcional de producto** — define qué construimos y por qué, con especificación mínima de cada bloque. El **PRD técnico** es un documento separado que aún NO existe y que se redactará como primer entregable post-Sprint S0. El PRD técnico baja cada bloque a especificación de implementación con esquemas SQL completos, endpoints FastAPI nuevos o extendidos, componentes React específicos a modificar (referenciando §3.5), tests E2E por bloque, y criterios de aceptación testables.

**MASTER v2.1 ya pasó revisión de terceros (Claude.ai Opus 4.7, 2026-04-19) con distinción.** El PRD técnico pasará por revisión análoga cuando se escriba.

**El desarrollo activo de CRECE v2 Tier 1 NO arranca hasta que existan los siguientes tres prerequisitos verificables:**

1. **NORTH-STAR.md consolidado** en `.context/` — ✅ creado 2026-04-19
2. **PRD técnico escrito y aprobado tras revisión cruzada** — Joy lo redacta basándose en este MASTER como fuente de verdad estratégica · CEO lo sube a Claude.ai Opus 4.7 para revisión de terceros · ajustes documentados en `.context/PRD-REVIEW.md` antes de cerrar el ciclo
3. **Sprint 0 de validación de supuestos completado** (§5 Sprint S0) con:
   - 3 documentos canónicos creados (NORTH-STAR + SPRINT-CURRENT + HANDOFF protocolo) — ✅ creados 2026-04-19
   - Benchmarks ER por estrato validados contra los 8 dirigentes con muestra real
   - Pipeline CIB básico testeado contra post Piña 200 comments + reporte de detección

**Saltarse cualquiera de los 3 = construir sobre fundamentos no validados = retrabajo garantizado.**

Esta regla es decisión arquitectural irreversible sin aprobación CEO explícita vía nueva entrada en §6.

### 9.7 Reglas de contención contra deriva (disciplina de sesiones)

Complementa §9.1-9.3 con disciplinas adicionales heredadas del Plan Maestro §8.3:

**Regla 1 — Worktrees separados para exploración vs implementación.** Si CEO pide explorar idea nueva, Claude Code lo hace en worktree dedicado que nunca toca branch principal. Exploración útil se migra por replicación manual, no por merge. Evita que experimentos a medias contaminen código de sprint. Práctica establecida en ramas `feat/sprint-c-hardening`, `feat/dirigente-surgery`, etc.

**Regla 2 — Gemini CLI como Puerta 2 antes de merges críticos.** Todo merge a `main` pasa por auditoría Gemini con prompt específico: *"Revisa este diff contra MASTER §3-5 y SPRINT-CURRENT.md y señala contradicciones o deriva de alcance"*. Este cross-check atrapa ~80% de problemas antes de que se vuelvan deuda técnica. Ya hay evidencia histórica de utilidad Gemini como cross-audit (decisiones D-DS-09 YouTube NO se oculta, D-NLP-02-03 defaults suaves).

**Regla 3 — Límite de duración por sesión.** NO dejar que Claude Code trabaje en sesiones de 4h donde contexto se degrada progresivamente. **Sesiones de 45-90 min con HANDOFF escrito al final** + descanso deliberado entre sesiones. Productividad acumulada es mayor con sesiones cortas bien cerradas que con sesiones largas mal cerradas.

### 9.8 Protocolo de dos puertas independientes para cambios estructurales al MASTER

**Patrón validado empíricamente en la sesión 2026-04-19** (v2.0 → v2.1 → v2.2 → v2.3): todo cambio estructural al MASTER pasa por dos revisiones independientes de agentes con dominios de evaluación complementarios antes del commit final.

**Puerta 1 — Claude.ai Opus 4.7** (rigor documental, coherencia narrativa, alineación estratégica):
- Entrega: versión completa del MASTER candidato para revisión
- Recibe: veredicto global + observaciones por sección + recomendación operativa

**Puerta 2 — Gemini CLI** (rigor de ingeniería, operación y compliance):
- Entrega: misma versión + Puerta 1 output
- Recibe: veredicto binario + hallazgos con severidad crítico/mejora + sugerencias concretas
- Archivado: cada auditoría Gemini queda en `.context/audits/gemini-master-vX.Y-audit-YYYY-MM-DD.md` para trazabilidad

**Integración:** Joy incorpora ambas auditorías en una sola versión final. Los hallazgos críticos se aplican sin debate. Los hallazgos "mejora" se evalúan caso por caso: aplicar ahora, documentar como 🟦 DIFERIDO con fecha objetivo, o descartar con razón explícita.

**Por qué funciona:** los dos agentes tienen dominios de evaluación naturalmente complementarios. Claude.ai detecta inconsistencias narrativas que Gemini no ve por no rastrear historial conversacional. Gemini detecta gaps de compliance / ingeniería / operación que Claude.ai no ve por operar en capa estratégica. La unión de las dos perspectivas aproxima una revisión completa; una sola puerta monopoliza sesgo cognitivo de un solo dominio.

**Regla:** cualquier cambio estructural futuro al MASTER (nueva sección, cambio de arquitectura, decisión crítica D-XX) pasa por este protocolo antes del commit. Cambios menores (typo, broken link, reordenamiento cosmético) quedan exentos.

**Ejemplo histórico validado:** v2.3 integró 4 hallazgos críticos Gemini (#04 ARCO, #05 reconciliación T1→T3, #06 SPOF Mac M4, #08 human-in-the-loop) que Puerta 1 no detectó. Sin Puerta 2, esos gaps habrían salido a producción.

---

## FIN DEL DOCUMENTO

**Cambios históricos:**
- **2026-04-19 v2.3** (Joy, post-audit Puerta 2 Gemini CLI + propuesta consolidada D-17 CEO) — **3 decisiones nuevas** (D-16 provider LLM unificado · D-17 cierre de ciclo Plan IA con 4 parámetros CEO fijados · D-18 endpoint ARCO purge-hash). **6 ajustes críticos Gemini** aplicados: §3.6 Human-in-the-loop obligatorio · §4.5 data_origin_checkpoint reconciliación T1→T3 · §7.1 riesgo SPOF Mac M4 + mitigación Ollama Coolify failover · Sprint S0 T0.4 validación Plutchik ciega · Sprint S1 expansión con tabla recomendaciones + ARCO endpoint · Sprint S4 expansión con ciclo 5 fases. **2 bloques nuevos** #10.5 Seguimiento + #10.7 Memoria (32 bloques efectivos ahora). **3 mejoras diferidas** explícitamente documentadas en §6.4 con fecha objetivo. **Nueva §9.8** protocolo dos puertas independientes Claude.ai + Gemini para futuros cambios estructurales. **MVP timeline expandido 3-4s → 4-5s** aprobado CEO parámetro 1 D-17.
- **2026-04-19 v2.2** (Joy, post-revisión terceros Claude.ai Opus 4.7) — 3 observaciones menores aplicadas: (1) nota aclaratoria en §3.1 sobre "T1 funciona pleno" = post-Sprint S1 completado; (2) §9.6 clarifica distinción MASTER estratégico vs PRD técnico separado (aún no redactado); (3) D-15 nueva formaliza Gemma 3:12b local como provider primario Plan IA en lugar de Claude API default. MASTER aprobado con distinción para commit.
- **2026-04-19 v2.1** (Joy) — inserción verbatim §2.6 economía del comportamiento (Claude.ai Opus 4.7, 7 subsecciones) + actualización §8.7 con 6 citas académicas específicas (Kahneman 1979/2011, Cialdini 2006, Haidt 2012, Bail PNAS 2018, Tajfel 1979) + cierre D-08 en §6 + checkbox §6.1 economía conductual marcado ✅.
- **2026-04-19 v2.0** (Joy + Claude.ai Opus 4.7) — sincronización con Plan Maestro v1.0: añadidas §1.5 (4 perfiles cliente), §2.1-2.5 (estado granular), §2.6 placeholder economía conductual, §3.4 (requisito transversal badge fidelity), §3.5 (25 componentes React con marcado IPD-legacy/agnóstico), §5 Sprint S0 (validación supuestos), §6 reestructurada con leyenda status + 14 decisiones + matiz IPD degrada-no-muere, §7 riesgos estratégicos con mitigación CIB 200 casos calibración, §7.4 métricas éxito sprint/MVP/tracción 90d, §8.7 fundamentación académica, §9.6 criterio de arranque duro, §9.7 reglas de contención.
- **2026-04-19 v1.0** creación inicial (Joy) post-sesión de investigación 4 fuentes + arquitectura dual-mode
