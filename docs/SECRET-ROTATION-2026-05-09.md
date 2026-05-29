# Procedimiento · Rotación SCRAPECREATORS_API_KEY · 2026-05-09

**Estado:** ⚪ NO APLICA · marcado como referencia histórica
**Decisión CEO 2026-05-09:** rotación innecesaria. Justificación:
- Cuenta ScrapeCreators es **versión free** (sin medio de pago, sin riesgo de cargo no autorizado)
- Coolify **nunca desplegó** código que usara la key
- El intento de integración es viejo y **el código se va a borrar**

Riesgo residual: bajo. NO bloquea Fase 3 branches recovery. Documento conservado para trazabilidad histórica del hallazgo Fase 1.B y para referencia si en el futuro se reactiva la integración con cuenta de pago.

---

## Si en el futuro se reactiva ScrapeCreators con cuenta de pago

Aplicar el procedimiento abajo. Hasta entonces, este documento queda como información sin acción requerida.

---

## Severidad histórica (ya no aplica)

**Severidad:** ALTA
**Owner ejecución:** CEO (acceso a dashboard ScrapeCreators + Coolify + Vercel)
**Owner validación:** Linda (verificar limpieza en código tras rotación)
**Estado original:** PENDIENTE — bloqueante para Fase 3 branches recovery

---

## Hecho

Valor literal `pgmI0aOa8bSj9dUoh1Ja0OLwXTC2` está **expuesto en historia git** del repo (commit `821950b` 2026-04-18 entre otros, en `backend/benchmarks/scraping/runners/scrapecreators.py`). Identificado por primera vez 2026-04-26 en `PLAN-HALLAZGOS-2026-04-26.md:47`. Eliminado del HEAD pero NO purgado de history. Cualquier `git show 821950b` lo expone.

Asumir comprometido: GitHub público es indexado por bots de scraping de secrets en <1h.

## Pasos de ejecución (CEO)

### 1. Revocar key actual en dashboard ScrapeCreators

- Login: https://scrapecreators.com (cuenta CEO)
- Dashboard → API Keys → revocar `pgmI0aOa...XTC2`
- Confirmar que está REVOKED, no solo desactivada

### 2. Generar nueva key

- Crear nueva key con mismo scope que la anterior
- Copiar valor (no compartirlo en chat ni Slack)

### 3. Actualizar 4 lugares con la nueva key

| Lugar | Acción |
|---|---|
| **Coolify env (backend producción)** | Dashboard Coolify → CRECE backend → Environment Variables → editar `SCRAPECREATORS_API_KEY` → Save → Restart container |
| **Vercel env (frontend si aplica)** | Dashboard Vercel → frontend project → Settings → Environment Variables → editar → Save → Re-deploy |
| **Local `.env` desarrollo** | `~/.config/last30days/.env` (machine-wide de Juan según HANDOFF-2026-04-17.md:2260) — coordinar con él |
| **CRECE local `.env`** | `~/Projects/crece-v2/backend/.env` si existe — actualizar |

### 4. Verificar funcionamiento

- Endpoint que usa la key: ejecutar smoke test
- Verificar logs Coolify post-restart sin errores 401/403 ScrapeCreators

### 5. Avisar a Linda para validación

Linda ejecutará en repo:
```bash
# Verificar que la key vieja no aparece en HEAD ni archivos tracked
git grep "pgmI0aOa8bSj9dUoh1Ja0OLwXTC2" 2>&1
# Debe retornar vacío

# Verificar que la key nueva tampoco aparece hardcoded (debe estar solo en env vars)
git grep "<primeros-8-chars-key-nueva>" 2>&1
# Debe retornar vacío
```

## Decisión sobre purga de history

**Opción A (recomendada): asumir comprometido + rotar suficiente.** La key vieja ya no funciona post-rotación. El riesgo residual = cargo no autorizado entre el momento del leak y la rotación, mitigable revisando billing ScrapeCreators.

**Opción B (alternativa): BFG repo-cleaner para purgar history completa.** Requiere force-push a TODAS las ramas que contengan el commit `821950b` (~3-5 ramas). Alta fricción operativa; cualquier fork/clone tendrá la key vieja igual. NO RECOMENDADA si la rotación es completa.

CEO debe firmar opción al cierre del proceso.

## Validación post-rotación

- [ ] Key vieja revocada en dashboard ScrapeCreators
- [ ] Key nueva generada
- [ ] Coolify env actualizado + container reiniciado
- [ ] Vercel env actualizado (si aplica) + redeploy
- [ ] Local `.env` actualizado
- [ ] Smoke test endpoint que usa la key → 200
- [ ] Linda verifica que key nueva no aparece hardcoded en repo
- [ ] CEO firma opción A o B sobre purga history
- [ ] Documentar cierre en `.context/DECISIONS.md` D-BR-1

## Lección preservada

Política Fase 4 (post recovery): **pre-commit hook con `git-secrets` o equivalente** para detectar secrets antes del commit. Esto NO se ejecutó cuando `821950b` se commiteó 18-abr ni cuando se identificó 26-abr — la rotación quedó documentada pero no ejecutada por 13 días.

Documentar en `CONTRIBUTING.md` Fase 4: **toda key de API se carga desde env var, nunca como default literal en código.**
