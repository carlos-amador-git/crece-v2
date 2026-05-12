# T0.2 — Validación Benchmarks ER por Estrato vs Data Real

## Metadatos de reproducibilidad

| Campo | Valor |
|---|---|
| **Sprint** | S0 · Tarea T0.2 |
| **Fecha** | 2026-04-19 |
| **Ejecutor** | Claude Opus 4.7 (1M context) |
| **Modelo/Script** | `python3` inline — agregación estadística sobre JSONL (sin LLM) |
| **Temperature** | N/A (sin LLM) |
| **Seed** | N/A (agregación determinista) |
| **Input primario** | `/Users/marxchavez/Projects/crece-v2/backend/benchmarks/scraping/results/2026-04-19/nlp_layer2_gemma_out.jsonl` (1,152 comments) |
| **Input secundario** | `/Users/marxchavez/Projects/crece-v2/backend/research/2026-04-19/SINTESIS-4-FUENTES.md` §1.3 |
| **Referencia estratos** | Gemini DR §2.2 — Nano/Micro/Mid-Tier/Macro/Mega |
| **Outputs** | `backend/research/2026-04-19/settings_strata.json` + este `.md` |
| **Rango fechas clasificación** | 2026-04-18 17:44 → 2026-04-18 20:22 |
| **Perfiles de prueba esperados** | 8 dirigentes × 5 plataformas = 40 celdas |

---

## 1. Tabla Gemini DR de referencia

| Estrato | Seguidores | ER esperado | Perfil |
|---|---|---|---|
| **Nano** | 1K–10K | 6.0–10.0% | Regidores, candidatos locales |
| **Micro** | 10K–50K | 3.5–6.0% | Diputados locales, alcaldes emergentes |
| **Mid-Tier** | 50K–100K | 2.0–4.0% | Diputados federales, alcaldes metropolitanos |
| **Macro** | 100K–500K | 1.5–2.5% | Senadores, gobernadores |
| **Mega** | 500K+ | 1.0–2.0% | Candidatos presidenciales, ejecutivo |

---

## 2. Data observable en el dataset

El archivo `nlp_layer2_gemma_out.jsonl` contiene **1,152 comments clasificados por Gemma 3:12b** — NO incluye `likes`, `views`, `followers_count`, `post_engagement_total`, ni `posts_metrics`. Cobertura parcial: solo X (Twitter) + Instagram.

### 2.1 Métricas derivables

| Métrica derivable | Disponible | Uso |
|---|---|---|
| Comments totales 90d | Sí | Proxy débil de volumen actividad |
| Authors únicos | Sí | Diversidad audiencia (bajo → CIB) |
| Comments/post estimado | Parcial (id prefix) | Proxy density |
| ER real (engagement/followers o /reach) | **NO** | Sin likes ni followers |
| Breakout Scale | NO | Sin views/reach |

### 2.2 Tabla observada por dirigente × plataforma

| Dirigente | Plataforma | Comments | Unique Authors | Diversidad % | Posts ~est |
|---|---|---:|---:|---:|---:|
| Alejandro Piña | X | 74 | 4 | 5.4% | 14 |
| Alejandro Piña | Instagram | 54 | 39 | 72.2% | 18 |
| Rafael Solano | X | 2 | 1 | 50.0% | 2 |
| Rafael Solano | Instagram | 6 | 5 | 83.3% | 5 |
| Saymi Pineda | X | 34 | 2 | 5.9% | 6 |
| Saymi Pineda | Instagram | 18 | 16 | 88.9% | 9 |
| Yessenia Nolasco | X | 96 | 4 | 4.2% | 13 |
| Yessenia Nolasco | Instagram | 18 | 10 | 55.6% | 6 |
| Gaby Jiménez | X | 189 | 158 | 83.6% | 179 |
| Gaby Jiménez | Instagram | 178 | 114 | 64.0% | 29 |
| César Cravioto | X | 29 | 22 | 75.9% | 29 |
| César Cravioto | Instagram | 15 | 11 | 73.3% | 8 |
| Laura Ballesteros | X | 83 | 67 | 80.7% | 83 |
| Laura Ballesteros | Instagram | 141 | 111 | 78.7% | 29 |
| Jorge Álvarez Máynez | Instagram | 168 | 160 | 95.2% | 26 |
| Jorge Álvarez Máynez | X | — (no capturado) | — | — | — |

**Cobertura real:** 15 celdas con data / 40 celdas esperadas (8 × 5) = **37.5%** de la matriz.

Plataformas totalmente ausentes: Facebook, TikTok, YouTube. Máynez X tampoco está en este corrida.

---

## 3. Comparación Estrato Asignado vs ER Esperado vs ER Observable

| Dirigente | Estrato asignado | Confianza | ER esperado (Gemini DR) | ER observable | Delta numérico | Status |
|---|---|---|---|---|---|---|
| Alejandro Piña | Nano | HIGH | 6–10% | **INCOMPUTABLE** | n/a | AMBIGUO |
| Rafael Solano | Nano | HIGH | 6–10% | **INCOMPUTABLE** | n/a | AMBIGUO |
| Saymi Pineda | Nano | MEDIUM | 6–10% | **INCOMPUTABLE** | n/a | AMBIGUO |
| Yessenia Nolasco | Nano | MEDIUM | 6–10% | **INCOMPUTABLE** | n/a | AMBIGUO |
| Gaby Jiménez | Micro | MEDIUM | 3.5–6% | **INCOMPUTABLE** | n/a | AMBIGUO |
| César Cravioto | Micro | MEDIUM | 3.5–6% | **INCOMPUTABLE** | n/a | AMBIGUO |
| Laura Ballesteros | Micro | MEDIUM | 3.5–6% | **INCOMPUTABLE** | n/a | AMBIGUO |
| Jorge Á. Máynez | Macro | HIGH | 1.5–2.5% | **INCOMPUTABLE** | n/a | AMBIGUO |

**Ningún delta numérico puede calcularse.** El criterio binario del MASTER (>30% delta en ≥3 dirigentes → recalibrar) **no aplica** porque requiere un número observable, y el dataset entregado no contiene los inputs para ER (likes, views, followers_count, o reach).

---

## 4. Gaps honestos — qué NO se puede calcular con este dataset

1. **ER formal** = (likes + comments + shares) / followers — falta likes y followers.
2. **Alternativa reach-based** = (likes + comments) / views — falta views.
3. **Snapshot diario followers** — no existe aún (gap documentado en SINTESIS §3).
4. **Comments/follower ratio aislado** — numerador OK, denominador ausente.
5. **Comparación cross-platform** — cobertura 37.5% (15/40 celdas). FB/TT/YT totalmente ausentes.
6. **Separación orgánico vs CIB** — diversidad baja (<10%) observada en Piña X, Pineda X, Nolasco X sugiere CIB; pero estrato es señal independiente de CIB.
7. **Máynez X ausente** — el candidato con mayor seguidores del lote no tiene fila X en este benchmark.

### Señales CIB detectadas colateralmente (no objetivo T0.2, input para T0.3)

| Dirigente | Plataforma | Diversidad | Señal |
|---|---|---|---|
| Alejandro Piña | X | 5.4% | ALTA — 4 autores / 74 comments |
| Saymi Pineda | X | 5.9% | ALTA — 2 autores / 34 comments |
| Yessenia Nolasco | X | 4.2% | ALTA — 4 autores / 96 comments |

---

## 5. Veredicto del criterio binario MASTER

> "si delta >30% en ≥3 dirigentes → recalibrar rangos en JSON. Si <30% → adoptar tabla Gemini DR"

**Veredicto: AMBIGUO por falta de data ER real.**

Ni "recalibrar" ni "adoptar con evidencia" son aplicables porque delta ER es incomputable. Se toma **decisión operativa documentada**:

### Decisión: ADOPTAR TABLA GEMINI DR CONDICIONALMENTE + flag recalibración diferida

**Racional operativo:**
1. Sprint S1 T2 necesita `{dirigente_id: estrato}` para arrancar. Entregamos el mapping con confianza declarada (HIGH/MEDIUM) → NO bloqueamos S1.
2. Tabla Gemini DR es el mejor baseline académicamente fundamentado (Sprout, Rival IQ 2025, Emplifi 2025).
3. La validación empírica ER real queda **condicionada a Sprint S1 T3** (cron snapshot diario `followers_count` por plataforma) + **Sprint S2** (persistir `likes`, `views` en `social_posts`).
4. Ciclo de recalibración: al cumplirse 30 días de snapshots + persistencia de métricas → re-ejecutar este análisis con datos reales y decidir recalibración formal (criterio binario recuperable).

---

## 6. Estratos asignados finales (consumidos por `settings_strata.json`)

| dirigente_id | estrato | confidence |
|---|---|---|
| alejandro_pinha | Nano | HIGH |
| rafael_solano | Nano | HIGH |
| saymi_pineda | Nano | MEDIUM |
| yessenia_nolasco | Nano | MEDIUM |
| gabriela_jimenez | Micro | MEDIUM |
| cesar_cravioto | Micro | MEDIUM |
| laura_ballesteros | Micro | MEDIUM |
| jorge_alvarez_maynez | Macro | HIGH |

**Distribución:** 4 Nano · 3 Micro · 1 Macro · 0 Mid-Tier · 0 Mega

---

## 7. Checklist sprint acceptance

- [x] Mapping 8 dirigentes → estrato publicado en `settings_strata.json`
- [x] Comparación tabla actual vs esperada ejecutada (limitada por gaps)
- [x] Delta + decisión documentada (AMBIGUO + adopción condicional)
- [x] Gaps honestos listados
- [x] Metadatos reproducibilidad completos (modelo, paths, fecha, temperature=N/A)
- [ ] **Criterio binario <30% delta** → NO aplicable por falta de ER numérico → decisión escalada a Sprint S1 T3 (post snapshot diario followers)

---

## 8. Recomendaciones para Sprint S1

1. **T1 prioridad crítica:** migration añadir `followers_count` a `social_profile_snapshots` + cron daily (ya en plan).
2. **T1 nueva subtarea:** persistir `likes_count`, `views_count`, `shares_count` por post en `social_posts` (campo `views` ya está en scraper Apify, falta persistirlo — ver SINTESIS §3.4).
3. **T2 consumir** `settings_strata.json` tal cual — confidence MEDIUM es aceptable para baseline v1.
4. **Retrospectiva S1 día 30:** re-ejecutar T0.2 con data completa y validar formalmente el criterio binario MASTER.
5. **Próximo benchmark scraping:** incluir Máynez en X, y completar FB/TikTok/YouTube para alcanzar 40/40 cobertura.

---

**FIN DEL DOCUMENTO T0.2**
