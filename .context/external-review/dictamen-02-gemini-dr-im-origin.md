# Dictamen 02 — Origen de la tabla Gemini DR en benchmarks de Influencer Marketing comerciales

**Fecha:** 2026-04-19
**Autor de la investigación:** agente externo (búsqueda en GitHub, Kaggle, Google Dataset Search, OSF, Zenodo, Harvard Dataverse, arXiv, SSRN + reportes públicos 2022-2026)
**Motivo de archivo:** input complementario para la decisión D-19 en CRECE_PRODUCT_MASTER.md §6
**Conclusión estructural:** la tabla Gemini DR no es calibración política mexicana sino adopción casi textual de benchmarks globales del Influencer Marketing comercial

---

## Hallazgo crítico principal

Tras agotar el tiempo de búsqueda en los repositorios indicados y reportes públicos de 2022 a 2026, la evidencia muestra un gap metodológico importante: la tabla generada originalmente por Gemini Deep Research no refleja el comportamiento de políticos mexicanos, sino que es una adopción casi textual de los benchmarks globales genéricos para la industria del Influencer Marketing (publicados típicamente por agencias como Later, Influencer Marketing Hub y Socialinsider para creadores de contenido de estilo de vida, retail y consumo).

## Sección 1: Tabla consolidada de hallazgos empíricos

No existen repositorios públicos ni datasets de acceso abierto (como en Kaggle o GitHub) que ofrezcan una muestra cruda y desagregada en estas cinco bandas exactas exclusivamente para políticos mexicanos de 2022 a 2026. Los datos reales disponibles se agrupan por la categoría general "Gobierno" o provienen de estudios de caso aislados en campañas latinoamericanas.

| Fuente | Año | Tamaño de muestra | Plataforma | Método de cálculo de ER | Rango observado (empírico) |
|---|---|---|---|---|---|
| Rival IQ (Social Media Industry Benchmark Report) | 2024 / 2026 | +2,500 marcas/cuentas globales (incluye sector Gobierno) | FB, IG, X, TikTok, LinkedIn | Total interacciones / Total seguidores × 100 | Sector Gobierno general: TikTok ~2.3%, LinkedIn ~2.0%, IG ~0.6-1.5%, FB ~0.6% |
| Influencer Marketing Hub / Later (Influencer Benchmarks) | 2024 / 2025 | Cuentas globales multi-industria | IG, TikTok, FB, YT | Interacciones / Seguidores (o Impresiones) × 100 | Nano 4.0-10.0%, Micro 2.0-5.0% (IG 3.86%), Mid ~1.5-3.0%, Macro 1.0-2.0%, Mega 0.7-1.2% |
| Revista Latina de Comunicación Social (Estudio académico LATAM) | 2021 / 2024 | Perfiles de candidatos presidenciales LATAM | TikTok | Interacciones totales / Seguidores × 100 | Casos atípicos alta movilización en campaña (ej. Petro) superaron 9.0% en cuentas Macro/Mega |
| Repositorios académicos (Dialnet, arXiv) | 2022-2026 | Estudios cualitativos o métricas agregadas de desempeño | X, FB | Interacciones directas | Gap de datos: no desagregan el ER por bandas de seguidores para la clase política mexicana en formato tabla |

## Sección 2: Veredicto por estrato de seguidores

La evaluación de la tabla provisoria arroja que las bandas de engagement están infladas para la comunicación política ordinaria (fuera de temporalidad electoral) y sufren del sesgo de "creador de contenido comercial".

**Nano (1K–10K / ER 6.0–10.0%):** Sin evidencia suficiente.
Gap sin cubrir para políticos mexicanos. La banda del 6-10% está confirmada en reportes de Influencer Marketing Hub (2024/2026) solo para nichos comerciales muy cerrados o en TikTok, pero es irreal aplicarla como estándar para un político local mexicano en Facebook o X.

**Micro (10K–50K / ER 3.5–6.0%):** Parcialmente confirmada (desviación severa a la baja).
Los reportes de consultoras cruzan el estrato Micro en ~3.86% a nivel global comercial. Sin embargo, en el rubro gubernamental estricto de Rival IQ, el promedio absoluto de las cuentas es drásticamente menor (usualmente no supera el 2.5% fuera de TikTok).

**Mid-Tier (50K–100K / ER 2.0–4.0%):** Sin evidencia empírica suficiente.
No existen datasets abiertos que aíslen a alcaldes o diputados mexicanos en este rango de seguidores para validar un 4% de engagement sostenido en plataformas como Twitter/X o Facebook.

**Macro (100K–500K / ER 1.5–2.5%):** Parcialmente confirmada.
Esta banda se alinea más con la realidad del sector público. El Rival IQ Benchmark 2024/2026 ubica al sector "Gobierno" oscilando cerca del 1.5% al 2.0% en plataformas de alto rendimiento (LinkedIn y TikTok).

**Mega (500K+ / ER 1.0–2.0%):** Confirmada por fuentes convergentes.
Es la banda más realista. Al tener una base masiva de seguidores (gobernadores, secretarios de estado, figuras presidenciales), el algoritmo y el alcance orgánico deprimen la tasa a rangos de 0.5% a 1.5%.

## Sección 3: Recomendaciones de ajuste

Si el objetivo es auditar cuentas políticas en México con rigor analítico, se debe desechar la tabla única cross-platform. Mantener una expectativa de 6.0% para un perfil Nano en Facebook o Twitter penalizará injustamente la cuenta auditada, ya que esos números solo son posibles en TikTok.

### Ajuste 1: Segmentación obligatoria por plataforma (no por seguidor universal)

Justificación: el reporte de Socialinsider y Rival IQ demuestra que el ER depende mucho más de la plataforma que del tamaño de la audiencia en el sector institucional.

Recomendación: construir tablas independientes. Una para TikTok/Instagram Reels (donde el contenido político sí alcanza promedios de 2.0%-4.0%) y otra para X/Facebook (donde el engagement orgánico político ronda el 0.5%-1.5%).

### Ajuste 2: Corrección del benchmark a la realidad gubernamental/política

Justificación: los políticos sufren de altos niveles de pasividad en sus audiencias (seguidores informativos, no interactivos).

Recomendación: si se necesita mantener una tabla agnóstica de la plataforma (por simplicidad), reducir drásticamente las expectativas para alinearlas con la categoría "Gobierno" de firmas como Rival IQ:

- Nano: bajar a 3.0% – 5.0%
- Micro: bajar a 2.0% – 3.5%
- Mid-Tier: bajar a 1.5% – 2.0%
- Macro: bajar a 1.0% – 1.5%
- Mega: bajar a 0.5% – 1.0%

### Ajuste 3: Factor "Temporalidad Electoral"

Justificación: la literatura académica (estudio de TikTok en campañas LATAM) muestra que el engagement explota en ciclos electorales.

Recomendación: crear un modificador o nota metodológica donde se acepte que durante los 90 días previos a un comicio (ej. Elecciones México 2024), las tasas esperadas se pueden multiplicar hasta por 2.5x debido a la polarización orgánica y pauta de contraste.

## Estado del dictamen

Investigación completada. Archivo consumido por D-19 del MASTER como evidencia del origen Influencer Marketing comercial de la tabla original Gemini DR. Informa la decisión de reemplazo estructural por matriz 5×5 estrato × plataforma con factor temporalidad electoral.
