# Diagnóstico Visual CRECE v2 — Screenshots CEO 2026-04-23

**Fuente:** `/Users/marxchavez/Downloads/Screen Crece/` (11 screenshots anotadas a mano por CEO).
**Perfil activo en captura:** Laura Ballesteros Mancilla (IPD 3.1/10 · 88.8K audiencia · MC Dip. Fed. Plurinominal LXVI).
**Clasificación de severidad:** 🔴 bloqueante · 🟡 corregible en sprint · 🟢 cosmético.

---

## Hallazgos por screenshot

### F-23-01 · Dashboard Overview — Tema Urgente (screenshot.jpg) 🔴
- **Anotación CEO:** "Los sentimientos para la oposición deben ser opuestos a los del oficialismo, no los podemos evaluar igual. Ya teníamos esto muy bien definido."
- **Problema:** La tarjeta "Tema Urgente" y las Alertas de Crisis aplican el mismo signo de sentimiento sin considerar afiliación. Para oposición (MC), crítica a Morena debería leerse como neutral/positivo para el dirigente, no como riesgo negativo.
- **Acción:** Reactivar lógica de `sentimiento_vs_afiliacion` (matriz v2 / v3 pendiente). Verificar que `Tema Urgente`, `Alertas de Crisis` y `Sentiment Prom.` lean de la misma función `polariza_por_bando(dirigente, post)`.

### F-23-02 · Competidor Principal — Inconsistencia de dirigente (screenshot (1).jpg) 🔴
- **Anotación CEO:** "inconsistencias en los nombres" (flecha de Laura Ballesteros Mancilla → bloque "Alejandro Pina vs Martí Batres").
- **Problema:** El dirigente del sidebar (Laura) no coincide con el `vs Competidor Principal` que hardcodea Piña. El bloque debería reaccionar al dirigente activo o declararse como comparativo global.
- **Acción:** Bind del componente `CompetitorCompare` al `activeLeaderId`. Si el dirigente no tiene rival configurado → mostrar empty state, no Piña por default.

### F-23-03 · Tono Discursivo — Falta opción RT (screenshot (1).jpg, (3).jpg) 🟡
- **Anotación CEO:** "agregar la opción para que aparezcan los RT" (junto a toggle `% / N`).
- **Problema:** El filtro actual es "sin RTs · >20 chars" hardcodeado. Falta un toggle `RT` junto a `%` y `N`.
- **Acción:** Extender el toolbar con tercer toggle `incluir RTs`. Persistir en query params.

### F-23-04 · Tono Discursivo — Falta filtro por red (screenshot (3).jpg) 🟡
- **Anotación CEO:** "debemos tener filtros por red social".
- **Problema:** La gráfica agrega todas las plataformas; no se puede aislar X vs IG vs FB.
- **Acción:** Añadir multi-select de plataformas sobre el chart (reusar componente existente de `/dashboard/aceptacion`).

### F-23-05 · Publicaciones Recientes — Múltiples fallos (screenshot (2).jpg) 🔴
- **Anotación CEO:** "Hay una inconsistencia en el sentimiento. Muchos corazones, no tenemos los likes y aparecen cero comentarios. También la publicación no hace referencia a la red social y al hacer click, nos debería mandar al sitio donde está publicada."
- **Problemas identificados (4):**
  1. Sentimiento no encaja con el contenido (post de "domingo futbolero" marcado Positivo 88%, otro de corrupción marcado Negativo -52% — validar matriz).
  2. Likes: se muestra el ícono ♡ con número pero el CEO lo lee como "corazones sin significado" → falta label explícito `likes`.
  3. Comentarios y shares siempre en `0` → scraper no está poblando esos campos (o el modelo no los persiste).
  4. No se indica la red social (falta ícono de plataforma en cada card).
  5. Cards no son clickeables hacia la URL original del post.
- **Acción:** (a) Verificar campos `comment_count`/`share_count` en modelo + scraper. (b) Añadir `platform_icon` por post. (c) Convertir card en link a `post.source_url` (target=_blank + rel=noopener).

### F-23-06 · Ficha Dirigente — Sentimiento (30d) pobre (screenshot (4).jpg) 🟡
- **Anotación CEO:** Resalta el chart "Sentimiento (30 dias)" como problemático. Sentimiento Prom. `-59%`.
- **Problema:** Misma raíz que F-23-01 — sin correción de bando, todo se ve negativo para oposición.
- **Acción:** Ligado a F-23-01. Aplicar `polariza_por_bando` también en la ficha individual.

### F-23-07 · Ficha Dirigente → tab Electoral vacío (screenshot (6).jpg) 🔴
- **Anotación CEO:** "Esta vacía la sección" · "0 secciones" en header.
- **Problema:** Dirigentes plurinominales no tienen secciones electorales asignadas → la pestaña queda vacía sin mensaje útil.
- **Acción:** Empty state diferenciado: "Diputada plurinominal — sin secciones territoriales asociadas" + CTA para asignar territorio si aplica.

### F-23-08 · Ficha Dirigente → tab Planes vacío (screenshot (7).jpg) 🟡
- **Anotación CEO:** "no hay información" · "No hay planes generados para este dirigente".
- **Problema:** Empty state existe pero no ofrece camino de acción.
- **Acción:** Agregar CTA "Generar plan ahora" → dispara flujo `/planes-ia/generar?dirigente={id}`.

### F-23-09 · Diagnóstico Tier 1 — Encabezado confuso (screenshot (8).jpg) 🟡
- **Anotaciones CEO:**
  - "10 bloques Tier 1 MVP · rendimiento algorítmico y de audiencia" → "Explicar de qué se trata".
  - "(MASTER §3.1)" → "Eliminar" (referencia interna que no debe ver el cliente).
  - "7/10 con datos · 3 insuficiente" → convertir a "Lista desplegable".
  - Box explicativa con Zenodo/Brookings/Sprout Social → "Hay que explicarlo en forma llana, sin tecnicismos".
  - "¿Qué es entonces el ER?" → falta glosario o tooltip explicativo.
  - Link "Metodología completa →" → "no se muestra nada en metodología" (link roto / página en blanco).
- **Acciones:**
  1. Cambiar subtítulo técnico por lenguaje llano (1 oración, audiencia no-técnica).
  2. Quitar toda referencia a `MASTER §X.Y` de la UI (solo interno).
  3. Convertir el badge "7/10 con datos · 3 insuficiente" en popover/dropdown que liste qué bloques sí y qué bloques no.
  4. Reemplazar texto académico por analogía coloquial + CTA "Ver metodología" que lleve a una página funcional (actualmente vacía).
  5. Tooltip en "ER" definiéndolo ("Engagement Rate = interacciones ÷ alcance").

### F-23-10 · Diagnóstico Tier 1 — Bloques ininteligibles (screenshot (8).jpg, (9).jpg) 🔴
- **Anotaciones CEO:** "Demasiado texto. Y demasiado complejo para entenderlo." · "Ninguna de los temas (7) se entiende. Demasiado complejos o rebuscados en su redacción. Hay que simplificar, con un modelo de enseñanza si los textos son muy amplios. O un esquema más sutil que denote lo que se está mostrando en forma simple."
- **Bloques nombrados problemáticos:** B01 ER normalizado · B02 Breakout Scale (Brookings) · B03 Matriz 2×2 · B04 Benchmark · B05 Sentiment Plutchik · B06 Crisis Spike · B07 Growth attribution · B08 Share of Voice · B09 Share/Like Ratio · B10 Humanización.
- **Problemas:** nomenclatura académica, sin interpretación ("¿esto es bueno/malo?"), sin contexto de referencia visible sin leer párrafo.
- **Acciones:**
  1. Cada bloque debe responder 3 preguntas: **(i)** ¿qué mide? (frase corta no técnica); **(ii)** ¿cómo te fue? (semáforo verde/amarillo/rojo); **(iii)** ¿qué hacer al respecto? (acción recomendada).
  2. Bajar la densidad textual 60% — mover detalles técnicos a popover "¿cómo se calcula?".
  3. Renombrar títulos: `Breakout Scale (Brookings)` → `Escalón de viralidad`, `Humanización Score` → `Qué tan humano suena`, etc.

### F-23-11 · Diferenciadores Tier 2 — Misma crítica (screenshot (10).jpg) 🔴
- **Anotación CEO:** "muy bonitos los gráficos pero poco entendibles. Muy complicados. Los textos, lo que se busca transmitir al usuario que son mediciones de ciertas cuestiones importantes, que le entienda. Que considere que son útiles. Y que le digan dónde está parado."
- **Bloques afectados:** Cross-Partisan Validation · CIB Detector (ITESO/DFRLab) · Filtro de Realidad · Topic Drift Detector · Rage Click Flag · Rastreador Promesas · Veda INE · Violencia Política.
- **Acción:** Aplicar mismo patrón "qué mide / cómo te fue / qué hacer" al Tier 2. Prioridad: Rastreador Promesas (0/12) y Violencia Política (6%) — son los que más interesan al cliente político.

---

## Diagnóstico consolidado

### Fallas estructurales (causa raíz)
1. **Motor de sentimiento sin afiliación política aplicada en UI.** La matriz v2/v3 existe en backend pero varios componentes del dashboard leen signo crudo. Impacto: F-23-01, F-23-05, F-23-06.
2. **Scrapers con campos incompletos.** `comment_count`, `share_count` y `source_url` no se pueblan o no se pasan al frontend. Impacto: F-23-05.
3. **Componentes hardcodeados a Piña.** `CompetitorCompare` no respeta `activeLeaderId`. Impacto: F-23-02.
4. **Copywriting técnico / orientado a MVP interno.** Referencias a MASTER §, Zenodo, Brookings, Plutchik sin traducir a lenguaje ejecutivo. Impacto: F-23-09, F-23-10, F-23-11.
5. **Empty states pasivos.** Secciones vacías no ofrecen ruta de acción. Impacto: F-23-07, F-23-08.
6. **Falta granularidad de filtros.** Sin filtro por red y sin toggle RT. Impacto: F-23-03, F-23-04.

### Plan de corrección sugerido (3 bandas)
- **Banda 1 — Bloqueantes demo (día 1-2):** F-23-01, F-23-02, F-23-05 (inconsistencia sentimiento + post cards rotas + competidor hardcoded).
- **Banda 2 — UX ejecutivo (día 3-5):** F-23-09, F-23-10, F-23-11 (rewrite de copy con modelo "qué mide / cómo te fue / qué hacer").
- **Banda 3 — Pulido (día 6-7):** F-23-03, F-23-04, F-23-06, F-23-07, F-23-08 (filtros, empty states, tooltips).

### Hallazgos que requieren decisión CEO
- ¿El botón "Metodología completa" debe llevar a doc interno, a página pública, o se elimina?
- ¿Mantener referencias a Brookings/ITESO/DFRLab como credibilidad académica, o simplificar completamente?
- Para dirigentes plurinominales (sin territorio), ¿se oculta tab Electoral o se muestra con mensaje?

---

**Screenshots revisados:** 11 de 11.
**Findings nuevos:** 11 (F-23-01 a F-23-11).
**Severidad global:** 4 🔴 bloqueantes · 7 🟡 corregibles.
