# Code-review independiente · migración `d23g1_actividad_alineada.py`

**Auditor:** `superpowers:code-reviewer` subagent (autor independiente per D-OPS-10)
**Fecha:** 2026-04-24
**Veredicto:** ✅ **APROBADA CON OBSERVACIONES** (3 puntos)

## Cumplimiento de protocolos

| Protocolo | Estado | Notas |
|-----------|--------|-------|
| **D-OPS-08** hand-written sin autogenerate | ✅ | Cabecera explícita líneas 1-9 · sin residuo "auto generated" · comentarios línea por línea numerados 1-5 |
| **D-OPS-09** atómica solo schema | ✅ | 5 ops upgrade · 5 ops + 3 drop_constraint downgrade · sin INSERT/UPDATE · sin mezcla con código |
| **D-OPS-10** diff legible no destructivo | ✅ | `upgrade()` cero `drop_*` · `downgrade()` simétrico · round-trip preserva schema |

## Verificación schema design

- CHECK constraints sintácticamente correctos · permiten NULL donde aplica (líneas 98, 135)
- `target_politico` valores `('oficialismo', 'oposicion', 'propio', 'personal', 'no_determinado')` consistentes con plan
- `clasificacion_origen NOT NULL DEFAULT 'ai_suggested'` no rompe UNIQUE/trigger (columna nueva)
- Partial index `ix_social_posts_profile_target_politico` sintaxis correcta
- **Discrepancia plan vs migración resuelta correctamente**: plan menciona índice sobre `(dirigente_id, target_politico)` pero `social_posts.dirigente_id` no existe · join va vía `profile_id → social_profiles → dirigente_id` · migración usa `(profile_id, target_politico)` · decisión correcta y documentada en cabecera líneas 42-46

## Reversibilidad

- `social_posts` ~3,800 filas · `ADD COLUMN` con default constante es metadata-only en PG ≥11 · sin riesgo de bloqueo largo
- `clasificacion_origen NOT NULL DEFAULT` lazy (PG ≥11) · no reescribe tabla
- CHECK constraint sobre filas existentes no genera estado inválido · default toma valor válido y otros permiten NULL

## Observaciones a aplicar (3)

### 1. Pre-flight check obligatorio

Antes de `alembic upgrade head`:

```bash
# Confirmar que las 4 columnas NO existen
docker exec crece-backend python -c "
from sqlalchemy import create_engine, text
e = create_engine('postgresql://crece:crece_dev@db:5432/crece')
with e.connect() as c:
    rows = c.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name = 'social_posts' AND column_name IN ('target_politico','nlp_model_version','clasificacion_origen')\"))
    print('social_posts duplicados:', list(rows) or 'ninguno · OK')
    rows = c.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name = 'dirigentes' AND column_name = 'rol_politico'\"))
    print('dirigentes duplicados:', list(rows) or 'ninguno · OK')
"

# Confirmar alembic head es la esperada
docker exec crece-backend alembic heads
# Esperado: s5m1_onboarding_tables (head)
```

**Status pre-aplicación 2026-04-24:** ambos checks ya verificados antes de escribir la migración:
- Schema actual confirmado · ninguna de las 4 columnas existe
- Alembic head confirmado · `s5m1_onboarding_tables`

### 2. Backfill semántico Day 4 (ajuste plan)

Los 95 posts pre-clasificados manualmente por equipo MD en sprint 2026-04-13 NO deben quedar como `ai_suggested` (default de la migración). El script `backfill_target_politico.py` (Day 4) debe:

1. Identificar los 95 posts pre-clasificados (filtro: `topics_extracted IS NOT NULL` y/o por fecha pre-2026-04-18)
2. `UPDATE social_posts SET clasificacion_origen='human_admin' WHERE id IN (...)` ANTES del IA backfill
3. Esos 95 posts quedan respetados sobre IA en queries del KPI

Documentado en plan línea ~Day 4.

### 3. Verificar `profile_id` existe en social_posts

Confirmado vía information_schema · `social_posts.profile_id integer` existe · index parcial `(profile_id, target_politico) WHERE target_politico IS NOT NULL` válido.

## Próximo paso

Tras firma CEO + ejecución pre-flight check, aplicar:

```bash
docker exec crece-backend alembic upgrade head
```

Verificar resultado:

```bash
docker exec crece-backend alembic current
# Esperado: d23g1_actividad_alineada (head)
```
