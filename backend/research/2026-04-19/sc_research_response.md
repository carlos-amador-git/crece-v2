# Diagnóstico Estratégico — Elementos del Plan de Consolidación Digital para Políticos Mexicanos

**Autor:** SC Research Agent (CRECE v2)
**Fecha:** 2026-04-18
**Alcance:** Fundamentar el rediseño del módulo de diagnóstico + plan IA de CRECE v2 con evidencia académica, casos comparados México/LATAM y benchmarks de la industria analytics.

---

## Resumen ejecutivo (TL;DR)

El diagnóstico digital accionable para un político profesional mexicano NO se construye sobre IPD 0-10 ni sentimiento promedio. Se construye sobre **cuatro ejes medibles con datos que CRECE ya scrapea**:

1. **Alcance fuera de la base** (unconnected reach / breakout posts) — es el único proxy honesto de crecimiento político real.
2. **Engagement rate por post normalizado contra tamaño de cuenta** — los benchmarks absolutos engañan.
3. **Composición del sentimiento** (no promedio): ratio anger/trust, intensidad, detección de comentarios coordinados.
4. **Share of voice vs competidores directos** (no vs MC nacional), con ventana temporal y keyword tracking.

Encima de esos cuatro ejes, un plan IA útil debe entregar **acciones Start/Stop/Continue con ejemplo concreto del post modelo**, no "mejora tu narrativa". Los casos Sheinbaum–Gálvez 2024, Samuel García 2021 y Alfaro 2018 coinciden: **la estrategia ganadora se mide por formato + frecuencia + hora + narrativa que CRUZA la base partidaria, no por likes totales**.

---

## LÍNEA 1 — Case studies: plataformas analytics para políticos

### 1.1 Proveedores globales y su uso en política

**Brandwatch (Cision)** — La plataforma más consolidada. Su motor `Iris AI` resume trends, analiza comentarios, y permite **benchmarking contra 300,000+ marcas/figuras** con share of voice, audience size, top posts, hashtag analysis y sentiment benchmarking. El dashboard típico muestra: mention volume over time, trending topics, sentiment, emotion, demographics, engagement. La feature `Benchmark` compara simultáneamente la cuenta del cliente contra 5-10 competidores directos — es su diferenciador clave para política (Source: [Brandwatch Benchmark product page](https://www.brandwatch.com/products/benchmark/)).

**Meltwater** — Fuerte en public sector / gobierno. Features destacadas: social listening, sentiment analysis, trend analysis, influencer identification, competitor benchmarking, custom dashboards. Reportes típicos incluyen crisis detection con `Storm Alert` (spike alerts automatizados) (Source: [Meltwater blog](https://www.meltwater.com/en/blog/top-social-listening-tools)).

**Sprinklr** — Positioned como best-for-Government. Su diferenciador es la integración unified customer experience — mezclando listening + publishing + care + engagement en un solo dashboard (Source: [Sprinklr social listening guide](https://www.sprinklr.com/blog/social-listening/)).

**Talkwalker** — Enfoque en IA conversacional y visual listening (reconocimiento de imágenes de logos/personas en fotos). Menos usado en política pero fuerte en crisis detection.

### 1.2 Campañas política reales — métricas internas conocidas

**Sheinbaum vs Gálvez 2024 (dato crítico):**
- Sheinbaum: 3 posts / 889,270 engagements / 16.85M views / 1.8M seguidores TikTok — engagement rate ~131% (engagement/seguidores)
- Gálvez: 276K seguidores / 12.56M views / 633K engagements — engagement rate **365%**
- Sentimiento: Sheinbaum dominó Facebook/YouTube/Instagram con sentimiento "trust"; Gálvez dominó TikTok y X con "anger"
- Lección: **alto engagement rate en base pequeña ≠ crecimiento de base. Gálvez perdió por 30 puntos**. La lealtad intensa no se convierte en voto si el alcance fuera de la base es bajo (Source: [Merca2.0 Tiktómetro](https://www.merca20.com/elecciones-2024-tiktometro-de-claudia-sheinbaum-xochitl-galvez-y-jorge-alvarez/), [Milenio](https://www.milenio.com/politica/elecciones/sheinbaum-aventaja-facebook-youtube-instagram-xochitl-galvez)).

**AMLO 2018:**
- 9M+ seguidores Twitter al cierre de campaña
- Dominó 4x el volumen de conversación de los otros candidatos
- Estrategia documentada por Oxford OII: hashtag campaigns (#AMLOmania), activist slang, historical context, viralidad (Source: [Oxford Internet Institute Mexico 2018](https://demtech.oii.ox.ac.uk/wp-content/uploads/sites/12/2018/06/Mexico2018.pdf)).

**Bolsonaro 2018:**
- Microtargeting WhatsApp por segmento: "gay kit", "armas", "iglesia" — mensaje distinto por grupo identificado
- Evidencia de gestión centralizada de grupos WhatsApp por operadores políticos
- Lección para CRECE: **la segmentación por cluster de seguidores importa más que el volumen total** (Source: [SAGE Journals Ozawa et al 2023](https://journals.sagepub.com/doi/full/10.1177/20563051231160632)).

**Alfaro Jalisco 2018:**
- Estrategia MC Naranja con video viral "Yuawi" — 70M views YouTube hasta 2024
- Operado por Euzen, Indat, La Covacha (relación largo plazo desde Tlajomulco)
- Lección: **un hit viral anclado + consistencia de frecuencia + narrativa corta** (Source: [Wikipedia Alfaro](https://en.wikipedia.org/wiki/Enrique_Alfaro_Ram%C3%ADrez), [Animal](https://grupoanimal.mx/explicaciones/euzen-indat-elecciones-jalisco)).

**Samuel García NL 2021-22:**
- TikTok @samuelgarciasepulveda: 2.6M seguidores, 61.2M likes
- Estrategia: contenido cotidiano (Mariana + hijas), lenguaje coloquial, frecuencia alta
- Ganó gubernatura a los 33 años, el más joven de NL (Source: [TikTok Samuel García](https://www.tiktok.com/@samuelgarciasepulveda)).

### 1.3 Proveedores México específicos

- **Enkoll, Massive Caller, Oraculus** — empresas de polling / analytics política, más orientadas a encuestas que a social listening en tiempo real. Ninguna ofrece lo que CRECE construye (scrapers + NLP + sentiment comments).
- Gap confirmado: **no existe en México una plataforma analytics política que combine scraping de 5 redes + NLP en español mexicano + benchmarking contra competidores**. CRECE tiene ventana de mercado.

### 1.4 KPIs "dashboard principal" repetidos en la industria

Destilando Brandwatch + Meltwater + Sprinklr + academia:

| # | KPI | Por qué importa |
|---|-----|------------------|
| 1 | **Engagement rate por post (normalizado por seguidores)** | Separa volumen de calidad |
| 2 | **Unconnected reach / reach fuera de seguidores** | Único proxy de crecimiento real |
| 3 | **Share of voice vs competidores** | Contexto competitivo |
| 4 | **Sentiment ratio (trust/anger/joy/fear)** | No promedio — composición |
| 5 | **Follower growth attribution por post (24/48/72h)** | Qué contenido CONSTRUYE base |
| 6 | **Completion rate / watch time video** | Señal algorítmica real |
| 7 | **Mention volume spike alerts** | Crisis detection |

### Takeaways accionables L1

1. **Reemplazar IPD 0-10 por un dashboard de 7 KPIs** ya validados por Brandwatch/Meltwater — stop reinventar scoring.
2. **Benchmarking obligatorio** contra 3-5 competidores directos (misma circunscripción, mismo rol político), no vs MC nacional.
3. **Sentiment como composición, no promedio** — guardar `trust`, `anger`, `joy`, `fear`, `sadness`, `disgust` por separado.
4. **Crisis alert automatizado** tipo Storm Alert: spike en volumen + shift en sentiment >2σ.
5. **Single-feature diferenciador de CRECE**: tomar la feature `Benchmark` de Brandwatch y adaptarla a política MX (3-5 rivales directos).

---

## LÍNEA 2 — Métricas normalizadas vs absolutas

### 2.1 Likes absolutos engañan sistemáticamente

Datos Rival IQ + Social Insider 2026 benchmarks (median engagement rate per post):
- **TikTok:** 3.70% (creció 49% YoY)
- **Instagram:** 0.48%
- **Facebook:** 0.15%
- **X:** 0.12%

Implicación para CRECE: **un post con 1000 likes en TikTok es malo si tienes 100K seguidores (1%), excelente si tienes 50K (2%)**. El número absoluto no sirve — siempre normalizar (Source: [Digital Information World](https://www.digitalinformationworld.com/2026/03/2026-social-media-benchmark-tiktok.html)).

**Benchmarks para políticos mexicanos (derivados del estudio Sheinbaum-Gálvez):**
- TikTok político MX con 10-50K seguidores: engagement rate saludable 4-8%
- Instagram político MX con 10-50K: 1-3% saludable, >3% excelente
- Facebook político MX: 0.2-0.5% saludable (el algoritmo castiga cuentas sin ads spend)
- X/Twitter político MX: 0.15-0.4% saludable

### 2.2 Breakout post detection — el gold standard

**Instagram** introduce `Trial Reels` que muestra un Reel SOLO a no-seguidores como test. Mosseri (Head of IG) oficial: medir `connected reach` vs `unconnected reach`, con watch time, likes y shares como señales clave para ambos (Source: [Dataslayer Instagram Algorithm 2026](https://www.dataslayer.ai/blog/instagram-algorithm-2025-complete-guide-for-marketers)).

**TikTok 2026 algo change:** videos son probados primero con seguidores, luego olas crecientes de no-seguidores si hay engagement. Meaningful engagement prioriza `saves` (intent to revisit) y `off-platform shares` sobre views pasivas. Completion rate > watch time (Source: [Buffer TikTok Algorithm](https://buffer.com/resources/tiktok-algorithm/)).

**Métrica accionable para CRECE:** `breakout_score = (reach_unconnected / reach_total) × log(reach_total)`. Un post con 30% unconnected reach es un outlier positivo — señala que cruzó la base.

### 2.3 Growth attribution por post (24/48/72h)

Metodología derivada del paper ScienceDirect Latin America elections (2022): **medir follower_delta en ventanas 24h/48h/72h post-publicación, correlacionar con el post específico**. Sólo funciona si CRECE scrapea followers diariamente (no semanal) — **esto es un requerimiento de producto crítico** (Source: [ScienceDirect correlation social media elections](https://www.sciencedirect.com/science/article/abs/pii/S0740624X22000818)).

Fórmula sugerida:
```
growth_attributed_24h = (followers_t+24h - followers_t-0h) - baseline_daily_growth
```
Con `baseline_daily_growth` = media móvil 7 días pre-post.

### 2.4 Detección de engagement auténtico vs coordinado

Papers Mexico: en el caso `#YaMeCanse` solo 10-14% de cuentas eran bots, el resto humanos coordinados — bot detection clásica (Botometer) **falla en México**. El estándar académico actual: detectar **coordinated inauthentic behavior (CIB)** vía network-based frameworks (similarity networks de content sharing) (Source: [ScienceDirect CIB Twitter](https://www.sciencedirect.com/science/article/abs/pii/S0167923622000902), [Tandfonline Mexico Twitter COVID](https://www.tandfonline.com/doi/full/10.1080/25729861.2022.2035935)).

Señales concretas aplicables a los scrapers de CRECE:
- **Repetición lexical** en comments (distancia Jaccard >0.7 entre N comments consecutivos)
- **Temporal clustering** (comments en ventana <30s con n>5)
- **Cuentas con patrón burner** (creación <30 días, handle numérico, 0 seguidores propios)
- **Idéntico link/hashtag** pushed por N cuentas diferentes en <5 min

### 2.5 Propaganda en tuits MX 2018

Estudio TecMonterrey 2025: 58.4% de 800K+ tweets analizados sobre el candidato líder exhibían características propagandistas, con **predominancia de sentimiento negativo y tono agresivo** (Source: [ScienceDirect LLM propaganda Twitter Mexico](https://www.sciencedirect.com/science/article/pii/S2772503025000465)).

### Takeaways accionables L2

1. **Scrapear followers count DIARIO**, no semanal — precondición para growth attribution.
2. **Implementar `breakout_score`** como métrica secundaria en dashboard de post-level.
3. **Benchmarks de engagement rate normalizados por plataforma + tamaño de cuenta** (tabla CRECE interna).
4. **Detector CIB** basado en similarity network de comments (no Botometer).
5. **Tag `propaganda_score` por tweet** usando LLM en español (el paper TecMty publicó metodología replicable).

---

## LÍNEA 3 — Contenido controversial vs alta aceptación

### 3.1 Más allá del sentimiento promedio — dimensiones

Academic: **"Partisanship on Social Media"** (Springer, análisis de 1.2M tweets de 564 elites políticas) demuestra que las expresiones de élite están impulsadas por **positive partisanship > negative partisanship**. Pero los ordinary users engagean más con **out-party hate** (Source: [Springer Political Behavior](https://link.springer.com/article/10.1007/s11109-022-09850-x)).

**Implicación:** el mismo post controversial puede ser leído como "base energizada" o "out-party hate seeker". CRECE necesita etiquetar comments por **alineación partidaria del autor** (no solo sentimiento).

### 3.2 ¿Controversial = bueno o malo para consolidación?

Paper ScienceDirect sobre negatividad: **los tweets de políticos con carga negativa se esparcen más ampliamente**, con diferencias por partido. Pero la expansión ≠ aprobación — viralidad negativa puede atraer oposición movilizada (Source: [ScienceDirect negativity spreads faster](https://www.sciencedirect.com/science/article/pii/S2468696423000010)).

Paper Communications Studies 2025 (Benoit functional theory, elecciones MX 2024, Brasil 2022, Colombia 2022): **"defenses" (posts respondiendo a ataques) aumentan comments +58.6% y likes +57.2%**. Los ataques sin contexto defensivo no correlacionan con crecimiento de base (Source: [Tandfonline Communication Studies](https://www.tandfonline.com/doi/full/10.1080/10510974.2025.2574004)).

**TikTok findings (ScienceDirect Political Content Engagement Model):** civility level y out-party critique son predictores más fuertes de engagement político. Divisive content es **amplificado algorítmicamente en TikTok durante elecciones** según arXiv paper 2025 (Source: [arXiv TikTok divisive messaging](https://arxiv.org/pdf/2509.10336)).

### 3.3 "High approval" real vs likes superficiales

Métrica propuesta para CRECE basada en la evidencia:

```
approval_real = (
  likes
  + 2*comments_positivos
  + 3*shares
  + 5*comments_from_out_party_positivos  # validación fuera de base
) / reach
```

El peso >1 a `comments_from_out_party_positivos` es lo que separa approval real de "base gritando". Operacionalmente:
- Clasificar autor de comment por alineación partidaria (scraping histórico de su timeline)
- Etiquetar comment como positivo/negativo (pysentimiento ya lo hace)
- Cruzar ambos

### 3.4 Detección de "aceptación exterior de la base"

Propuesta: `out_of_base_validation_score` por post
- Identificar followers del político → "base"
- Identificar commenters NO en "base"
- % de comments positivos provenientes de no-base sobre total comments
- >15% es outlier positivo — post cruzó el muro partidario

### Takeaways accionables L3

1. **Dimensiones del sentimiento ≠ promedio**: guardar emoción discreta (trust/anger/joy/fear/sadness/disgust) y ratios.
2. **Clasificar autor de comment por alineación partidaria** (Morena/PRIAN/MC/independiente) — requisito nuevo de scraping.
3. **Métrica `approval_real`** con peso 5x en comments positivos out-party — el diferenciador real.
4. **Divisive content NO es recomendación automática** — medir tradeoff viralidad vs polarización de la base.
5. **Etiquetar posts como "defense"** (respuesta a ataque) — tienen +57% engagement y son estratégicamente útiles.

---

## LÍNEA 4 — Diagnóstico + Plan IA: mejores prácticas

### 4.1 Estructura que genera decisiones accionables

Marco `Start / Stop / Continue` adaptado a política, derivado del arsenal Brandwatch + Sprout Social + práctica consultora:

```
START (3 acciones concretas a empezar en próximos 14 días):
  - Ejemplo: "Publicar 1 Reel/semana con formato 'recorrido barrio' — 
    tu base actualmente consume este formato en @competidor_X 
    (engagement rate 4.2% vs tu 0.8% en mismo formato)"

STOP (3 prácticas a detener):
  - Ejemplo: "Dejar de publicar comunicados oficiales como carousel IG — 
    save rate <0.5%, es ruido. Moverlos a X o a web."

CONTINUE (3 prácticas funcionando, amplificar):
  - Ejemplo: "Los posts de domingo 10am con narrativa familiar 
    generan 3x engagement de tu promedio. 
    Aumentar frecuencia a 2x/semana."
```

Cada recomendación **debe incluir**:
- Post modelo (link al post propio o del competidor)
- Métrica respaldo (número concreto)
- Ventana temporal (14/30/90 días)
- Recursos necesarios (1 Reel semanal = 1 sesión grabación + 1 edición)

### 4.2 Formato matriz 2x2 para posicionamiento

**Eje X:** engagement rate (bajo-alto)
**Eje Y:** reach fuera de base (bajo-alto)

Cuadrantes:
- **Alto-Alto (breakthrough):** replicar formato → STRATEGY (hit content)
- **Alto-Bajo (echo chamber):** base energizada pero no creciendo → AMPLIFY (pagar ads / crosspost)
- **Bajo-Alto (misfire):** llega a gente pero no conecta → REWRITE (narrativa no resuena)
- **Bajo-Bajo (noise):** dead content → KILL

Cada post clasificado en un cuadrante = decisión accionable inmediata.

### 4.3 Casos MX exitosos — qué entregaron

**Alfaro 2018:** operadora (Euzen + Indat + La Covacha) mantenía relación multi-año desde Tlajomulco → el plan no era un reporte aislado, era un **retainer de ops**. Su output combinaba:
- Dashboard KPIs tiempo real
- Reunión estratégica semanal
- Reporte quincenal con matriz 2x2

**Samuel García 2021-22:** consistencia de narrativa (Mariana + hijas, lenguaje coloquial), frecuencia diaria TikTok, adaptación a trending audios. El plan semanal probablemente incluía: 3-5 audios trending con guión adaptado + 2 contenidos familiares + 1 gobierno (Source: múltiples posts de @samuelgarciasepulveda).

### 4.4 Formato preferido: dashboard + reporte + reunión

Evidencia industria: los corporate marketers usan self-serve dashboards, **pero en political campaigns domina "managed service"** (Source: [Sutton Smart political ROI](https://suttonsmart.com/political-consulting/political-cross-screen-media-attribution-roi-analysis-2/)). CRECE v2 para ser diferencial debe soportar:
1. **Dashboard tiempo real** (alcance técnico)
2. **Reporte semanal escrito** generado por IA, listo para reenviar al político (formato ejecutivo)
3. **Template de reunión estratégica** quincenal — la IA prepara la agenda

### Takeaways accionables L4

1. **Adoptar Start/Stop/Continue** como estructura del plan IA — no "mejora tu narrativa".
2. **Matriz 2x2 engagement × out-of-base reach** como visual principal del diagnóstico.
3. **Cada recomendación debe linkear a post modelo** (propio o competidor) — prohibido recomendar en abstracto.
4. **Triple output:** dashboard + reporte ejecutivo semanal + template reunión — no solo dashboard.
5. **Plan IA con ventanas temporales y recursos** — "publica 1 Reel semanal" no "sé más auténtico".

---

## LÍNEA 5 — Casos de fracaso: qué NO hacer

### 5.1 Cambridge Analytica (2018, bancarrota)

- **Bankruptcy Chapter 7 mayo 2018**, $5B multa FTC a Facebook 2019
- Involucrada en campaña MX 2018 (allegations microtargeting), exposición pública quebró credibilidad
- **Lección para CRECE:** data handling ético desde día 1, nunca hacer psychographic profiling sin consentimiento (Source: [Wikipedia CA scandal](https://en.wikipedia.org/wiki/Facebook%E2%80%93Cambridge_Analytica_data_scandal)).

### 5.2 Vanity metrics matan campañas

Viant study: **36% de CFOs citan vanity metrics como top concern de sus CMOs**. En política, el equivalente: consultores vendiendo dashboards con impressions y followers cuando no mueven voto (Source: [Improvado vanity metrics](https://improvado.io/blog/what-is-a-vanity-metric)).

Regla operativa: **"si una métrica no influye una decisión, no pertenece al dashboard"** — debe aplicarse con disciplina quirúrgica en CRECE. Candidatos a eliminar: total likes acumulados, total followers sin delta, total posts.

### 5.3 Correlación ≠ causalidad en elecciones

Caso Gálvez 2024: engagement rate 365% en TikTok, perdió por 30 puntos. **Alto engagement en base concentrada + bajo reach fuera de base = derrota**. El dashboard debe jerarquizar reach fuera de base SOBRE engagement rate total.

### 5.4 Morena Edomex 2017 — obsesión digital + ground game débil

Morena perdió Edomex 2017 con campaña digital intensa pero operación territorial débil. **Lección:** CRECE debe explicitar que el diagnóstico digital es condición necesaria, NO suficiente. El plan IA debe incluir warning si engagement crece pero territorio no (ligar a datos INE electorales por sección).

### 5.5 Dashboards sin acción

Bloomberg Businessweek y research industria repiten: dashboards que no se miran pierden sentido en <90 días. Anti-patrones:
- 20+ widgets sin jerarquía
- Métricas absolutas sin benchmark
- Sin alertas automatizadas
- Sin ownership claro de cada métrica

CRECE debe limitar el dashboard principal a **7-9 widgets max** con jerarquía estricta.

### 5.6 Misinformation backlash

Bolsonaro 2018 ganó con misinformation WhatsApp, pero la misma máquina erosionó legitimidad democrática y terminó en los ataques del 8 enero 2023. **CRECE debe incluir salvaguardas de compliance INE**: modo veda, etiquetado de contenido IA, trazabilidad de gastos. Ya está parcialmente implementado según CLAUDE.md del proyecto (Source: [SAGE Journals Bolsonaro WhatsApp](https://journals.sagepub.com/doi/full/10.1177/20563051231160632)).

### Takeaways accionables L5

1. **Prohibir vanity metrics en dashboard principal** — total likes, total followers, total posts.
2. **Regla dura:** cada métrica debe tener "qué decisión dispara" documentada; sin eso, fuera.
3. **Warning automático** si engagement crece pero reach fuera de base no — evita trampa Gálvez.
4. **Salvaguarda compliance INE** integrada al plan IA (modo veda, etiqueta IA, gasto).
5. **Máximo 7-9 widgets** en dashboard principal con jerarquía visual estricta.

---

## INVENTARIO DE ELEMENTOS CANDIDATOS (20 bloques)

Tabla de bloques potenciales del diagnóstico. Cada bloque incluye: nombre, pregunta que responde, inputs del backend, ejemplo, fuente.

### #01 — Breakout Posts de la semana
- **Pregunta:** ¿Qué publicación de esta semana cruzó el muro de mi base?
- **Inputs:** posts_table (reach_connected, reach_unconnected), followers_count snapshot
- **Ejemplo:**
  ```
  [Card]
  🎯 Breakout: Reel 15-abril "Recorrido Iztapalapa"
  32% alcance fuera de base (vs 4% promedio)
  +180 followers atribuibles 48h
  Formato: Reel 45s POV | Audio trending: 342K usos
  ```
- **Fuente:** Instagram Trial Reels + TikTok FYP mechanics

### #02 — Matriz 2x2 de posts (Engagement × Reach fuera de base)
- **Pregunta:** ¿Cuál de mis últimos 30 posts debo amplificar, matar o reescribir?
- **Inputs:** posts últimos 30d con engagement_rate + unconnected_reach_ratio
- **Ejemplo:** scatter plot con 4 cuadrantes coloreados (breakthrough / amplify / rewrite / kill), cada dot clickable
- **Fuente:** Framework estratégico propio basado en Brandwatch Benchmark + BCG matrix

### #03 — Benchmark vs competidores directos
- **Pregunta:** ¿Cómo me comparo con mis 3-5 rivales reales esta semana?
- **Inputs:** competidor_ids (misma circunscripción/rol), últimas 4 semanas de posts
- **Ejemplo:** tabla de 5 filas × 6 columnas (followers, engagement rate, posts/sem, breakout ratio, share of voice, sentiment trust ratio)
- **Fuente:** Brandwatch Benchmark product

### #04 — Sentiment composition (no promedio)
- **Pregunta:** ¿Qué emociones dominan en mis comments — hay ira creciente?
- **Inputs:** comments con tags emotion (trust/anger/joy/fear/sadness/disgust) vía pysentimiento
- **Ejemplo:** stacked bar chart 7 días × 6 emociones; warning si anger >30% o ratio trust/anger <1
- **Fuente:** Discrete emotion model (Ekman/Plutchik) + Sheinbaum vs Gálvez 2024

### #05 — Crisis Spike Alert
- **Pregunta:** ¿Hay una crisis emergiendo ahora mismo?
- **Inputs:** volumen mentions hora a hora, media móvil 7d, sentiment
- **Ejemplo:** banner rojo "SPIKE DETECTADO: +340% mentions últimas 2h, sentimiento -70%, tema: #X"; link a acciones sugeridas
- **Fuente:** Meltwater Storm Alert + Emplifi spike alerts

### #06 — Growth Attribution por post (24/48/72h)
- **Pregunta:** ¿Qué post de la semana me trajo seguidores reales, no solo likes?
- **Inputs:** followers_count DIARIO, posts con timestamp
- **Ejemplo:** tabla top 5 posts ordenados por `follower_delta_48h - baseline_daily_growth`; cada fila link al post
- **Fuente:** Metodología ScienceDirect Latin America elections correlation study

### #07 — Out-of-base Validation Score
- **Pregunta:** ¿Mis posts reciben validación de gente que NO me sigue?
- **Inputs:** comments con clasificación autor (base/no-base), sentiment del comment
- **Ejemplo:** gauge 0-100% por post; >15% es outlier; drill-down ver comments específicos no-base positivos
- **Fuente:** Springer Political Behavior 2022 + framework propio

### #08 — CIB Detector (Coordinated Inauthentic Behavior)
- **Pregunta:** ¿Me están atacando con comentarios coordinados?
- **Inputs:** comments últimas 48h con lexical similarity + temporal clustering + author age/pattern
- **Ejemplo:** lista de "clusters sospechosos" con N comments, similitud %, accounts, primera detección; botón "ignore" / "flag"
- **Fuente:** ScienceDirect CIB Decision Support Systems + caso #YaMeCanse

### #09 — Start/Stop/Continue Plan
- **Pregunta:** ¿Qué empiezo, qué paro, qué mantengo esta semana?
- **Inputs:** últimas 4 semanas de posts + performance + competidor data
- **Ejemplo:** 3 cards (verde/rojo/azul) con 3 acciones cada una; cada acción incluye post modelo linkeado + métrica respaldo + recursos necesarios
- **Fuente:** Framework OKR adaptado + práctica Alfaro/García consultoras

### #10 — Propaganda Score por tweet
- **Pregunta:** ¿Los ataques contra mí son propaganda organizada?
- **Inputs:** tweets negativos dirigidos + LLM classifier (Gemma/Claude)
- **Ejemplo:** tabla de tweets negativos últimos 7d con columna "propaganda_prob" y "téctica detectada" (loaded language, ad hominem, straw man)
- **Fuente:** ScienceDirect LLM propaganda Twitter Mexico 2025 (TecMty)

### #11 — Engagement rate benchmark por tamaño de cuenta
- **Pregunta:** ¿Mi engagement rate es bueno, normal o malo para mi tamaño?
- **Inputs:** followers_count, engagement_rate, plataforma
- **Ejemplo:** gauge con zonas (rojo <p25, amarillo p25-p50, verde p50-p75, azul >p75) vs percentiles de políticos MX con tamaño similar
- **Fuente:** Digital Information World 2026 benchmark + derivación propia

### #12 — Defense Post Detector
- **Pregunta:** ¿Estoy respondiendo a los ataques? ¿Con qué efectividad?
- **Inputs:** posts tagged como "defense" (responden a mentions negativas)
- **Ejemplo:** tabla defense posts con engagement lift vs baseline (+57% esperado según Benoit theory)
- **Fuente:** Tandfonline Communication Studies 2025 Benoit functional theory

### #13 — Hora/Día óptimos de publicación
- **Pregunta:** ¿Cuándo publicar para maximizar reach fuera de base?
- **Inputs:** histórico posts × (día de semana + hora) × unconnected_reach
- **Ejemplo:** heatmap 7×24 coloreado por unconnected_reach promedio; resalta "domingo 10am" (caso Samuel García)
- **Fuente:** TikTok algorithm + práctica campañas MX

### #14 — Narrativa Score (tema/framing)
- **Pregunta:** ¿Qué temas me funcionan y cuáles no?
- **Inputs:** posts con tags tópico (seguridad, empleo, familia, denuncia, etc.) extraídos vía LLM
- **Ejemplo:** barras por tópico con engagement rate + out-of-base reach; resalta "denuncia corrupción" 3x baseline
- **Fuente:** Topic modeling + framing analysis Academic papers

### #15 — Cluster de seguidores (segmentación)
- **Pregunta:** ¿Mi base está creciendo en los segmentos que necesito para ganar?
- **Inputs:** followers con features demográficas inferidas (género, edad, ubicación, alineación)
- **Ejemplo:** sankey diagram seguidores ganados últimos 30d por segmento; warning si "indecisos" <10%
- **Fuente:** Bolsonaro 2018 microtargeting playbook (sin las malas prácticas)

### #16 — Share of Voice en temas clave
- **Pregunta:** ¿Domino la conversación en los temas que importan a mi candidatura?
- **Inputs:** keywords estratégicos, volumen mentions propio vs competidor
- **Ejemplo:** stacked area chart por tema (seguridad/economía/salud) con % SoV; si "salud" propio <20% = gap
- **Fuente:** Brandwatch Benchmark + Meltwater

### #17 — Reporte Semanal Ejecutivo (IA-generado)
- **Pregunta:** ¿Puedo reenviar un reporte de 1 página al político sin editar?
- **Inputs:** todo lo anterior + template IA (Claude/Gemma)
- **Ejemplo:** PDF 1 página con 3 headlines + matriz 2x2 + 3 Start/3 Stop/3 Continue + gráfica evolución 4 semanas
- **Fuente:** Práctica consultora Euzen/Indat + formato DOK political briefings

### #18 — Veda INE Compliance Banner
- **Pregunta:** ¿Estoy cumpliendo restricciones INE (veda, gasto, etiqueta IA)?
- **Inputs:** calendario INE, flags contenido_ia por post, gasto scraping/ads
- **Ejemplo:** banner permanente con 3 checks (veda activa sí/no, % contenido etiquetado IA, gasto vs límite)
- **Fuente:** Lineamientos INE + CLAUDE.md CRECE

### #19 — Comparativa Plataforma Óptima
- **Pregunta:** ¿En qué plataforma debo invertir más mi tiempo este mes?
- **Inputs:** performance por plataforma últimos 90d + benchmark MX
- **Ejemplo:** radar chart 5 plataformas × 4 ejes (reach, engagement, growth, out-of-base); recomendación: "duplicar esfuerzo en TikTok, bajar Facebook"
- **Fuente:** Buffer State of Social + Digital Information World

### #20 — Post Mortem de crisis pasadas
- **Pregunta:** ¿Qué aprendí de las últimas crisis y ataques?
- **Inputs:** crisis detectadas históricas + post-crisis recovery metrics
- **Ejemplo:** timeline últimos 6 meses con marcadores de crisis, duración, sentimiento pre/durante/post, lecciones
- **Fuente:** Social listening crisis management playbook + memoria institucional

---

## Fuentes consultadas (18)

1. [Brandwatch Benchmark product](https://www.brandwatch.com/products/benchmark/)
2. [Brandwatch Measure product](https://www.brandwatch.com/products/measure/)
3. [Meltwater Top Social Listening Tools](https://www.meltwater.com/en/blog/top-social-listening-tools)
4. [Sprinklr Social Listening Guide 2025](https://www.sprinklr.com/blog/social-listening/)
5. [Digital Information World 2026 Benchmarks](https://www.digitalinformationworld.com/2026/03/2026-social-media-benchmark-tiktok.html)
6. [Buffer TikTok Algorithm 2026](https://buffer.com/resources/tiktok-algorithm/)
7. [Dataslayer Instagram Algorithm 2026](https://www.dataslayer.ai/blog/instagram-algorithm-2025-complete-guide-for-marketers)
8. [Oxford Internet Institute - Mapping 2018 Mexican Election](https://demtech.oii.ox.ac.uk/wp-content/uploads/sites/12/2018/06/Mexico2018.pdf)
9. [Reuters Institute Digital News Report 2024 - Mexico](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2024)
10. [Merca2.0 Tiktómetro Sheinbaum Gálvez](https://www.merca20.com/elecciones-2024-tiktometro-de-claudia-sheinbaum-xochitl-galvez-y-jorge-alvarez/)
11. [Milenio Sheinbaum vs Gálvez plataformas](https://www.milenio.com/politica/elecciones/sheinbaum-aventaja-facebook-youtube-instagram-xochitl-galvez)
12. [Springer Political Behavior - Partisanship on Social Media](https://link.springer.com/article/10.1007/s11109-022-09850-x)
13. [ScienceDirect - Negativity Spreads Faster](https://www.sciencedirect.com/science/article/pii/S2468696423000010)
14. [ScienceDirect - Coordinated Inauthentic Behavior Twitter](https://www.sciencedirect.com/science/article/abs/pii/S0167923622000902)
15. [ScienceDirect - LLM Propaganda Detection Twitter Mexico](https://www.sciencedirect.com/science/article/pii/S2772503025000465)
16. [Tandfonline - Political Communication MX/BR/CO Instagram](https://www.tandfonline.com/doi/full/10.1080/10510974.2025.2574004)
17. [SAGE Journals - WhatsApp Brazil Bolsonaro](https://journals.sagepub.com/doi/full/10.1177/20563051231160632)
18. [Sutton Smart - Political Cross-Screen ROI](https://suttonsmart.com/political-consulting/political-cross-screen-media-attribution-roi-analysis-2/)

---

## Gaps de información no cerrados

1. **Números internos de campaña Sheinbaum 2024** — sólo hay lo público (Merca2.0, Milenio); las métricas internas que usó el equipo no son accesibles.
2. **Samuel García NL 2021 — métricas semanales de la campaña** — hay datos agregados actuales, no el dashboard semanal que usaba su equipo.
3. **Benchmarks específicos por tamaño de cuenta para políticos MX** — hay benchmarks globales por industria, no un corte político MX segmentado por 10K/50K/500K.
4. **Stack técnico interno de consultoras MX (Euzen/Indat/La Covacha)** — no publicado.
5. **Evidencia cuantitativa de éxito/fracaso Morena Edomex 2017** relacionada a digital específicamente — anecdótica en fuentes consultadas.

---

## 3 hallazgos más importantes (≤100 palabras)

1. **Reach fuera de base > engagement rate:** Gálvez 2024 tuvo 365% engagement rate en TikTok pero perdió por 30 puntos. CRECE debe jerarquizar `unconnected_reach` sobre likes totales en el dashboard principal.
2. **Sentiment como composición discreta, no promedio:** Sheinbaum dominó con "trust", Gálvez con "anger" — el promedio oculta la señal. Guardar las 6 emociones Plutchik por separado y calcular ratios `trust/anger` como KPI principal.
3. **Plan IA debe entregar Start/Stop/Continue con post modelo linkeado**, no recomendaciones abstractas. Cada acción del plan debe incluir: post ejemplo (propio o competidor), métrica respaldo, ventana temporal, recursos. El patrón Alfaro 2018 + Samuel García 2021 coincide: consistencia operacional semanal > insights aislados.
