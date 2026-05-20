# Feedback CEO 2026-05-20 · `/dashboard/aceptacion/fantasmas` tab "Perfiles Observados"

**Captura:** Saymi · ventana 44d · 56.5K reacciones · 1.5K comments · 99.9% NLP · 476 posts.
**Status:** CEO documentó issues durante revisión visual · regresa para review/aprobación de cambios. **NO IMPLEMENTAR HOY.**

---

## Issues reportados

### 1. ⚠️ Renombrar columnas "Ganadores" / "Negativos" (HIGH)

**Componente:** `frontend/src/components/aceptacion/top-posts-cards.tsx:147`

**Estado actual:**
```tsx
{winner ? "Ganadores" : "Negativos"}
```

**Problema raíz:** la columna mide **polaridad NLP promedio de los comments**, NO el sentimiento del post. Confusión visible en captura: post de Día de la Niña/Niño (con texto positivo) aparece como "Negativo" porque sus *comments* tienen polaridad -1.00.

**Decisión previa CEO ("quedamos que tendría otro nombre"):** "Negativos" debe renombrarse. Ejemplo dado por CEO: **"Menos Audiencia"**. NO es decisión final — espera confirmación.

**Propuesta para review (cuando CEO regrese):**

| Actual | Propuesto opción A | Propuesto opción B | Opción C |
|---|---|---|---|
| Ganadores | Mejor recibidos | Bien recibidos | Más audiencia favorable |
| Negativos | Peor recibidos | Menos audiencia | Más rechazo en comments |

**Sub-acción:** ambos headers (Ganadores/Negativos) y la línea explicativa deben coincidir en mensaje. Header columna NO puede contradecir al subtítulo.

---

### 2. ⚠️ Subtítulo / explicación poco visible (MED)

**Componente:** `frontend/src/components/aceptacion/watched-profiles-tab.tsx:512-518`

**Estado actual:**
```tsx
<h3>Posts mejor y peor recibidos por sentimiento de comentarios</h3>
<p>Ranking por polaridad NLP promedio (no por engagement). Últimos 30 días, Facebook.
   Para ver el ranking por engagement absoluto: Contenido → Más populares.</p>
```

**Problema:** la explicación es correcta pero NO compensa la confusión "Ganadores/Negativos". CEO razonó en voz alta: "Ahhhh ya vi porque, es porque tienen los comentarios negativos." — el dato está en pantalla pero el usuario tuvo que deducirlo.

**Propuesta:** además de renombrar columnas (issue #1), reforzar en cada CARD de post el contexto: agregar línea pequeña tipo "Comments avg: -1.00" o ícono explicativo en lugar de solo `+1.00 / -1.00` desnudo.

---

### 3. 🔴 Posts sin ninguna reacción aparecen rankeados (HIGH · pendiente verificación)

**Observación CEO textual:** *"Hay datos que no tienen ninguna reacción y eso es ilógico por lo que yo observé y revisé."*

**Hipótesis:** el ranking de polaridad NLP no filtra por reactions/comments mínimos. Un post con 0 reactions pero 1 comment fuertemente negativo puede aparecer en "Negativos".

**Verificación requerida:** revisar query SQL del endpoint que sirve a `TopPostsCards`. Si NO hay filtro de `reactions > 0 OR comments >= N`, agregar threshold (sugerencia: `comments >= 3` mínimo para evitar muestras absurdamente pequeñas, mismo criterio que F4b plan).

**Archivo backend a inspeccionar:** probable `backend/app/api/v1/endpoints/aceptacion.py` o similar (no `posts_unified.py`, ese sirve a /hub).

---

### 4. 🟡 Posts con menos likes que comments negativos — caso confirmado

**Observación CEO:** *"hemos visto que sí hay post con menos likes."* + se respondió a sí mismo: *"es porque tienen los comentarios negativos"*.

**No es bug**, es feature observada empíricamente. El framework refleja correctamente que un post con muchos comments críticos (poca recepción positiva) cae al lado "Negativos" aunque el contenido del post sea neutral/positivo.

**Acción:** ninguna técnica. Documentar en metodología cliente que la métrica es **recepción del público (comments NLP)** ≠ **autoría del post (tono_discurso)**. Distinguir ambas en UI con etiquetas claras (issue #1 + #2).

---

### 5. 🟡 Tooltip "% CLASIFICADOS NLP"

**Captura visual:** tooltip aparece sobre "Comments en posts del dirigente en la ventana. Cuenta total de comments en BD."

Es un tooltip que ESTÁ funcionando — no es issue. Solo se anota porque la captura lo muestra abierto. Tooltip OK.

---

## Plan de implementación (cuando CEO confirme)

1. **CEO decide naming** para columnas Ganadores/Negativos (3 opciones propuestas issue #1).
2. **Verificar query backend** del TopPostsCards: agregar filtro `comments >= N` (issue #3).
3. **Actualizar headers + subtítulo + tooltips** en `top-posts-cards.tsx` + `watched-profiles-tab.tsx` consistente con nuevo naming.
4. **Smoke Playwright** en `/dashboard/aceptacion/fantasmas?tab=perfiles-observados`.
5. **Commit + deploy Vercel.**

---

## Archivos involucrados

- `frontend/src/components/aceptacion/top-posts-cards.tsx` (líneas 130-150 + dialog details 200-241)
- `frontend/src/components/aceptacion/watched-profiles-tab.tsx` (líneas 512-518)
- Backend hook que sirve datos: investigar `useTopPosts` o equivalente en `frontend/src/lib/api/hooks/`
- Backend endpoint: verificar query SQL del ranking polaridad

---

## Memoria a guardar (si CEO ratifica)

Sub-regla NLP: **polaridad NLP promedio de comments ≠ tono_discurso del post**. UI debe distinguir ambas dimensiones explícitamente. Confusión "Día de la Niña/Niño aparece negativo" fue causada por mezclar estos dos conceptos en headers de columna.
