# Diagnóstico Estratégico — Plan Consolidación Digital Políticos Mexicanos

**Fuente:** Perplexity (pegado por CEO, 2026-04-19)

---

El siguiente documento sistematiza, a partir de investigación y benchmarks latinoamericanos/estadounidenses, qué debería contener un diagnóstico + plan de consolidación digital útil para un político profesional mexicano (diputado, secretario, coordinador, etc.). Tiene como base datos de scrapers (posts, comentarios, engagement, sentimiento, tiempo y geografía) y busca cerrar el gap entre métricas "bonitas" y decisiones accionables: qué tipo de post, tono, formato y ritmo de publicación debe cambiar mañana.

Cada sección está diseñada para que CRECE v2 pueda traducirla directamente a dashboards, reportes y alertas de IA.

***

## 1. CASE STUDIES: Plataformas de social media analytics para políticos

### 1.1 Qué reportes entregan Brandwatch, Meltwater, Sprinklr, Talkwalker a políticos

Plataformas de escucha digital como **Brandwatch**, **Meltwater**, **Sprinklr** y **Talkwalker** no tienen "pacientes políticos" visibles al público, pero sí hay insight de qué reportan y cómo se usan en campañas políticas.[1][2][3][4]

- **Brandwatch** entrega:
  - **Share of Voice (SOV)**: porcentaje de mención del político frente a sus competidores en cada tema (economía, seguridad, educación, etc.).[2][5]
  - **Sentiment score agregado**: no solo "positivo/negativo" sino evolución temporal y por tema (ej. "subió el enojo en seguridad en X semana").[5][2]
  - **Top influencers y cuentas amplificadoras**: qué actores no‑oficiales (youtubers, periodistas, tuiteros) mueven más la conversación sobre el político.[6][5]
  - **KPIs empresariales adaptados**: alcance, engagement rate, crecimiento de seguidores, retorno de periodo de campaña (post‑campaña vs. previa).[7][1]

- **Meltwater**: monitoreo cruzando redes sociales, medios tradicionales y blogs, con filtros por tema, canal, idioma y geografía.[3] Reportes de "medición cualitativa": qué temas se amarran internamente de verdad (no solo tendencias superficiales).[3]

- **Talkwalker**: enfoque en reportes de campaña: "impacto de la campaña", "tráfico generado", "engagement rate", "conversiones" (si se miden a través de formularios o landing pages).[4] Comparaciones benchmark vs. competidores.[4]

**KPIs tipo dashboard (extrapolados a políticos mexicanos):**

| KPI principal | Qué mide |
|---|---|
| Share of Voice político | % de veces que se menciona al político frente a competidores en temas clave |
| Sentiment score promedio | Tendencia de tono general — "mejorando o empeorando" |
| Engagement rate por post | Efectividad real de cada tipo de post en generar interacción |
| Tasa de crecimiento de seguidores | Si un tipo de contenido genera pujas de seguidores |
| Impresiones/alcance orgánico | Potencial de llegar a no‑seguidores sin anuncios |

### Takeaways L1
- Mini‑dashboard "político‑competitivo" con SOV frente a 2–3 adversarios
- Sentiment por tema político (seguridad, educación, impuestos), no promedio
- Ranking automático de Amplificadores (top 10 cuentas influyentes)
- Lenguaje de campaña mexicana: "momentos de crisis", "mensajes que prenden"

***

## 2. MÉTRICAS NORMALIZADAS VS ABSOLUTAS

### 2.1 Métrica que correlaciona con crecimiento real

- **Engagement rate por alcance** > por seguidores > absoluto
- Fórmula: `ER = Interacciones / Alcance × 100`
- Mejor mide efectividad real porque descuenta tamaño de audiencia

### 2.2 Breakout Score — viralidad a no‑seguidores

```
BO = (Alcance - Seguidores) / Seguidores × 100
```
Si alcance > 3× seguidores → post está "rompiendo" hacia fuera.

### 2.3 Growth attribution por post — Follow‑window method

- Seguidores a `t-12h`, `t+24h`, `t+48h`, `t+72h`
- `Growth atribuido ≈ (Seguidores_t+24 − Seguidores_t-12) − Baseline`
- Requiere baseline de crecimiento diario

### 2.4 Engagement auténtico vs coordinado
- **Concentración temporal**: >60% comments en primeros 10 min = sospechoso
- **Patrones lenguaje**: repeticiones frase exacta, emojis/hashtags idénticos
- **Distribución users**: >80% likes de cuentas <100 seguidores = bot probable
- **Indicador de coordinación**: >50% comments 1ª hora + >70% users <100 followers → alerta

### 2.5 Benchmarks México
- Facebook: 0.5–1% ER (bueno para marcas grandes)
- X: 0.3–0.7%
- Instagram: 1.1–2.5% orgánico
- Influencers MX 10k–500k: 1.0–1.8%
- Marcas MX: 0.2–0.5%
- **Target político profesional:** ER por alcance ≥ 1% en X/IG/TikTok

### Takeaways L2
- Implementar ER por alcance como métrica principal con benchmarks por red + tamaño
- Breakout Score automático
- Follow‑window service para growth attribution por post
- Índice de sospecha de coordinación

***

## 3. CONTENIDO CONTROVERSIAL VS ALTA ACEPTACIÓN

### 3.1 Dimensiones de "controversial"
- **Polarización alta:** ratio aprobación/rechazo cercano 1:1
- **Intensidad emocional alta:** sentimiento fuerte (±), no neutro
- **Concentración geográfica:** si polarización se concentra regionalmente
- **Temporalidad:** pico en < 24h = "snap controversy"

### 3.2 Efecto controversia en consolidación
- Refuerza base fiel (más engagement entre simpatizantes)
- Genera enemigos activos (más voz negativa)
- **No hay evidencia** que controversia por sí sola asegure victoria
- Controversia bien gestionada = posicionamiento. Mal gestionada = mortífera.

### 3.3 Alta aceptación REAL vs "superficial likes"
- Narrativas de **solución**: propuestas concretas, no solo crítica
- Imágenes/emociones positivas: esperanza, logros reales, cifras verificables
- MX: contenido de **gestión** (informes obra, resultados programas, cifras) → + positivo, − negativo

### 3.4 Detectar aceptación fuera de base
- **Indicador de Expansividad:** % interacciones positivas desde cuentas NO simpatizantes
- Si un post genera comentarios positivos de cuentas que no siguen a otros políticos de la coalición → señal de expansión

### Takeaways L3
- Índice de polarización por post (ratio positivo/negativo)
- Indicador "controversia útil vs dañina"
- Rank posts alta aceptación real
- Indicador de Expansividad (outside base)

***

## 4. DIAGNÓSTICO + PLAN IA — MEJORES PRÁCTICAS

### 4.1 Estructura accionable
- **Start/Stop/Continue**: qué empezar, qué detener, qué continuar
- **Matriz 2x2**: contenido (exitoso/fallido) × engagement (alto/bajo)
- **Alertas por tema**: si sentimiento o SOV cambia bruscamente

### 4.2 Campañas exitosas MX
- Enfoque en contenido orgánico de gestión (no solo anuncios)
- Narrativa consistente en redes

### 4.3 Formato preferido por políticos
- Reportes semanales escritos con resumen ejecutivo
- Dashboards tiempo real con alertas
- Reuniones estratégicas periódicas

### Takeaways L4
- Reporte semanal Start/Stop/Continue automatizado
- Dashboards tiempo real con alertas
- Reuniones estratégicas mensuales con reportes personalizados

***

## 5. CASOS DE FRACASO

### 5.1 Reportes que fracasaron
- **Cambridge Analytica**: datos sin límites, criticada por falta transparencia/ética
- **Verified MX**: no generó valor real

### 5.2 Errores típicos
- Vanity metrics (likes, seguidores sin contexto)
- Correlación confundida con causalidad

***

## Fuentes (Perplexity)

[1] Brandwatch — KPIs metricas
[2] Brandwatch plataforma monitoreo
[3] Meltwater GetApp México
[4] Talkwalker reporte redes sociales
[5] Martech Challenges Brandwatch
[6] Herramientas análisis competencia
[7] Brandwatch KPI guide
[8] Estrategias campaña online partidos (UP revistas)
[9] Web Scraping análisis político (CIC‑IPN)
[10] Marketing político digital y reputación en México (Luz)
[11] Métricas y KPIs Redes Sociales 2026
[12] Engagement rate fórmulas y benchmarks (dks.digital)
[13] INE — Conectados pero desinformados (PDF)
[14] Cepymenews engagement 2026
[15] Marketing4ecommerce MX — influencers
[16] Scielo — Brechas digitales México
[17] Rendición de Cuentas — partidos políticos datos
[18–35] ver links completos en respuesta original

_Nota: el output terminó cortado en 5.2 "Correlación confundida" — el documento original de Perplexity se truncó._
