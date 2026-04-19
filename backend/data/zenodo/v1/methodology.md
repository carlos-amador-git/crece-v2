# Metodología — Benchmarks ER políticos mexicanos (CRECE v2 · v1)

**Dataset:** `benchmarks_er_politicos_mx_v1`
**Versión:** 1.0 (preliminar · calibración abierta)
**Fecha de corte:** 2026-04-19
**Autor:** MD Consultoría SC · equipo CRECE v2
**Licencia:** CC BY 4.0 (permite uso comercial derivado con atribución)
**DOI:** TBD (asignable al publicar en Zenodo)

---

## §1 · Motivación — por qué un dataset propio MX

Los benchmarks de Engagement Rate (ER) disponibles públicamente para México son estructuralmente inadecuados para auditar perfiles políticos. Las tablas comerciales de referencia (Hootsuite, Rival IQ, Influencer Marketing Hub, Emplifi, Sprout Social, Later, Socialinsider) están construidas sobre universos de **Influencer Marketing global** — creadores de contenido de retail, estilo de vida y consumo masivo — no sobre actores del sistema político-gubernamental.

Dos dictámenes externos realizados para este proyecto (`.context/external-review/dictamen-01-gemini-dr-im-origin.md` y `dictamen-02-gemini-dr-im-origin.md`, 2026-04-19) convergen en tres hallazgos críticos:

1. **Origen IM commercial.** La tabla Gemini Deep Research 1×5 (Nano/Micro/Mid/Macro/Mega) que arrancó el diagnóstico del producto CRECE es una adopción casi textual de los rangos de Influencer Marketing Hub / Later / Socialinsider. No es calibración política mexicana.
2. **Gap estructural 1×5 vs 5×5.** El ER político depende más de la plataforma que del tamaño de la audiencia. TikTok > Instagram ≈ Facebook-gubernamental > X por factor 3-10×. Una tabla 1×5 induce falsos positivos en TikTok y falsos negativos en X / Facebook.
3. **Temporalidad electoral.** La literatura académica (estudio TikTok en campañas LATAM, Revista Latina de Comunicación Social 2024, análisis Sheinbaum/Gálvez 2024) muestra engagement × 2.0–2.5× en ventana 90d pre-comicio.

Se dispone de un dataset académico MX relevante como referencia — **Zenodo 10.5281/zenodo.7877001 "15M tweets MX 2021"** — que es follow-up alto valor / bajo esfuerzo para validación cruzada, pero no cubre multi-plataforma ni temporalidad electoral contemporánea.

Este dataset `benchmarks_er_politicos_mx_v1` es la **respuesta estructural de CRECE** a ese gap: un bundle reproducible propio, con DOI asignable, actualización periódica, y metodología pública que cualquier investigador puede replicar.

---

## §2 · Stack de captura de datos

El pipeline de scraping opera sobre 5 plataformas (X / Instagram / Facebook / TikTok / YouTube) con arquitectura de resiliencia de 3 capas:

**Capa 1 — Apify (primario comercial, free tier $5/mes)**
- `apify/instagram-profile-scraper` · `apify/facebook-pages-scraper` · `apidojo/tweet-scraper` · `apify/tiktok-scraper` · `streamers/youtube-scraper`
- Veredicto interno documentado en `~/.claude/projects/.../project_5redes_veredicto.md` (2026-04-18 · 2041 items capturados · $2.29 free tier).

**Capa 2 — Scrapling v2 (fallback open-source · Playwright stealth)**
- Fallback cuando Apify rate-limita o el perfil es privado. Caso confirmado: X timeline bloqueado por login-wall → `twscrape` con cookies burner autorizadas.
- Veredicto X en `~/.claude/projects/.../project_x_scrapers_veredicto.md` (2026-04-18 · 1067 items · $0.85).

**Capa 3 — Brightdata (validador / web-unblocker para spot-checks de integridad)**
- Se invoca solo para validar coherencia de contadores cuando Apify y Scrapling difieren > 5%. No es fuente primaria.

Los 3 stacks escriben al mismo schema interno (`SocialProfile` + `SocialPost` + `SocialProfileSnapshot` — `backend/app/models/social.py`) para reproducibilidad.

---

## §3 · Definición operativa de estrato político

Se adopta la taxonomía de **5 estratos por rango de followers** normalizada entre las 5 plataformas. El estrato se calcula contra el follower count promedio de los snapshots diarios de la plataforma **más poblada** del dirigente (conservador — evita inflar estrato por una plataforma secundaria).

| Estrato | Rango de followers (ventana media 90d) |
|---|---|
| **Nano** | < 10,000 |
| **Micro** | 10,000 – 50,000 |
| **Mid** | 50,001 – 250,000 |
| **Macro** | 250,001 – 1,000,000 |
| **Mega** | > 1,000,000 |

Estos cortes difieren del Influencer Marketing commercial (habitualmente Nano < 1K, Micro 1K-100K) y están calibrados para el universo político-gubernamental MX donde los perfiles < 10K son ya poco relevantes en términos de alcance orgánico.

---

## §4 · Cálculo de ER por plataforma

**Fórmula base:**

```
ER(post) = (likes + comments + shares) / followers_snapshot × 100
```

donde:
- `likes`, `comments`, `shares` son contadores del post al momento de captura (T+N donde N = días desde publicación en el pipeline).
- `followers_snapshot` es el valor de `social_profile_snapshots.followers_count` más cercano temporalmente al `published_at` del post (tolerancia ±24h).
- El resultado se expresa en porcentaje (0-100) con 2 decimales.

**Consideraciones específicas por plataforma:**

- **YouTube:** `shares` no siempre está disponible vía API pública; cuando no lo está se usa `(likes + comments) / subscribers × 100` y se marca el campo `shares_available=False` en metadata.
- **TikTok:** `views` se incluye en un campo secundario pero NO entra en la fórmula estándar (evita inflar ER por autoplay); se usa para cálculo de `Breakout Scale` en capa analítica separada.
- **Instagram Reels vs posts:** se agregan juntos en la celda Instagram del v1 preliminar; la v2 segregará Reels.

---

## §5 · Ventana de observación

**Default:** 90 días móviles contados hacia atrás desde la fecha de corte del bundle.

**Exclusión explícita — ventana pre-electoral:** se descartan los posts publicados dentro de los 90 días previos a un comicio aplicable al distrito del dirigente. Esto corresponde al modificador temporal **1.0** (base) definido en `CRECE_PRODUCT_MASTER.md §3.1 #01`. La rampa 1.5× / 2.5× pre-comicio se reporta en un dataset secundario futuro (v2).

**Calendario de comicios MX considerados:**
- Elección federal 2024 — ventana 2024-03-03 a 2024-06-02 (excluida)
- Elecciones locales 2025 CDMX / Oaxaca — ventanas por distrito excluidas por mapping `unidad_territorial.seccion_electoral` → fecha comicio.

Cuando el script de generación `scripts/generate_zenodo_bundle.py` corre sin calendario electoral disponible (v1 preliminar), reporta la ventana completa de 90d y marca la caveat `temporal_filter_applied=False` en `_calibration_log.json`.

---

## §6 · Criterio de validación estadística (🟢 VALIDATED)

Una celda de la matriz 5×5 se marca como **🟢 VALIDATED** cuando cumple las 3 condiciones simultáneamente:

1. `n_observaciones ≥ 30` — al menos 30 posts publicados por al menos 1 dirigente distinto dentro de la celda (estrato × plataforma), para cumplir el Teorema del Límite Central con margen de seguridad.
2. Intervalo de Confianza 95% calculable (bootstrap 10,000 iteraciones sobre los percentiles p25/p50/p75).
3. Diversidad de fuentes: al menos 2 dirigentes distintos contribuyen a la celda (evita que 1 dirigente outlier distorsione el benchmark).

Cuando `n < 30` la celda se reporta como **🟡 TBD** con `n_observaciones` explícito para trazabilidad. El v1 preliminar publicará con cualquier número de celdas 🟢 (incluso 0 / 25) y el CSV mantiene todas las 25 filas para homogeneidad estructural.

---

## §7 · Limitaciones conocidas

**Cobertura actual del piloto (v1 preliminar):**
- 8 dirigentes piloto: sesgo geográfico a CDMX + Oaxaca. El benchmark MX real requerirá expansión a ≥30 dirigentes de ≥10 estados antes de considerarse representativo nacional.
- 2 plataformas con captura confiable (Instagram, X). Facebook / TikTok / YouTube están **extrapoladas preliminarmente** desde los dictámenes externos hasta que el pipeline acumule ≥30d de snapshots en las 3 plataformas.

**Sesgos metodológicos documentados:**
- **Sesgo partidista.** El piloto es mayoritariamente Movimiento Ciudadano + perfiles independientes. La generalización a Morena / PAN / PRI / Verde requiere muestreo estratificado por partido en v2+.
- **Sesgo de supervivencia.** Solo se capturan perfiles públicos vivos al momento del scrape. Cuentas eliminadas, privadas o baneadas no entran en el universo.
- **Ventana corta.** 90d captura ciclos de 1 tema electoral pero no variabilidad estacional (verano vs fin de año, informes de gobierno, 15 de septiembre, etc.).

**Exclusiones explícitas:**
- Posts dentro de los 90d previos a cada comicio aplicable (reservados para análisis separado de temporalidad electoral).
- Posts con `is_political=False` en clasificación interna (contenido personal del dirigente que no aporta señal de comunicación política).
- Comentarios sobre los posts — este dataset mide **ER orgánico**, no sentiment ni polaridad (cubiertos en capa NLP separada del producto).

---

## §8 · Reproducibilidad

Para regenerar el CSV desde cero con el corpus interno actual:

```bash
cd /path/to/crece-v2
source backend/venv/bin/activate
python backend/scripts/generate_zenodo_bundle.py \
    --window-days 90 \
    --output backend/data/zenodo/v1/
```

El script es idempotente: sobrescribe `benchmarks_er_politicos_mx_v1.csv` y `_calibration_log.json` con metadata de la ejecución. El bundle publicable no incluye credenciales de base de datos ni PII de dirigentes — solo agregados por celda.

---

## §9 · Citación sugerida

```
MD Consultoría SC. (2026). Benchmarks ER políticos mexicanos —
CRECE v2 v1 [Data set]. Zenodo. DOI: TBD
```

**Dataset académico de referencia para validación cruzada:**
Santos Rodríguez, A., Pérez-Rosas, V. et al. (2023). *Mexican Political Tweets 2021 Dataset (15M tweets)*. Zenodo. DOI [10.5281/zenodo.7877001](https://doi.org/10.5281/zenodo.7877001)

---

**Contacto:** info@mdconsultoria-ti.org
**Código fuente:** https://github.com/MarxCha/crece-v2 (MIT — código generador) + este bundle (CC BY 4.0 — datos agregados).
