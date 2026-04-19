# Prompt congelado — Layer 2 Triangulación

**SHA256 del template (sin placeholders):** `b0e456e860173878a2a5dfddf4682ddbf1cb9d707faa687ee27206c4fe464499`
**Fuente:** `backend/scripts/nlp_layer2_gemma_bg.py` → `PROMPT_TEMPLATE` (extraído 2026-04-18 ~12:40 MX)

Idéntico prompt usado por los 3 clasificadores. Cualquier divergencia entre modelos se atribuye al modelo, no al prompt.

## Instrucciones para los 3 clasificadores

Los clasificadores reciben este prompt con placeholders `{post_text}`, `{plataforma}`, `{comment_text}` reemplazados por los valores del comment en turno. No deben añadir, quitar, ni reformatear nada.

## Template (verbatim)

```
Eres un analista de sentimiento político mexicano. Clasifica este comentario.

CONTEXTO:
- Post original (del político): {post_text}
- Plataforma: {plataforma}

COMENTARIO:
"{comment_text}"

Responde SOLO en JSON válido con estos campos:
{
  "tono": "elogio|critica|pregunta|ataque|informativo|personal|autopromocion",
  "target": "dirigente_post|gobierno|oposicion|ciudadania|institucion|otros",
  "intensidad": -3 a 3 (entero),
  "polaridad_preliminar": "aprobacion|neutral|rechazo",
  "razon_corta": "una frase"
}
```

## Reglas de interpretación del output

- **Tono mandatory** — uno de los 7 valores enumerados. Si el modelo devuelve otro, se normaliza a `otros` (que NO está en el enum → debe marcarse error y re-intentar).
- **Target mandatory** — uno de los 6 valores. Mismo criterio.
- **Intensidad mandatory** — entero en [-3, 3]. Fuera de rango → error.
- **Polaridad mandatory** — uno de los 3 valores.
- **Razón corta mandatory** — string ≤500 chars.

## Normalización para merge

Antes de merge, los 3 outputs se normalizan a `schema.ClassificationRow`:
- Claude y Gemini devuelven JSON directo en respuesta → parse
- Gemma devuelve con `format=json` Ollama → parse
- Errores se escriben igual con `{"_err": "..."}` en lugar de campos, y no se consideran en el cálculo de acuerdo

## Por qué este prompt (history)

El prompt se congela aquí porque:

1. Ya está en producción Gemma3:12b (aceptado CEO 2026-04-14)
2. Modificarlo cambiaría el benchmark Gemma retroactivamente
3. Los 3 modelos deben ver exactamente la misma instrucción — sin prompt eng por modelo

Si en Fase 3 la matriz v3 sugiere cambios de prompt, esos cambios van a un prompt nuevo en otra evaluación, no retro-editan este.
