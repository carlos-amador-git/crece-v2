# PLAN · pendientes post-reunión 2026-05-11

**Origen:** revisión CEO 2026-05-11 sobre frontend en producción (Ballesteros como VIEWER).
**Mandato:** *"Haz un plan y resuelvelos. Verifica que esto no vuelva a ocurrir."*
**Sesión:** Linda · branch `feat/phase-b-pesos-editables` · HEAD `1aa9ca1`

---

## Pendientes detectados

| # | Pendiente | Causa raíz | ETA |
|---|---|---|---|
| P-01 | `CompetitorSnapshotCard` muestra **8.8K** mock cuando el real es 89.8K | `DIRIGENTE_METRICS_FALLBACK` hardcoded · nunca cableado a `/benchmark/ranking` | 2-3h |
| P-02 | Gráfica "Tono Discursivo" muestra muy pocos posts | Filtros >20 chars + sin RT + por día; coverage OK (83.8%), distribución desigual | 1h |
| P-03 | "Publicaciones Recientes" sin filtro por red | UI no expone selector aunque hook ya soporta `platform` | 20 min |
| P-04 | Ballesteros FB+TT con métricas en 0 (y Solano FB · Máynez FB+TT) | Scraper de profile-metrics no corrió o falló · `last_scraped_at` null en 4/5 casos | 30-60 min |
| **P-05** | **Anti-recurrencia · que no se vuelva a colar mock-data o desincronización** | No hay guardrail · regla de CLAUDE.md "NUNCA mocks" no se valida en CI | 1h |

ETA total: ~5h

---

## Sprint 1 · P-03 · Filtro red en Publicaciones Recientes (20 min)

**Acción**
- En `frontend/src/app/dashboard/page.tsx:546-566`, añadir `<select>` igual al de Tono Discursivo (`l497-510`) con state local `recentPlatformFilter`.
- Pasar `platform: recentPlatformFilter || undefined` al hook `useSocialPosts({ per_page: 5, platform: ... })`.
- Verificar visualmente: Todas / Twitter / IG / FB / TT / YT filtra los 5 cards.

**Criterio aceptación**
- Selector visible, default "Todas las redes", cambia los 5 cards al instante.
- Tests existentes siguen pasando.

---

## Sprint 2 · P-04 · Auditar y re-scrapear FB+TT zeroed (30-60 min)

**Acción**
1. Confirmar handles válidos haciendo HEAD request (`curl -I`) o `playwright` quick check a:
   - https://facebook.com/LauraBallesterosMX
   - https://tiktok.com/@lauraballesterosmx
   - https://facebook.com/RafaSolanoPerez
   - https://facebook.com/AlvarezMaynez
   - https://tiktok.com/@alvarezmaynez
2. Si cuenta existe pública: re-correr scraper de profile-metrics (`backend/app/scrapers/facebook.py` `tiktok.py`) en modo "solo profile metrics" (no posts). Comando: `python -m app.scripts.scrape_profile_only --dirigente-id 8 --platform FACEBOOK`.
3. Si cuenta no existe / privada: `UPDATE social_profiles SET is_active=false WHERE ...` y actualizar UI para no mostrar la barra en 0 sino "no aplica".
4. Confirmar nuevos `followers_count` > 0 o flag inactivo.

**Criterio aceptación**
- Card "Seguidores por Plataforma" en `/dashboard` ya no muestra "0" engañoso para Ballesteros.
- Misma vista para Solano y Máynez si las cuentas existen.
- Si la cuenta no existe, la barra desaparece (no aparece como "0").

---

## Sprint 3 · P-02 · Auditoría coverage Tono Discursivo (1h)

**Acción**
1. Query diagnóstico por dirigente:
   ```sql
   SELECT sp.dirigente_id, d.full_name,
     COUNT(*) total,
     COUNT(*) FILTER (WHERE p.sentiment_score IS NOT NULL) con_sentiment,
     COUNT(*) FILTER (WHERE p.sentiment_score IS NOT NULL AND length(p.content) >= 20 AND NOT p.content LIKE 'RT @%') paso_filtros,
     COUNT(*) FILTER (WHERE p.published_at >= NOW() - INTERVAL '30 days') ultimos_30d
   FROM social_posts p
   JOIN social_profiles sp ON p.profile_id=sp.id
   JOIN dirigentes d ON sp.dirigente_id=d.id
   GROUP BY sp.dirigente_id, d.full_name;
   ```
2. Si para Ballesteros (dirigente 8) hay menos de ~50 posts que pasan filtros en 30d, entonces la gráfica está rota visualmente porque el dataset es escaso.
3. Decisión:
   - **Opción A:** mantener filtros estrictos y poner CTA "Faltan datos · clasifica X posts pendientes" cuando dataset < umbral.
   - **Opción B:** relajar filtros (incluir RT como "neutro" o bajar chars a >10).
   - **Opción C:** mostrar disclaimer "muestra reducida · N posts cumplen criterios de calidad" debajo del título.
4. Implementar la opción elegida en `SentimentLineChart` o en el card que lo envuelve.

**Criterio aceptación**
- Usuario entiende que la barra alta del 17/4 es real (no error), y que los días vacíos = sin posts que pasen filtros (no = sin actividad).

---

## Sprint 4 · P-01 · CompetitorSnapshotCard real (2-3h)

**Acción**
1. Backend: extender `/benchmark/ranking` (o crear `/benchmark/comparison?dirigente_id=X`) que devuelva:
   ```json
   {
     "dirigente": {"nombre":"Laura Ballesteros","partido":"MC","followers":89800,"engagement":3.2,"sentiment":0.42},
     "competidores": [
       {"nombre":"Marti Batres","partido":"MORENA","followers":285000,"engagement":1.8,"sentiment":-0.12}
     ]
   }
   ```
   - Dirigente data: sumar `social_profiles.followers_count` agrupado por `dirigente_id`. Engagement y sentiment desde último período de 30d.
   - Competidores: usar `competidor_social_profiles` real. Filtrar por org del dirigente (si Solano CDMX → competidores CDMX).
2. Frontend: nuevo hook `useBenchmarkComparison(dirigenteId)` en `frontend/src/lib/api/hooks/use-benchmark.ts`. Reemplazar el FALLBACK estático por la respuesta del hook.
3. Borrar `DIRIGENTE_METRICS_FALLBACK` y `DEMO_COMPETITORS` del componente. Loading state con Skeleton.
4. Validar: Laura Ballesteros real ≈ 89.8K (no 8.8K). Batres real ≈ 285K. Si Taboada en BD es 198K (no 142K mock), aceptarlo — es el real.

**Criterio aceptación**
- Card muestra 89.8K para Laura.
- Datos coinciden con `/dashboard` Tu Audiencia (mismo cálculo, mismo número).
- Cero strings hardcoded en el componente.

---

## Sprint 5 · P-05 · Anti-recurrencia · guardrails (1h)

**Causa raíz del problema:** la regla *"NUNCA mocks o datos inventados"* de `CLAUDE.md:l25` no se valida programáticamente. Cualquier sprint puede meter un placeholder con `// TODO: replace later` y se quedará indefinidamente.

**Acción · 3 capas de defensa**

### 5.1 Test de integridad UI ↔ BD
- Nuevo `frontend/tests/integration/no-hardcoded-metrics.spec.ts`:
  - Login como Ballesteros viewer.
  - Snapshot `Tu Audiencia` y `vs Competidor → Laura`.
  - **Assert que ambos números son iguales** (tolerancia ±5%).
  - Cualquier mock futuro rompería esta aserción al cambiar el valor del competidor sin que cambie el del KPI.

### 5.2 Lint rule (grep en CI)
- Añadir a `frontend/.eslintrc.json` o como `scripts/check-no-mocks.sh`:
  - Regex que falla si encuentra patrones sospechosos en `frontend/src/**/*.tsx`:
    - `_FALLBACK\s*=\s*\{[^}]*followers:\s*\d{3,}`
    - `// Placeholder` cerca de números literales `\d{4,}`
    - `// TODO: replace.*API`
  - Conectado al hook pre-commit existente.

### 5.3 Convención documentada
- Update `CLAUDE.md` del proyecto: añadir bullet en sección "Reglas de Calidad":
  > "Si un componente necesita data antes que el endpoint backend esté listo, NO usar hardcoded fallback. En su lugar, mostrar `<Skeleton />` indefinido + log a Sentry/console. Cero números falsos visibles al usuario."
- Update `.context/DECISIONS.md` con `D-ANTI-MOCK-1` documentando el incidente como evidencia.

**Criterio aceptación**
- `npm run lint` o `pnpm lint` falla si alguien re-introduce un patrón mock-data.
- Test integration verde con datos reales, rojo si hay mock.
- CLAUDE.md actualizado con la regla operativa.

---

## Orden de ejecución y por qué

1. **Sprint 1 (P-03)** primero — quick win 20 min, valida que el flujo de cambios sigue funcionando.
2. **Sprint 2 (P-04)** segundo — data quality urgente, afecta lo que la audiencia ve.
3. **Sprint 3 (P-02)** tercero — diagnóstico antes que código.
4. **Sprint 4 (P-01)** cuarto — el más grande, ya con contexto cargado.
5. **Sprint 5 (P-05)** último — guardrails sobre todo lo anterior.

Cada sprint = 1 commit independiente. Reporte al cierre de cada uno.

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Sprint 2: cuenta FB/TT realmente cerrada → no se puede re-scrapear | Marcar `is_active=false` y ocultar barra. No engañar con 0. |
| Sprint 4: endpoint `/benchmark/comparison` necesita schema nuevo | Usar `/benchmark/ranking` existente y filtrar en frontend si no hay tiempo de extender backend. |
| Sprint 5: lint rule da false positives en código legítimo | Acotar la regex a `_FALLBACK` específico, no a cualquier número. Iterar si bloquea. |
| Romper algo en producción (Vercel) | Cada sprint commit-able y revertible. Smoke E2E al cierre antes de push a main. |
