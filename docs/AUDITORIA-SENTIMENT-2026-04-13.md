# Auditoría Profunda de Sentiment Analysis — CRECE v2.0

**Fecha:** 2026-04-13
**Sesión:** Cleanup post whisper batch
**DB state:** 3,833 posts totales, 3,709 con sentimiento (pysentimiento)
**Solicitado por:** CEO — encontró anomalías considerables en el primer ejercicio

---

## Resumen ejecutivo

El pipeline **NLP técnicamente funciona** (pysentimiento clasifica correctamente el texto que recibe), pero el **uso agregado del sentiment a nivel dirigente es engañoso** por 6 problemas de diseño, no del modelo.

---

## Distribución actual por dirigente + plataforma

| Dirigente | Plataforma | Total | Avg sent | Pos | Neg | Neu |
|---|---|---|---|---|---|---|
| **Piña Medina (MC oposición)** | TWITTER | 100 | **-0.295** | 25 | 57 | 18 |
| Piña Medina | INSTAGRAM | 50 | +0.010 | 15 | 15 | 20 |
| Piña Medina | FACEBOOK | 55 | +0.064 | 17 | 14 | 24 |
| Piña Medina | TIKTOK | 62 | -0.178 | 9 | 23 | 30 |
| **Cravioto (MORENA)** | TWITTER | 100 | +0.403 | 62 | 4 | 34 |
| Cravioto | TIKTOK | 298 | -0.007 | 64 | 69 | 165 |
| **Jiménez (MORENA)** | TWITTER | 100 | +0.290 | 47 | 10 | 43 |
| Jiménez | TIKTOK | 1027 | +0.335 | 532 | 107 | 388 |
| Solano (MC opinión) | TWITTER | 100 | -0.090 | 20 | 33 | 47 |
| **Pineda (Gobierno Oaxaca)** | TWITTER | 100 | **+0.644** | 90 | 1 | 9 |
| Pineda | TIKTOK | 1052 | +0.602 | 803 | 27 | 222 |
| Nolasco (Gobierno Oaxaca) | TWITTER | 100 | +0.530 | 79 | 1 | 20 |

---

## Anomalías identificadas (6 problemas)

### 🔴 Anomalía #1 — Sentimiento del texto ≠ Imagen política

**Caso:** Piña Twitter avg = -0.295, 57/100 negativos.

**Posts ejemplo (todos clasificados NEGATIVE correctamente):**
- "Mi solidaridad con la familia del alcalde de Uruapan, Carlos Manzo. Su asesinato duele..." (-0.98)
- "Lo que ocurrió en Poza Rica tiene nombre: fraude. Morena le dio la espalda..." (-0.97)
- "Prometieron no subir la tarifa… y lo hicieron otra vez" (-0.96)
- "Dos semanas y el @metro de la Línea 1 volvió a fallar" (-0.96)

**Diagnóstico:** Piña es oposición → estrategia = criticar gobierno → tweets con tono negativo → sentiment NEGATIVE es técnicamente correcto pero engañoso como KPI de "imagen del político". Un dirigente opositor TIENE que publicar contenido negativo sobre el gobierno.

**Impacto:** El dashboard presenta "Sentimiento -0.295" como si fuera una métrica negativa, cuando refleja estrategia política normal de un opositor.

**Fix propuesto:**
1. Renombrar la métrica en UI: "Sentimiento del discurso" → **"Tono discursivo"** (crítico / neutral / propositivo / celebratorio)
2. Añadir segunda métrica: **"Sentimiento hacia el dirigente"** (analiza comments, NOT posts) — requiere scraper de replies
3. Contextualizar por rol político (oposición vs oficialismo) en el framing del KPI

---

### 🔴 Anomalía #2 — Retweets contaminan sentimiento (29-52% de tweets)

| Dirigente | RTs/100 tweets | RTs negativos |
|---|---|---|
| Rafael Solano | **52** | 9 |
| Yesenia Nolasco | **50** | 1 |
| Gabriela Jiménez | 36 | 2 |
| Piña Medina | 29 | 14 |
| Pineda Velasco | 11 | 0 |
| Cravioto | 3 | 0 |

**Diagnóstico:** Los RTs NO son contenido del dirigente, son amplificación de otros. Piña retuitea noticias negativas (asesinatos, fraudes) → infla su "sentiment negativo". Nolasco retuitea noticias positivas de gobierno → infla su "positivo".

**Fix propuesto:** Excluir RTs del cálculo agregado O etiquetarlos visualmente en la UI. Query actual no distingue originales vs RTs.

---

### 🔴 Anomalía #3 — Posts duplicados cross-platform (cuentan 3-4 veces)

**Ejemplos detectados:**
- "Para seguir impulsando una movilidad segura..." — Nolasco, 4 copias (FB + IG + TW + ?)
- "Desde la #Semovi les mando un saludo..." — Nolasco, 4 copias (FB + IG + TW)
- "¡El mayor de los éxitos a las y los atletas capitalinos!" — Cravioto, 4 copias
- "Domingo futbolero ⚽️" — Piña, 4 copias (FB + IG)

**Diagnóstico:** Práctica normal de políticos publicar el mismo contenido cross-platform. No es bug del scraper pero inflan promedios agregados (cuenta 3-4 veces el mismo mensaje).

**Fix propuesto:** Deduplicar por `(dirigente_id, LEFT(content, 100))` antes de calcular promedios agregados. Query demo ya probada abajo.

---

### 🟡 Anomalía #4 — Posts muy cortos ruidosos

39 posts con < 20 chars. Ejemplo problemático:
- "¡Adiós! ¡Adiós!" → clasificado NEGATIVE (-0.77) ❌

**Diagnóstico:** Modelo pysentimiento con contexto insuficiente produce clasificaciones poco confiables en textos ultra cortos.

**Fix propuesto:** Excluir posts < 30 chars del sentiment agregado O marcarlos con `confidence='low'`.

---

### 🟡 Anomalía #5 — 54% de posts con emoción "others" (pysentimiento no identifica)

| Emoción dominante | Posts |
|---|---|
| others | 1,994 (54%) |
| joy | 1,590 (43%) |
| anger | 82 |
| sadness | 41 |
| surprise | 2 |

**Diagnóstico:** El modelo de emociones pysentimiento es débil para español político. Más de la mitad de posts no tiene emoción clasificable.

**Fix propuesto:** O usar modelo mejor (ej. BETO fine-tuned) o eliminar widget de emociones de la UI (no aporta señal).

---

### 🟡 Anomalía #6 — Pysentimiento es un modelo general, no político

pysentimiento fue entrenado en corpus generales (reviews, tweets sobre diversos temas), no sobre discurso político mexicano. Frases comunes en política:
- "Exigimos a Morena que rinda cuentas" — NEGATIVE (pero es declaración legítima de oposición)
- "Estamos trabajando con la Jefa de Gobierno" — POSITIVE (pero para opositores suena a sumisión)

**Fix propuesto:** Este es un blocker para un v2 — usar LLM (Gemma/Claude) con prompt político específico O fine-tune BETO sobre discurso mexicano.

---

## Impacto cuantificado del fix propuesto

Aplicando #2 (excluir RTs) + #3 (deduplicar):

| Dirigente | Antes avg_sent | Después avg_sent | Δ |
|---|---|---|---|
| Piña Medina | -0.295 (TW) | **-0.165** | +0.13 |
| Cravioto | +0.403 (TW) / -0.007 (TT) | **+0.148** | mezcla |
| Jiménez | +0.290 (TW) | **+0.342** | +0.05 |
| Solano | -0.090 (TW) | **+0.071** | +0.16 (cambia signo) |
| Pineda | +0.644 (TW) | **+0.608** | -0.04 |
| Nolasco | +0.530 (TW) | **+0.387** | -0.14 |

**Observación:** Solano cambia de negativo a positivo después de limpiar RTs (sus tweets propios son positivos, sus RTs eran críticas que amplificaba).

---

## Plan de acción recomendado (en orden)

### Inmediato (esta sesión)
1. **Excluir RTs del sentiment agregado** — filtro `WHERE content NOT LIKE 'RT @%'` en endpoints de overview y sentiment-timeline
2. **Deduplicar por contenido** en agregaciones — `DISTINCT ON (dirigente_id, LEFT(content, 100))`
3. **Excluir posts < 30 chars** del avg
4. **Renombrar UI**: "Sentimiento" → "Tono discursivo" con explicación en tooltip

### Sprint siguiente
5. **Scraper de comments/replies** — para medir "sentimiento hacia el dirigente" (lo que dice la gente de él) vs "sentimiento del discurso" (lo que él dice)
6. **Desactivar widget de emociones** hasta tener modelo mejor
7. **Prompt LLM político** — usar Gemma local con prompt contextual sobre rol oficialismo/oposición

### Deuda de diseño (futuro)
8. **Fine-tune modelo BETO** sobre discurso político mexicano (requiere dataset etiquetado)

---

## Archivos afectados por el fix #1-#4

- `backend/app/api/v1/endpoints/dashboard.py` — `/overview` agregación
- `backend/app/api/v1/endpoints/social.py` — `/sentiment-timeline`, `/posts`
- `frontend/src/components/charts/sentiment-line-chart.tsx` — tooltip y labels
- `frontend/src/app/dashboard/page.tsx` — KPI card "Sentimiento" → "Tono discursivo"
