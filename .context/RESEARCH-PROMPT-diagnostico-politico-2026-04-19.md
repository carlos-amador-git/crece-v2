# Research prompt — Diagnóstico Estratégico Plan Consolidación Digital

**Fecha:** 2026-04-19
**Autor:** Joy (CRECE v2)
**Disparado contra:** `sc:research` + `gemini -p` (+ opcional Gemini Deep Research externo del CEO)

---

CONTEXTO
========
Estoy construyendo CRECE v2 — una plataforma de inteligencia electoral y social
para Movimiento Ciudadano CDMX y otros actores políticos mexicanos. Mi cliente
es un dirigente político (diputado, secretario, coordinador) que quiere
CONSOLIDAR su presencia digital (no solo medirla). Tenemos scrapers corriendo
contra X, Instagram, Facebook, TikTok y YouTube que traen posts + comments +
métricas de engagement + sentimiento clasificado.

El gap actual: tengo infraestructura de NLP que clasifica tono/polaridad de
comments, pero el PRODUCTO que ve el político es genérico — "IPD 4.5/10",
"sentimiento promedio -0.3" — datos que no le sirven para decidir qué hacer
mañana. Necesito diseñar el DIAGNÓSTICO + PLAN DE CONSOLIDACIÓN que realmente
genere decisiones accionables para un político mexicano.

OBJETIVO DE LA INVESTIGACIÓN
============================
Responder: ¿qué elementos, métricas, narrativas y recomendaciones debe
contener un diagnóstico + plan de consolidación digital para un político
profesional que quiere ganar capital político online?

5 LÍNEAS DE INDAGACIÓN
======================

1. CASE STUDIES — Plataformas de social media analytics para políticos
   - ¿Qué reportes entregan Brandwatch, Meltwater, Sprinklr, Talkwalker a
     políticos en campaña en USA, UK, Brasil, México?
   - ¿Qué productos similares existen en México (Enkoll, Massive Caller,
     Oraculus — su línea analytics no encuesta)?
   - ¿Cuáles son los 3-5 KPIs que estas plataformas destacan como "dashboard
     principal" para un político?
   - Ejemplos específicos: screenshots de reportes de Barack Obama 2012,
     AMLO 2018, Bolsonaro 2018, Sheinbaum 2024 — qué métricas usaron internamente

2. MÉTRICAS NORMALIZADAS VS ABSOLUTAS
   - "Likes absolutos" vs "engagement rate (likes/seguidores)" vs "organic
     reach" — ¿cuál correlaciona mejor con crecimiento real de base política?
   - Cuál es el "gold standard" para detectar un post viral que alcanzó
     audiencia NO-SEGUIDORES (breakout)
   - Cómo medir "growth attribution por post": si publico hoy, cuántos
     seguidores gané en las 24/48/72h siguientes que son atribuibles a ese post
     específico (no al contexto mediático general)
   - Cómo distinguir engagement AUTÉNTICO vs bot/coordinado (ej.: flame wars,
     comentarios coordinados por Morena/PRIAN/etc.)
   - Benchmarks: ¿qué engagement rate normalizado es "bueno" en México para
     un político con 10K/50K/500K seguidores?

3. CONTENIDO CONTROVERSIAL VS ALTA ACEPTACIÓN
   - ¿Qué dimensiones definen un post como "controversial" más allá del
     sentimiento promedio? (ratio aprobación/rechazo, diversidad del discurso,
     polarización geográfica, concentración temporal)
   - ¿Los posts controversiales son buenos o malos para consolidación?
     — Investigación académica o reportes que lo respondan con datos
   - Qué tipo de contenido genera "high approval" real vs "superficial likes":
     ejemplos en política mexicana
   - Cómo detectar un post que "tuvo aceptación en el exterior de su base"
     (followers de oposición que lo validaron) — este es un indicador fuerte
     de expansión de capital político

4. DIAGNÓSTICO + PLAN IA — MEJORES PRÁCTICAS
   - ¿Qué estructura de reporte genera decisiones accionables para un
     político? (ej.: framework "Start/Stop/Continue", semáforo, matriz 2x2
     contenido/engagement)
   - Ejemplos de planes de consolidación digital exitosos para políticos
     mexicanos (MC-Alfaro Jalisco 2018-21, Samuel García NL 2021-22, etc.)
   - Qué recomendaciones concretas ("sube más reels", "responde a críticos
     con datos") vs vagas ("mejora tu narrativa") entregan los sistemas
     de alto calibre
   - Cómo se presenta el diagnóstico: dashboard tiempo real vs reporte
     semanal escrito vs reunión estratégica — qué prefieren los políticos
     y cuál da mejores resultados

5. CASOS DE FRACASO — QUÉ NO HACER
   - ¿Qué reportes/plataformas de social media analytics para políticos
     fracasaron y por qué? (ej.: Cambridge Analytica, Verified MX, etc.)
   - Errores típicos: vanity metrics, dashboards sin acción, reportes que
     confunden correlación con causalidad, métricas de plataforma sin
     contexto político
   - Casos donde el "plan de consolidación digital" salió mal: el político
     se obsesionó con ratings digitales y perdió elección (Morena Edomex
     2017, PAN 2024, etc.)

FORMATO DE RESPUESTA DESEADO
============================
- Investigación estructurada por las 5 líneas
- Mínimo 8-12 fuentes verificables (links, papers, reportes de consultoras,
  artículos de académicos políticos latinoamericanos)
- Cada sección termina con 3-5 "takeaways accionables" para mi producto
- Sección final: "Inventario de elementos candidatos" — lista de 15-30
  bloques potenciales que podría tener mi diagnóstico (cards, métricas,
  recomendaciones, charts, alertas), cada uno con:
   * Nombre corto del elemento
   * Qué pregunta responde para el político
   * Inputs necesarios del backend (¿ya los tengo? ¿faltan?)
   * Ejemplo concreto de cómo se vería
   * Fuente/precedente de dónde viene la idea

CONSTRAINT
==========
- Foco: México y Latinoamérica (EEUU sólo para benchmarks de estado del arte)
- Contexto: políticos profesionales (diputados, secretarios, gobernadores) —
  NO candidatos amateur ni influencers políticos
- Prohibido: vaguedades tipo "usar storytelling". Cada recomendación debe
  poder implementarse con data de scrapers (posts, comments, engagement,
  sentimiento, tiempo, geografía).

DELIVERABLE
===========
Un documento MD de 8-12 páginas. Título: "Diagnóstico Estratégico —
Elementos del Plan de Consolidación Digital para Políticos Mexicanos".
