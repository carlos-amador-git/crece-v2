# PENDIENTES · CRECE v2 · al 2026-05-25 noche (pre-apagón)

**Snapshot tras 3 sprints del 2026-05-25 + F4 matriz polaridad.**
**Sesión Linda CRECE-electoral · branch `feat/post-ingest-hugo-2026-05-20`**

Para backlog técnico histórico (pre-mayo) ver `.context/BACKLOG.md`. Este archivo es snapshot operativo · NO histórico.

---

## A · Bloqueadores de cliente

Ninguno. App lista para piloto Saymi (id=3) y Pepe (id=57).

---

## B · Decisiones operativas pendientes CEO

### B1 · 57+ commits sin merge a `main`

5ta semana deployando vía `vercel deploy --prod` directo desde rama `feat/post-ingest-hugo-2026-05-20`. Funciona pero la divergencia crece. Decisión: ¿squash-merge a `main` o continuar así?

### B2 · Onboarding piloto Saymi/Pepe

¿Hay sesión agendada para mostrar el dashboard al cliente? Credenciales listas: `pineda@crece.mx` / `demo2026!` y `pmonroy@paz.mx` / `demo2026!`.

### B3 · Cleanup BD S-8.1

154 `watched_profiles` auto_suggested + 320 `watched_like_events` del E2E S-8.1 esperando orden CEO post-postmortem.

---

## C · Backlog técnico (sprint propio cada uno)

### C1 · PII compliance review · severity HIGH

Gap del audit-full 2026-05-19 Gemini cross-audit. Validar que perfiles sociales no se persisten/procesan con PII identificable. LFPDPPP.

### C2 · Performance N+1 stress test BFF

Endpoint `/posts/unified` con dataset realista (cliente real con 5K+ posts). Sin tests de carga hoy. Audit Gemini: HIGH.

### C3 · Error Boundaries frontend específicos

Si BFF cae 500, ¿app crashea o muestra fallback graceful? Validar y aplicar `<ErrorBoundary>` por sección. Audit Gemini: MEDIUM.

### C4 · Mobile audit completo

Más allá del fix sidebar contrast de hoy. Revisar TODAS las vistas en 360px/375px viewport.

### C5 · Tests pytest scripts LLM

- `regen_plan_dirigente.py` (Sprint F PLAN-2026-05-17 · diferido por LLM mocks complejos)
- `migrate_tono_v1_to_v2_saymi.py` (creado hoy · misma dificultad)

### C6 · Test Vitest applyVipOverrides

Requiere setup Vitest primero (no existe en frontend). Suite chica pero requiere infraestructura.

---

## D · Mejoras backlog (sin demanda real · OPCIONAL)

### D1 · "Contenido con más Impacto" REAL

Endpoint propio ORDER BY engagement_rate DESC con cap mínimo (>=5 likes). Hoy renombrado a "Publicaciones recientes" por honestidad. Cuando quieras crearlo:
- Nuevo endpoint backend `/api/v1/dirigentes/{id}/top_posts_by_engagement`
- Frontend cambia el query y restaura el título "Más Impacto"

### D2 · Backfill NLP enriquecido sobre POSTS

Granularidad 5 colores `tono_discurso`. Hoy hecho v1→v2 (7 categorías). Si se quiere finer-grained, sprint dedicado.

### D3 · Calendario INE distrital B17

Sprint S4 del MASTER. Solo si cliente pide veda electoral por distrito real (hoy es heurística keyword global).

---

## E · Blockers diferidos (estado conocido)

### E1 · B-COMPETIDORES-MODELO-1 · modelo huérfano

Tabla `competidores` + `competidor_social_profiles` existen pero NO conectadas al pipeline. Hoy benchmarking usa `dirigentes.competidor_directo_ids INT[]`. Pendiente decidir: deprecar tabla o renombrar a "directorio extendido".

### E2 · Bug #3B · save_count TT sin columna BD

Bookmarks TikTok están en `raw_data` pero no hay columna SQL. No urgente · solo si cliente pide bookmarks como métrica visible.

### E3 · 8 posts Saymi residuo v1 post-migración

De los 1,160 procesados en F4, quedaron 8 posts con tono v1 legacy (`neutral` 7 + `positivo` 1). 0.7% residuo. Si quieres 100% homogéneo, una corrida más con `--limit 20`.

### E4 · Threads activación cuenta

Diferido sprint 10 (Hugo D3 IG burner ya cerrado · este es distinto · Threads como plataforma propia).

---

## F · NO está pendiente (intencional · ya decidido)

| Item | Razón |
|---|---|
| Rotación `.env.scraping-keys` + filter-repo | CEO ratificó 2026-05-25: "no interesa por ahora" |
| B-IG-DATACENTER-IP-1 IG scraping | Descartado · RADAR cubre |
| B-META-APPREVIEW-1 Meta App Review | Diferido indefinido D-1.3 (sin caso de negocio) |
| Re-scrape TT métricas Saymi | NO necesario · datos en `raw_data` · UPDATE one-shot hecho hoy |

---

## Resumen ejecutivo

**Total operativo:** 2 decisiones tuyas (B1, B2) + 1 cleanup (B3) + 6 sprints técnicos (C1-C6) + 3 mejoras opcionales (D) + 4 estados conocidos (E).

**Nada bloqueante de demo cliente.** Si cliente entra hoy a la app, todo funciona.

**Próxima sesión recomendada:** B2 (onboarding piloto · prioridad comercial) o C1 (PII compliance · prioridad legal).
