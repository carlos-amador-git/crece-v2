# HANDOFF · sesión Linda · 2026-05-11 noche · EMERGENCIA luz

**Sesión que cierra:** Linda · peer `uji6x64w` · CRECE-electoral
**Razón cierre:** apagón de luz inminente en Mac del CEO · commit defensivo + push + handoff
**Branch:** `feat/phase-b-pesos-editables` · pusheado a `origin/`
**HEAD:** `a366d78`
**Última prod URL alive:** `frontend-zeta-sepia-46.vercel.app` · deploy `frontend-59sl3jo8c` (proyecto Vercel `frontend`, NO `crece-v2`)

---

## Lo que se completó hoy (2026-05-11)

### Sprint A · 5 fixes post-review CEO + anti-mock guardrail (commits `a817735` + `6d30fa5`)
1. P-03 Filtro red en Publicaciones Recientes (dropdown Todas/X/IG/FB/TT/YT)
2. P-04 FB/TT con followers_count=0 muestra "Sin datos · sync pendiente" (NO 0 engañoso)
3. P-02 Nuevo endpoint `/social/sentiment-coverage` + disclaimer "X de Y posts clasificados"
4. P-01 `CompetitorSnapshotCard` reescrito · usa `useKpiOverview` + `useBenchmarkRanking` reales · borrado mock 8.8K
5. P-05 **D-ANTI-MOCK-1**: `frontend/scripts/check-no-mocks.sh` + `CLAUDE.md` regla §5 + step en `.github/workflows/e2e-smoke.yml` "Anti-mock-data guardrail"

### Sprint B · Fix CSS barra Ballesteros invisible (commit `711f8eb`)
- `--chart-1` no existe en este theme (convención shadcn default no aplicada aquí)
- Cambiado a `--chart-accent` + `bg-accent/15` para badge MC

### Sprint C · Card B01 simplificada · metodología link interno (commit `0d58ee4`)
- Quitada jerga "Zenodo v1 · Nano X · Sprout Social · Rival IQ · IM commercial"
- Anchor `#er-mx` en metodología
- Link "Ver metodología en Configuración →" en B01

### Sprint D · /sprint-implement narrativa política B01-B10 (commits `e4b3fdf` + `88486ba` docs)
- Cross-audit Gemini: **GO con 3 ajustes** (Popover en lugar de Tooltip · diccionario defensivo B05 · empty states)
- 6 sprints según `.context/PLAN-2026-05-11-diagnostico-narrativa-politica.md`
- 10 cards reescritas con narrativa política
- Todas con icono ℹ️ Popover linkeando a metodología#b01-b10
- Tip educativo B10 movido a metodología#b10
- B03 "Esfuerzo Sin Retorno" warning explícito · B10 "Distante" explícito
- **Nueva dep:** `@radix-ui/react-popover@^1.1.15` (instalada · `package.json` + `package-lock.json` commiteados)
- **`D-NARRATIVA-1`** en `DECISIONS.md`

### Sprint E · WIP commit defensivo (commit `a366d78` actual HEAD)
Capturado sin pulir por apagón:
- `frontend/src/app/dashboard/page.tsx` +39 líneas (tsc verde)
- `frontend/src/app/dashboard/dirigentes/[id]/page.tsx` +87 líneas (tsc verde)
- `backend/scripts/classify_posts_gemma_coolify.py` cambios menores
- Docs `.context/` acumulados (planes 23-abr a 9-may + inventarios branches + research SMB)
- Backend scripts triangulación posts 2-way (cerrado D-DIAG-01)
- `docs/SECRET-ROTATION-2026-05-09.md`

⚠️ **AL RETOMAR:** revisar `git diff e4b3fdf..a366d78 -- frontend/` para entender qué se tocó en page.tsx y dirigentes/[id]/page.tsx en esta sesión post-deploy narrativa, decidir si esos cambios entran al mismo PR o se separan.

#### Análisis del WIP `a366d78` (hecho pre-apagón)

**`frontend/src/app/dashboard/page.tsx` (+33 −6) · MANTENER**
- Signal badges en 2 KPI cards del Overview · consistente con D-NARRATIVA-1
- Presencia Digital: Sobresaliente/Saludable/Mejorable/Crítico (umbrales >7/>5/>3/≤3)
- Tu Audiencia: Creciendo Fuerte/En Crecimiento/Estable/En Descenso (según change)
- Cambio puramente visual, cero riesgo backend
- Acción: squash con narrativa B01-B10 en PR único

**`frontend/src/app/dashboard/dirigentes/[id]/page.tsx` (+76 −11) · MIXTO**

Bloque 1 · Card IPD header enriquecido (subtitle + signal badge avg) · MANTENER. Consistente con narrativa.

Bloque 2 · Card "Sentimiento (30 días)" → REEMPLAZADA por "Resumen de Desempeño" · **NO MERGEAR SIN VALIDAR CEO**:
- Elimina SentimentLineChart del perfil dirigente — decisión UX no consensuada
- Umbrales hardcoded sin base (`total_engagement_7d > 5000` — ¿de dónde?)
- "Fortalezas/Oportunidades" son plantillas estáticas, no derivadas de matriz política 3-capas (D-NLP-01)
- Link "Ver Diagnóstico Full" → `/dashboard/diagnostico?dirigente={id}` — verificar si ruta funcional con ese query param
- Acción: pedir validación CEO antes de squash. Alternativa: revertir bloque 2 y mantener SentimentLineChart hasta que haya rediseño consensuado.

Bloque 3 · "Publicaciones Recientes" → renombrada "Contenido con más Impacto" + slice 3 · MANTENER con fix:
- Rename a "Contenido con más Impacto" OK (lenguaje político mejor)
- Slice a top 3 OK (jerarquía visual)
- Empty state OK
- **Hack a remover:** usa `<TabsList><TabsTrigger>` como link visual (sin ser tab funcional). Reemplazar por `<Link>` normal con la flecha.

**Resumen acciones próxima sesión:**
1. Squash bloques mantenibles con narrativa B01-B10 (signal badges Overview + IPD header).
2. Validar con CEO si SentimentLineChart se queda o se reemplaza por "Resumen de Desempeño" (con datos reales, no plantillas).
3. Reemplazar hack TabsTrigger por `<Link>` normal en sección "Contenido con más Impacto".
4. Verificar ruta `/dashboard/diagnostico?dirigente={id}` antes de habilitar el botón "Ver Diagnóstico Full".

---

## Estado pendiente · diferido a próximo sprint

### P-04b (data quality) — scraper Playwright profile-metrics FB+TT
**5 perfiles afectados:** Solano FB · Máynez FB+TT · Ballesteros FB+TT (handles válidos, scrapers no han poblado followers_count).
- HEAD requests confirmaron páginas existen (HTML title OK)
- Scraper requiere Playwright + cookies de sesión FB válidas
- Decisión 2026-05-11: no se corrió en sesión por riesgo en piloto activo
- UI mitigada (muestra "Sin datos · sync pendiente" con barra punteada)

### P-02b (data quality) — re-clasificación sentiment batch
Coverage actual (medido 2026-05-11 vía `/social/sentiment-coverage`):
- Ballesteros (id=8): 13.6% (32/236 últimos 30d)
- Solano (id=2): 20.0% (4/20)
- Piña (id=1): 52.7% (39/74)

UI mitigada con disclaimer "X de Y posts clasificados" cuando <80%. Para subir coverage, correr re-clasificación batch con NLP v3.

### Diferidos del /sprint-implement narrativa (rediseños mayores)
- B03 matriz 2×2 "Lo que funciona / Lo que te daña" (vs scatter actual)
- B08 gauge en lugar de pie chart
- B07 excerpt real del post (requiere `content_preview` en schema B07 backend)

---

## Para retomar después del apagón

### Comandos exactos al volver
```bash
cd ~/Projects/crece-v2
git status                                        # debe estar limpio si fue todo pusheado
git log --oneline -8                              # confirmar HEAD = a366d78
cat .context/HANDOFF-2026-05-11-pre-apagon.md     # esto que estás leyendo
cat .context/STATUS.md | head -100                # estado oficial
cat .context/DECISIONS.md | head -120             # D-NARRATIVA-1 y D-ANTI-MOCK-1 recientes
git diff e4b3fdf..a366d78 -- frontend/            # ver qué quedó WIP no pulido
docker ps | grep crece                            # backend local Mac Mini
curl -s http://localhost:4040/api/tunnels | head  # ngrok activo? URL actual?
```

### Verificaciones obligatorias antes de seguir
1. **Confirmar ngrok URL activa** == `BACKEND_TUNNEL_URL` en Vercel (`vercel env pull /tmp/x.env --environment=production`).
   - Si ngrok cambió tras restart Mac → actualizar Vercel env var + redeploy.
2. **Confirmar alias prod** apunta a `frontend-59sl3jo8c` o más reciente: `vercel inspect frontend-zeta-sepia-46.vercel.app`.
3. **`.vercel/project.json` debe decir `projectName: "frontend"`** (no `crece-v2` — incidente 2026-05-11 redirige a project equivocado).
4. **Antes de cualquier `vercel deploy`:** `cat frontend/.vercel/project.json` para confirmar.
5. **Antes de cualquier card nueva en diagnóstico:** debe pasar `npm run check:no-mocks` (D-ANTI-MOCK-1 enforced en CI).

### Próximo paso recomendado al volver
1. **Validación visual CEO** en prod del trabajo narrativa B01-B10 (no validó aún el último deploy `frontend-59sl3jo8c`).
2. Decidir qué hacer con WIP en `a366d78` (page.tsx + dirigentes/[id]/page.tsx no descritos en commit · 87+39 líneas no pulidas).
3. Sprint próximo (§9.8 ≈ 2026-05-20): elegir entre P-04b, P-02b, B03 matriz, B08 gauge, B07 excerpt.

---

## Credenciales útiles
- Login admin: `admin@consultoriamd.com` / `crece2026!`
- Login viewer: `pina@crece.mx` / `solano@crece.mx` / `ballesteros@crece.mx` → password `demo2026!`
- Auth tiene rate limit: 5/min · si pega rate, esperar 60s antes de reintentar

## Contexto pendiente que el CEO mencionó pero no se completó
- "Vamos a dejar por el momento tanto overview como dirigentes" — no fusionar/borrar rutas, decisión 2026-05-11
- "El indice de aceptación es distinto" — overview vs dirigentes/[id] son redundantes para VIEWER pero NO tocar
- "Linda" es el nombre asignado a esta sesión (peer uji6x64w)

## Notas operativas
- Backend local Mac Mini puerto 8002 · ngrok tunnel para Vercel proxy
- **Coolify (`crece.mdconsultoria-ti.org` + `api-crece.mdconsultoria-ti.org`) = DEMO/showcase · Vercel + Mac Mini = PILOTO operativo (Solano · Piña · Ballesteros).** Roles distintos, NO duplicación. Coolify NO se apaga · se mantiene actualizado para presentaciones. Mandato CEO 2026-05-11: *"eso es lo que estuvo mal. No era tener dos pilotos. Solo el de Vercel"* + *"Coolify si es para mostrar"*. Ver `~/.claude/projects/-Users-marxchavez-Projects-crece-v2/memory/reference_coolify_alive_2026_05_11.md`.
- Prod URL única del PILOTO: `frontend-zeta-sepia-46.vercel.app`
- Si Mac queda totalmente apagada, el piloto cae → frontend Vercel mostrará "Failed to fetch". Esa es la consecuencia aceptada · NO usar Coolify como fallback del piloto (Coolify tiene su propia BD demo, no espejo del piloto).
- CI guardrail anti-mock instalado en `.github/workflows/e2e-smoke.yml` step "Anti-mock-data guardrail (D-ANTI-MOCK-1)"

## Acción pendiente con Carlos Amador
**Instrucción para mandarle cuando se confirme deploy demo (NO ejecutar sin OK CEO):**
> "Hola Carlos · sobre Coolify (demo) · hay narrativa nueva del día en `feat/phase-b-pesos-editables`.
>
> Cuando puedas:
> 1. Branch: `feat/phase-b-pesos-editables` · commit estable: **`88486ba`** (NO el HEAD que tiene WIP `a366d78` sin validar).
> 2. Frontend: `cd frontend && npm ci` (dep nueva: `@radix-ui/react-popover`) + `npm run build`.
> 3. Backend: rebuild (endpoint nuevo `/social/sentiment-coverage`). Sin alembic migration nueva.
> 4. Cuando termines, ping para que CEO valide demo.
>
> Las cuentas demo de Coolify (BD propia VPS) quedan como están — no migrar nada del piloto."

NO confundir roles: Coolify es demo, no fallback del piloto. Si Coolify queda desactualizado vs piloto, la acción correcta es **actualizar**, NO apagar.

---

**Sesión Linda cerrando aquí. Próxima sesión retoma desde este archivo + STATUS.md.**
