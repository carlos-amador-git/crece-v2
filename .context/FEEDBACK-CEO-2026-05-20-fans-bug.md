# Bug crítico Top Fans Saymi · 2026-05-20

**Reporte CEO:** *"Misael no puede ser top 1 y luego estar en lugar 3 dentro de Audiencia Objetivo. Hugo menciona a Carlos —apellido extraño— que tenía 232 o más likes, y otros fans que ahora no se ven."*

**Status:** documentado. **NO IMPLEMENTAR** hasta que CEO confirme alcance. Hugo (peer s2ryygne) parado esperando findings para reconciliar con su side.

---

## Hallazgo #1 · Misael DUPLICADO en watched_profiles (CRÍTICO)

**Evidencia BD verificada empíricamente 2026-05-20 08:50:**

```
id=1  · ext_id=61578398601244        · Misael Gómez · source=cliente_seed   · 0 reactions reales
?     · ext_id=misael.gomez.981351   · (referido en vip-overrides.ts)        · usado por VIP override
?     · ext_id=42ac820...sha256      · Misael Gómez · source=auto_suggested · 77 reactions reales BD
```

Hay **al menos 2-3 representaciones distintas del mismo Misael** en BD:

1. **cliente_seed** (id=1) · ext_id numérico FB `61578398601244` · sin reactions · creado en seeding manual sprint-S8-final.
2. **auto_suggested** · ext_id hash sha256 `42ac820a...` · 77 reactions reales del ingest RADAR.
3. **VIP override** referencia `misael.gomez.981351` (ext_id usado en `vip-overrides.ts:36`) → ¿existe en BD o es virtual?

**Consecuencia visible UI:**
- `TopFansRanking` aplica override → Misael #1 con 250 reactions (mockup `misael.gomez.981351`).
- `CuratedSeedList` (Audiencia Objetivo) muestra Misael **cliente_seed** con sus reactions reales (probable orden alfabético o por reactions).

**El CEO ve dos Misaeles distintos en la misma pantalla.** Visualmente parecen contradicción.

**Causa raíz probable:**
- Cuando RADAR ingestó reactions con `author_hash` (sha256 del nombre+platform), creó un nuevo `watched_profiles` row con `source=auto_suggested` en lugar de matchear contra el cliente_seed existente.
- vip-overrides.ts apunta a un ext_id (`misael.gomez.981351`) que NO matchea ni cliente_seed ni auto_suggested actual.

---

## Hallazgo #2 · "Carlos" de Hugo = Pedro Carlock (apellido extraño confirmado)

Hugo mencionó "Carlos con 232 o más likes". Empíricamente:

```
Top fans reales Saymi (auto_suggested, sin override):
#1 Pedro Carlock              234 reactions  ext_id=a1cf3c45...sha256
#2 Carlos David               159
#3 Roberto Carlos             150
#4 Juan Carlos Hernandez      129
#5 Misael Gómez (real)         77  ext_id=42ac820...sha256
#6 Carlos Hernandez            48
...
#9 Pedro Carlock (DUPLICADO)   36  ext_id=578633161 (FB user_id numérico)
```

**Pedro Carlock** está DUPLICADO también:
- `a1cf3c45...sha256` con 234 reactions (RADAR ingest reciente)
- `578633161` user_id numérico con 36 reactions (ingest viejo Apify?)

**Suma real Pedro Carlock = 234 + 36 = 270 reactions.** Hugo dijo "232 o más" — cercano a 234, su número de RADAR.

---

## Hallazgo #3 · "Otros fans que ahora no se ven"

CEO reportó que fans aparecidos antes ya no se ven. Hipótesis (sin verificar aún):
- Antes del ingest RADAR el TopFansRanking mostraba uno conjunto de fans (Apify scraper).
- Post-ingest RADAR aparecen los `auto_suggested` con sha256 hashes (Pedro Carlock 234, Carlos David 159, etc.).
- Si el componente filtra por `source` o por una ventana de fechas, fans pre-RADAR podrían quedar fuera.

**Verificación pendiente:** revisar query de `TopFansRanking` para entender qué incluye/excluye. Antes de tocar, necesitamos ver el diff visual antes/después del ingest.

---

## Acción técnica propuesta (NO IMPLEMENTAR sin CEO + Hugo)

### Corto plazo (cosmético + safety)

1. **Dedupe display en UI** — agrupar por `author_hash` o `display_name` normalizado: si "Misael Gómez" aparece en cliente_seed + auto_suggested, mostrar UNA sola entrada combinando reactions. **Cambio frontend solamente, BD intacta.**

2. **Mostrar fuente** — badge pequeño en cada fan: "cliente_seed" / "auto" / "VIP". Hace explícito por qué Misael salta a #1.

3. **Update vip-overrides.ts** — apuntar override a un ext_id que SÍ exista en BD (`42ac820...` para que el match funcione) en lugar de `misael.gomez.981351` que parece huérfano. Necesita confirmación CEO.

### Largo plazo (consolidación BD)

4. **Migration consolidate Misael** — UPDATE watched_like_events SET watched_profile_id = (id del cliente_seed) WHERE watched_profile_id IN (...duplicados...); DELETE duplicados auto_suggested. Tras esto, BD tiene UN solo Misael con TODAS sus reactions.

5. **Migration Pedro Carlock** — mismo patrón. Consolidar 234+36 reactions en una sola fila.

6. **Constraint anti-duplicado en watched_profiles** — UNIQUE INDEX (dirigente_observador_id, platform, author_hash) o LOWER(display_name) según política.

7. **Idempotencia ingest** — RADAR ingest debe matchear contra cliente_seed existentes ANTES de crear auto_suggested. Si display_name match → upsert sobre existente, NO insert nuevo.

### Coordinación con Hugo (mensaje propuesto)

```
Hugo, encontramos en CRECE BD el bug del duplicado que sospechabas:

- Misael Gómez existe 2+ veces: cliente_seed (id=1, 0 reactions) + auto_suggested (sha256 42ac820...) con 77 reactions reales del ingest RADAR.
- Pedro Carlock idem: ext_id sha256 (234r) + ext_id numérico 578633161 (36r) = 270 reactions reales si se consolidan.

Causa probable: tu ingest RADAR no matcheaba contra cliente_seed existentes; creaba auto_suggested nuevos por author_hash sha256 del display_name+platform.

Pregunta para tu side: cómo construyes el author_hash? Tienes alguna lógica de "si display_name existe ya en watched_profiles del dirigente, hacer UPSERT en lugar de INSERT"?

CEO está parando para revisar findings; sin urgencia. Cualquier insight de tu side ayuda.
```

---

## Archivos involucrados

- BD tabla `watched_profiles` (Saymi tiene 13 cliente_seed + N auto_suggested)
- BD tabla `watched_like_events` (eventos asociados al watched_profile_id)
- `frontend/src/lib/api/utils/vip-overrides.ts:36-52` · override ext_id `misael.gomez.981351`
- `frontend/src/components/aceptacion/top-fans-ranking.tsx` · aplica `applyVipOverrides`
- `frontend/src/components/aceptacion/curated-seed-list.tsx` · muestra Audiencia Objetivo (cliente_seed)
- Endpoint backend de top-fans (probable `aceptacion.py` o `watched_profiles.py`)

---

## Decisión NLP previa CEO (mismo cuestionario)

Para el feedback `.context/FEEDBACK-CEO-2026-05-20-fantasmas.md` issue #1 (renombrar "Ganadores/Negativos"):

✅ **CEO eligió opción C** — "Más audiencia favorable" / "Más rechazo en comments". Implementable junto con los fixes de este archivo, mismo PR.
