# HANDOFF — Cerrar NLP pendiente (~284 items) con Gemini INLINE · 2026-05-27

**Regla de oro:** Gemini clasifica **con su propio razonamiento (inline)** — lee filas, las clasifica en su respuesta, escribe el UPDATE. **NO** correr los scripts `backfill_*` ni llamar al binario `gemini -p` (eso dispara cloudcode-pa.googleapis.com → 429). El loop es: `psql SELECT → razonar → psql UPDATE → repetir`.

DB: `PGPASSWORD=crece_dev psql -h localhost -p 5438 -U crece -d crece`

## Pendientes (ubicación de la info)
**A) Comments sin clasificar (~277, con texto):**
```sql
SELECT sc.id, spr.dirigente_id, d.full_name, d.rol_politico, sc.content
FROM social_comments sc
JOIN social_posts sp ON sc.parent_post_id = sp.id
JOIN social_profiles spr ON sp.profile_id = spr.id
JOIN dirigentes d ON spr.dirigente_id = d.id
WHERE spr.dirigente_id IN (1,2,3,5,8,60)
  AND sc.nlp_tono IS NULL
  AND length(trim(COALESCE(sc.content,''))) > 0
ORDER BY spr.dirigente_id, sc.id
LIMIT 30;   -- procesar en lotes de 30; el WHERE es idempotente → re-correr saca los ya hechos
```
**B) Posts sin topics (~7, con texto):**
```sql
SELECT sp.id, d.full_name, sp.content
FROM social_posts sp
JOIN social_profiles spr ON sp.profile_id = spr.id
JOIN dirigentes d ON spr.dirigente_id = d.id
WHERE spr.dirigente_id IN (3,5,8)
  AND sp.topics_extracted IS NULL
  AND length(trim(COALESCE(sp.content,''))) > 0;
```

## Rúbrica de clasificación (CONSISTENTE con la data existente)
**Comments → `nlp_tono`** (uno de): `critico, propositivo, celebratorio, informativo, solidario, ataque, personal`
- critico: cuestiona/denuncia/señala fallas · propositivo: propone soluciones · celebratorio: celebra/apoya/felicita · informativo: hechos sin postura · solidario: condolencias/apoyo emocional · ataque: ataque directo a persona/institución · personal: sin carga política (saludos, felicitaciones genéricas)

**Comments → `nlp_target`** (uno de): `dirigente, gobierno, oposicion, ciudadania, medios, autopromocion, tema_especifico, otro`
- `dirigente` = dirigido directo al titular (usar `full_name` de la fila). `gobierno`/`oposicion` son RELATIVOS al `rol_politico` del dirigente (ej. para un MC=oposicion, criticar a MORENA = `gobierno`).

**Comments → `nlp_polaridad`** (smallint, DETERMINISTA del tono):
`celebratorio|solidario|propositivo → 1` · `personal|informativo → 0` · `critico|ataque → -1`

**Posts → `topics_extracted`** (jsonb): 2-4 temas en español, minúsculas. Formato EXACTO:
`{"topics": ["tema uno", "tema dos"], "extracted_at": "<ISO8601>", "model_version": "gemini-inline-2026-05-27"}`

## SQL de escritura
```sql
-- por comment:
UPDATE social_comments
SET nlp_tono='<tono>', nlp_target='<target>', nlp_polaridad=<-1|0|1>,
    nlp_model_version='gemini-inline-2026-05-27'
WHERE id=<id>;

-- por post (topics):
UPDATE social_posts
SET topics_extracted='{"topics":["..."],"extracted_at":"2026-05-27T...","model_version":"gemini-inline-2026-05-27"}'::jsonb
WHERE id=<id>;
```

## Verificación al cierre (debe dar 0)
```sql
SELECT spr.dirigente_id,
  COUNT(*) FILTER (WHERE sc.nlp_tono IS NULL AND length(trim(COALESCE(sc.content,'')))>0) AS comments_texto_pendientes
FROM social_comments sc JOIN social_posts sp ON sc.parent_post_id=sp.id
JOIN social_profiles spr ON sp.profile_id=spr.id
WHERE spr.dirigente_id IN (1,2,3,5,8,60) GROUP BY 1 ORDER BY 1;
-- + posts topics: ...WHERE topics_extracted IS NULL AND length(trim(content))>0
```

## NO hacer
- NO clasificar filas con content vacío (ya excluidas por el `length>0`; si aparece una vacía, déjala NULL).
- NO usar el binario `gemini -p` ni los scripts backfill (429).
- NO inventar contenido — clasificar SOLO sobre el `content` que existe.

Pendientes por dirigente (al momento): comments — Saymi 109, Balles 98, Piña 39, Gaby 19, Solano 9, Felipe 3 · topics — Saymi 3, Gaby 3, Balles 1.
