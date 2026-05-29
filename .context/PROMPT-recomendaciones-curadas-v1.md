# Prompt maestro · Recomendaciones IA curadas — v1 (2026-05-12)

Destilado del flujo que produjo las 5 recomendaciones de Pepe Monroy (calidad
demo, cross-audit Gemini aplicado al 100%). Sirve como estándar para los 7
dirigentes restantes y futuros perfiles.

---

## 1. Inputs no negociables

Antes de redactar UN solo draft, leer:

| Input | Fuente |
|-------|--------|
| 10 posts más recientes del dirigente (content + plataforma + fecha) | `social_posts JOIN social_profiles WHERE dirigente_id=X ORDER BY published_at DESC LIMIT 10` |
| Perfil estructural | `dirigentes` (`partido`, `rol_politico`, `cargo`, `estado`) |
| FODA actual | endpoint `/diagnostico/foda/{id}` o `planes_ia` tipo DIAGNOSTICO |
| Plataformas activas con followers | `social_profiles WHERE dirigente_id=X` |
| Comments analizados (matriz v2) | `social_comments` con `nlp_model_version='comment-framework-v2'` |

**Regla**: si no tienes datos en alguna fila, declarar el gap en el draft, no inventar.

---

## 2. Identidad por extracción tonal

Antes de redactar, completar este resumen del tono observable en sus 10 posts:

- **Plataforma dominante** (mayor frecuencia + engagement)
- **Vetas temáticas** (típicamente 3-4: institucional / personal / coyuntural / cívica)
- **Hashtag pattern** (¿usa muchos? ¿una sola línea? ¿en MAYÚSCULAS?)
- **Estructura típica** (longitud de párrafo, uso de emojis, cita a otros actores)
- **Marco político**: ¿oficialismo (defiende gestión propia / 4T) o oposición
  (contraste vs adversario)?
- **Audiencia**: leal vs cross-cutting · partidista vs neutral

Si el dirigente es **oficialismo (MORENA)**, su veta institucional es PROYECTO
NACIONAL / 4T / Sheinbaum / Brugada / etc. Si es **oposición (MC)**, su veta
institucional es CONTRASTE / DENUNCIA / "lo que no hicimos / hicieron mal".

---

## 3. Selección de efemerides (por dirigente)

Por cada efeméride candidata próxima 60 días:

| Filtro | Acción |
|--------|--------|
| Viralidad **alta** + cargo NACIONAL/ESTATAL | INCLUIR siempre |
| Viralidad **media** + alineada con sus vetas | INCLUIR |
| Viralidad **media** + agenda polarizante (LGBT+, aborto, religión) | EVALUAR riesgo según base · típicamente DESCARTAR para perfil conservador |
| Viralidad **baja** | Descartar salvo conexión directa con el cargo |
| **Jornada electoral** (cualquier año) | INCLUIR si el cargo es legislador / dirigente partidista — omitirla es señal débil |

Si el cargo es **único** (ej. Pepe = Líder Nac. Partidos Locales), buscar efemerides
que conecten con su función específica (Día de la Democracia 15-sep, Día Internacional
de la Paz 21-sep para Pepe).

---

## 4. Estructura por recomendación (lo que va a la BD)

```yaml
tipo: start | continue | mitigar       # default start para efemerides
accion_texto: |
  # Título corto con emoji(s) — 1 línea, sin "POST IG + FB" (los iconos lo dicen)
  
  Contexto estratégico (1-2 líneas): por qué este día, para esta persona.
  
  Marco/Tono: (1 línea) qué emoción/postura le da peso.
  
  Draft (post real, en SU voz, listo para publicarse):
  "..."
  
  Notas operativas: hora de publicación, formato (post/reel/story), CTA.

ventana_inicio: TIMESTAMPTZ                # día previo 18-20h
ventana_fin: TIMESTAMPTZ                   # día efeméride 23:59
ventana_duracion_dias: int

criterio_exito: {
  # objetivo MEDIBLE — ratio engagement, # comments, # shares, etc.
  # Comparar contra baseline propio del dirigente, NO contra cifras inventadas.
}

principio_conductual: str                  # 1 frase: Cialdini Authority, Haidt Care,
                                           # Cialdini Affinity, Sunstein Choice,
                                           # Heath StickyMessage, etc.

evidencia_respaldo: {
  # Por qué este draft funciona PARA ESTE dirigente:
  # - Veta tonal alineada (cita posts pasados)
  # - Oportunidad/Debilidad de su FODA que ataca
  # - Plataforma específica
}

estado: aprobada                           # default visible al cliente
```

---

## 5. Reglas anti-genérico

1. **El draft debe ser indistinguible** de un post propio del dirigente al leerlo
   sin contexto. Si suena a "comunicado oficial genérico", está mal.
2. **Hashtags consistentes** con su pattern observable. No agregar hashtags que
   no usa nunca.
3. **Cero plantilla de relleno** tipo "Como [cargo], reafirmo el compromiso con
   [eje]". Eso es lo que NO queremos.
4. **Marco propio del partido**: MORENA habla de "transformación", "primero los
   pobres", cita a Sheinbaum/AMLO. MC habla de "naranja", "Nuevo Norte", "Samuel
   García", "ciudadanía"; ataca a MORENA y PAN simétricamente.
5. **Tonalidad del cargo**:
   - Legislador → habla del Congreso, foros, dictámenes, iniciativas
   - Ejecutivo estatal/municipal → habla de obra, infra, atención ciudadana
   - Dirigente partidista → habla de afiliación, militancia, territorio
6. **Sin emojis genéricos**: usar los que el dirigente YA usa. Si solo usa 🏛️ y
   🤝, no metas 🌟 o 🔥.

---

## 6. Cross-audit Gemini (obligatorio)

Después de redactar las N recomendaciones por dirigente, enviar a Gemini con:

```
Critica estos drafts. Devuelve veredicto APROBADO / AJUSTAR / DESCARTAR por
cada uno. Evalúa:
1. ¿Captura el tono real del dirigente?
2. ¿Hay riesgo INE / polarización?
3. ¿Fecha y ventana razonable?
4. ¿Falta alguna efeméride crítica para su perfil?
5. ¿La estructura/longitud matchea su estilo?
```

Aplicar el 100% de los AJUSTAR/DESCARTAR antes de INSERT a BD.

---

## 7. Anti-patterns vistos en el bulk-v1 (skeleton automático)

- `accion_texto` con "POST IG + FB" en texto → redundante con iconos. **EVITAR**.
- Draft genérico tipo "Como [cargo], reafirmo el compromiso con [eje principal]"
  → no agrega valor. **EVITAR**.
- Mismo draft para 7 dirigentes con substitución de variables → suena a
  mailing automático. **EVITAR**.
- Hashtags inventados que el dirigente no usa → ruptura de identidad. **EVITAR**.

---

## 8. Validación post-INSERT

1. Login como el dirigente (viewer) → ver las recs en /dashboard/recomendaciones
2. Verificar iconos de plataforma renderizan correcto
3. Draft block (mono + border-left) visible
4. Hash de validación: las 5 recomendaciones deben sentirse como "una conversación
   curada por un equipo humano que conoce al dirigente" — no como output de bot.

---

*Prompt destilado por Claude Code 2026-05-12 tras la curación hand-crafted de
Pepe Monroy (5 recs · cross-audit Gemini) y el bulk-v1 fallido (35 recs
templated, sin voz propia, reemplazadas por la versión hand-crafted v2).*
