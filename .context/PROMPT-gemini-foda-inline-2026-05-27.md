# PROMPT para Gemini PRO (inline) — Generar FODA de 7 dirigentes · 2026-05-27

**Tú (Gemini) eres el modelo que razona.** NO corras `regen_diagnostico_gemini.py`, NO llames `gemini -p`, NO uses ningún script wrapper (eso dispara 429 + ENAMETOOLONG). El loop es: `psql SELECT` → razonas el FODA con tu propio criterio → `psql INSERT`. Igual que el patrón NLP-284.

## Reglas duras
- Solo lectura + INSERT en `planes_ia`. NO toques scrapers, NO toques Instagram (freeze).
- Grounded 100% en la data real que lees. NO inventes métricas ni hechos.
- Español. FODA conciso y accionable para campaña política.
- Idempotente: marca tu corrida con `modelo_ia='gemini-pro-inline-2026-05-27'`. Si re-corres, primero `DELETE FROM planes_ia WHERE tipo='DIAGNOSTICO' AND modelo_ia='gemini-pro-inline-2026-05-27' AND dirigente_id=:did;` antes del INSERT (evita duplicar).

DB: `PGPASSWORD=crece_dev psql -h localhost -p 5438 -U crece -d crece`

## Dirigentes en scope
`1` Piña · `2` Solano · `3` Saymi · `5` Gaby · `8` Ballesteros · `57` Pepe Monroy · `60` Felipe Martínez.

## Por CADA dirigente (did), corre estos SELECT para reunir evidencia:

```sql
-- A) Identidad
SELECT id, full_name, cargo, partido, rol_politico FROM dirigentes WHERE id=:did;

-- B) Perfiles + audiencia por red (followers REALES, ya frescos)
SELECT platform, handle, followers_count, posts_count
FROM social_profiles WHERE dirigente_id=:did ORDER BY followers_count DESC;

-- C) Engagement + volumen por red
SELECT spr.platform, COUNT(sp.id) posts,
  round(AVG(sp.engagement_rate)::numeric,2) er_prom,
  round(AVG(sp.sentiment_score)::numeric,3) sentiment_prom
FROM social_profiles spr JOIN social_posts sp ON sp.profile_id=spr.id
WHERE spr.dirigente_id=:did GROUP BY spr.platform ORDER BY posts DESC;

-- D) Distribución de tono del discurso (mix editorial)
SELECT tono_discurso, COUNT(*) n
FROM social_posts sp JOIN social_profiles spr ON sp.profile_id=spr.id
WHERE spr.dirigente_id=:did AND tono_discurso IS NOT NULL
GROUP BY tono_discurso ORDER BY n DESC;

-- E) Recepción de la audiencia (tono de comentarios)
SELECT sc.nlp_tono, COUNT(*) n
FROM social_comments sc JOIN social_posts sp ON sc.parent_post_id=sp.id
JOIN social_profiles spr ON sp.profile_id=spr.id
WHERE spr.dirigente_id=:did AND sc.nlp_tono IS NOT NULL
GROUP BY sc.nlp_tono ORDER BY n DESC;

-- F) Temas dominantes (muestra)
SELECT topics_extracted->'topics' FROM social_posts sp JOIN social_profiles spr ON sp.profile_id=spr.id
WHERE spr.dirigente_id=:did AND topics_extracted IS NOT NULL LIMIT 30;

-- G) admin uid (para generado_por_id)
SELECT id FROM users WHERE role='ADMIN' LIMIT 1;
```

## Razona el FODA — EXIGENCIA DE PROFUNDIDAD (no escueto)
**Mínimo 3 ítems por cuadrante (idealmente 3-4). NUNCA 1 solo.** Aunque la cuenta sea chica, SIEMPRE hay 3+ ángulos: cruza redes, tono, recepción, temas, ritmo de publicación. Si te faltan ideas, mira otra dimensión (ej. mix de tono editorial, ratio críticos/celebratorios, red con ER alto vs red dormida, tema dominante, ausencia de tema clave).

Cada ítem:
- `titulo`: frase estratégica y accionable (no una etiqueta de 2 palabras).
- `evidencia`: **1-2 oraciones completas** con (a) el número concreto, (b) una comparación o contexto, y (c) la implicación estratégica. NO one-liners.

**Calibración — esto es lo que NO quiero (escueto), y lo que SÍ quiero (rico):**
- ❌ Pobre: titulo="Semilla inicial en TikTok", evidencia="TikTok lidera con 2,380 seguidores."
- ✅ Rico: titulo="TikTok es el único motor de tracción real", evidencia="Con 2,380 seguidores y 2.91% de ER en 98 posts, TikTok concentra casi toda la interacción útil — supera por mucho a FB (4,714 seguidores pero ER plano) y a IG (6 seguidores, irrelevante). Es el canal donde conviene invertir el grueso de la producción de video corto."

Sé honesto: red con audiencia chica o ER=0 = Debilidad real, no la maquilles. Pero descríbela con contexto y qué hacer al respecto.

## Persiste (UN INSERT por dirigente)
`estructura_json` DEBE tener AMBOS shapes (el endpoint lee top-level español; el script de Planes lee `.foda.{F,O,D,A}`):

```sql
DELETE FROM planes_ia WHERE tipo='DIAGNOSTICO' AND modelo_ia='gemini-pro-inline-2026-05-27' AND dirigente_id=:did;

INSERT INTO planes_ia (dirigente_id, tipo, contenido, modelo_ia, prompt_usado, generado_por_id, aprobado, estructura_json, created_at)
VALUES (
  :did, 'DIAGNOSTICO',
  'FODA generado inline por Gemini PRO grounded en data real 2026-05-27',
  'gemini-pro-inline-2026-05-27',
  'PROMPT-gemini-foda-inline-2026-05-27.md',
  :admin_uid, false,
  CAST(:json AS JSONB),
  NOW()
);
```

Donde `:json` =
```json
{
  "version": "gemini-pro-inline-2026-05-27",
  "fortalezas":   [{"titulo": "...", "evidencia": "..."}],
  "oportunidades":[{"titulo": "...", "evidencia": "..."}],
  "debilidades":  [{"titulo": "...", "evidencia": "..."}],
  "amenazas":     [{"titulo": "...", "evidencia": "..."}],
  "foda": {
    "F": ["mismo titulo de cada fortaleza, string"],
    "O": ["..."],
    "D": ["..."],
    "A": ["..."]
  },
  "baseline": {
    "profiles": [{"platform": "...", "handle": "...", "followers": 0, "posts": 0}]
  }
}
```
(Los arrays `foda.{F,O,D,A}` = los mismos títulos de los ítems top-level, como strings. `baseline.profiles` = lo que leíste en SELECT B.)

## Verificación al cierre (debe dar 7)
```sql
SELECT COUNT(DISTINCT dirigente_id) FROM planes_ia
WHERE tipo='DIAGNOSTICO' AND modelo_ia='gemini-pro-inline-2026-05-27';
```
Reporta: tabla por dirigente con # ítems F/O/D/A. Cuando termines, avisa a CC — él corre la derivación de Planes (determinista, host).
