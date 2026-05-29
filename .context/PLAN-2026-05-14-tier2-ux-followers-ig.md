# PLAN · 2026-05-14 · Tier 2 UX refactor + Followers IG vía proxy

## Origen

1. **Review externo CEO 2026-05-13 noche** sobre dashboard "Diferenciadores Tier 2" (cards B11-B18). Reproducido literal abajo.
2. **Bloqueo descubierto en vivo 2026-05-13**: Instagram bloquea queries desde IP de datacenter — sesión de chatmx_oficial autenticada NO puede consumir API (`@instagram` mismo retorna `ProfileNotExistsException`). Memoria de proyecto ya lo había documentado para YT/TikTok; ahora confirmado para IG.

---

## Sprint A · Refactor visual Tier 2 (~2.5h)

### Hallazgos del review (fuente: CEO + Gemini, 2026-05-13)

#### Lo que ya es "oro puro" (preservar)

- Subtítulo de la pantalla: "Lo que ni Brandwatch ni Meltwater calculan" — golpe de autoridad, no tocar.
- Card B13 (Reality Filter): separa orgánico de inauténtico — función killer.
- Códigos `B11/B12...` + `conf 0.50` — aire de herramienta científica, mantener.

#### Mejoras concretas a implementar

1. **Carga cognitiva (densidad de texto):**
   - Notas técnicas tipo "Jaccard sobre captions cortos…" mover a tooltip / popover (patrón ya usado en Tier 1 B-NARRATIVA-1).
   - Solo el "Hallazgo Principal" visible por defecto.
   - **Esfuerzo:** ~45 min (popover wrap por card).

2. **Jerarquía de alertas en B14** ("¿Tu audiencia habla de lo que publicas?"):
   - Bloque rojo abajo compite con advertencia naranja arriba.
   - Si "Detector en calibración" → toda la card en estado disabled / overlay semitransparente.
   - **Esfuerzo:** ~20 min.

3. **Grid rojo de B14 (visualización):**
   - No queda claro qué representan los cuadros.
   - Agregar leyenda + etiquetas de eje (ej: "cada cuadro = 1 post · color = mismatch audiencia").
   - **Esfuerzo:** ~30 min.

4. **Botón "Activar Filtro" del Reality Filter:**
   - Hoy escondido arriba derecha.
   - Convertir en **switch global prominente** que cambie el modo de toda la página a "Safe/Organic" (overlay de color + indicador en sidebar).
   - **Esfuerzo:** ~30 min.

5. **Empty state de B16** (Rastreador Promesas):
   - "Datos insuficientes" → cambiar por CTA accionable "Registrar primera promesa ahora" (link a `/dashboard/contenido` o panel admin).
   - **Esfuerzo:** ~10 min.

6. **B17 Cumplimiento Veda Electoral:**
   - Cuando veda esté activa: borde de tarjeta rojo/naranja intenso + indicador animado (`animate-pulse`).
   - Hoy el badge "Puede publicar" es suficiente para estado verde; el delta visual entrega solo en estado rojo.
   - **Esfuerzo:** ~20 min.

7. **B18 Violencia Política:**
   - Si el % sube, mostrar tags automáticos categorizados (insultos / amenazas / violencia de género).
   - Requiere clasificador NLP adicional sobre comments marcados → **diferido a sprint NLP** (no aplica este sprint UI).
   - **Esfuerzo este sprint:** 0 (sólo registrar B-VIOLENCIA-TAGS-1 en BLOCKERS).

8. **Agrupación visual por "zonas de riesgo":**
   - Zona 1 Autenticidad (B11, B12, B13) — "¿Es real lo que pasa?"
   - Zona 2 Narrativa (B14, B15, B16) — "¿Estamos comunicando bien?"
   - Zona 3 Legal/Riesgo (B17, B18) — "¿Estamos seguros?"
   - **Implementación:** wrapper `<section>` por zona con título + descripción corta + grid interno. CSS Grid 2-column responsive.
   - **Esfuerzo:** ~30 min (es el cambio más alto-impacto).

### Criterios de aceptación

- [ ] Screenshot before/after Playwright de cada card refactorizada.
- [ ] tsc clean + `npm run check:no-mocks` verde.
- [ ] CEO valida en Vercel staging antes de cerrar.

### Tiempo total Sprint A: ~3h

---

## Sprint B · Followers IG vía proxy residencial (~2.5h)

### Contexto del bloqueo

Sesión 2026-05-13: login `soporte@consultoriamd.com.mx` → IG aceptó credenciales pero `Profile.from_username` retorna `ProfileNotExistsException` incluso para `@instagram` (cuenta oficial). Diagnóstico: IG bloquea queries desde IP de datacenter (Mac Mini Coolify probablemente también). Confirmado patrón documentado para YT/TikTok en `reference_brightdata_residential.md`.

### ⚠️ Update 2026-05-13 noche · Apify sin crédito

CEO confirmó que el free tier Apify de este ciclo está agotado (`B-APIFY-CREDIT-EXHAUSTED-1`).
Camino 2 (Apify Actor) **no es viable hasta renovación del ciclo mensual**. Caminos $0 reales esta semana:
- Mover scrapers al host Mac Mini (IP residencial, evita datacenter block).
- Brightdata residential proxy via `BRD_API_TOKEN` (free dentro de cuota).
- Scrapling v2 para X ($0 puro, ya validado).

### Caminos viables (revisado · Apify out por ahora)

#### Camino 1 · Brightdata Web Unlocker (1.5h) — RECOMENDADO sin Apify

- `BRD_API_TOKEN=bc52cf16-...` ya en `backend/.env`.
- Configurar `instaloader.Instaloader.context._session.proxies` para rutear vía `brd.superproxy.io:22225`.
- Validar con: `Profile.from_username(L.context, 'instagram')` debe retornar followers >0.
- Después: `chatmx_oficial.get_followers()` (límite 50 para test).

**Pros:** ya hay token, $0 incremental dentro de cuota mensual.
**Contras:** Brightdata residential consume ancho de banda — typical $1-3 por 1000 requests.

#### Camino 2 · Apify Instagram Profile Scraper (1h)

- `APIFY_TOKEN=apify_api_eG89F2BGegEPSHrnBOTlbwwILRswuF3obKC9` ya en `backend/.env.scraping-keys` (NO cargado al container actualmente).
- Wire al docker-compose: agregar `env_file` adicional o mover token a root `.env`.
- Actor `apify/instagram-profile-scraper` → input `{username: "chatmx_oficial", resultsLimit: 50}` → output JSON con followers.

**Pros:** Apify gestiona proxy + retry internamente, código más simple.
**Contras:** Actor de followers específicos puede ser de pago. Verificar antes (`apify/instagram-followers-scraper` cuesta ~$3.50/1k).

### Implementación scaffold (común a ambos caminos)

Archivo nuevo: `backend/app/scrapers/instagram_privileged.py` (paralelo a `youtube_privileged.py`).

```python
class InstagramPrivilegedScraper:
    def __init__(self, profile_handle: str, *, use_proxy: bool = True): ...
    async def login(self) -> None: ...
    async def get_followers(self, limit: int = 50) -> list[dict]: ...
    async def get_recent_posts(self, limit: int = 10) -> list[dict]: ...
    async def get_post_comments(self, shortcode: str) -> list[dict]: ...
    async def upsert_followers(self, db, items) -> int: ...
    async def record_comment_engagements(self, db, posts, comments) -> int: ...
```

Diferencias clave vs `youtube_privileged.py`:
- No usa `OAuthTokenByPlatform` (IG sin OAuth real hasta Meta App Review). Usa credenciales `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD` directas.
- `source='scraper_auth'` en `social_followers` (no `'oauth'`).
- Marca tokens "session-based" con TTL más corto (24h) para forzar re-login frecuente.

### Criterios de aceptación

- [ ] Login funciona via proxy (CEO confirma en logs).
- [ ] `get_followers(limit=50)` retorna ≥1 fila real para `chatmx_oficial`.
- [ ] Cross-reference con commenters: si algún follower comentó algún post → `follower_engagement` insertado.
- [ ] UI `/dashboard/seguidores` muestra "X followers IG · Y han comentado".

### Riesgos

- IG puede dar checkpoint challenge incluso por proxy (cuenta nueva en IP nueva). **Mitigación:** acceso al inbox `soporte@consultoriamd.com.mx` confirmado por CEO.
- Costo Brightdata/Apify si abusamos rate. **Mitigación:** límite 50 followers + 10 posts en este sprint.

### Tiempo total Sprint B: ~2.5h

---

## Sprint C · Vercel deploy + UI validación followers YT (~30 min)

Pendiente del 2026-05-13:

- [ ] `cd frontend && vercel deploy --prod` (CEO debe autenticar `vercel login` primero si no lo está).
- [ ] Validación visual: login como Piña en Vercel → `/dashboard/seguidores` → ver `benjamin jimenez · YouTube · 0 comments`.
- [ ] Test con OAuth real (re-conectar tu YT si token expiró).

---

## Orden recomendado de ejecución

1. **Sprint C primero (30 min)** — desbloqueo visual, baja inversión. Confirma que pipeline OAuth→BD→API→UI cierra.
2. **Sprint B (2.5h)** — habilita Instagram (la red con más data Saymi-style). Camino 2 (Apify) más simple, recomendado.
3. **Sprint A (3h)** — UX refactor Tier 2, mayor impacto pero el más largo. Hacer al final con energía fresca.

Total: ~6h. Sesión completa.

---

## Anexo · Review CEO + Gemini 2026-05-13 (literal)

> **Pantalla "Diferenciadores Tier 2"**
>
> Esta pantalla es el corazón técnico de CRECE. Aquí es donde se separan de herramientas comerciales como Brandwatch o Meltwater.
>
> **Lo que es "Oro Puro":**
> - Narrativa de Valor: subtítulo "Lo que ni Brandwatch ni Meltwater calculan" es golpe de autoridad.
> - Filtro de Realidad: tarjeta B13 separa orgánico de inauténtico.
> - Transparencia IA: códigos B11, B12 + conf 0.50 → aire de herramienta científica.
>
> **Oportunidades de Mejora:**
> 1. Carga cognitiva: notas técnicas → tooltip.
> 2. Jerarquía de alertas en B14: estado desactivado cuando calibrando.
> 3. Grid rojo B14: leyenda explicativa.
> 4. Botón Reality Filter: switch global prominente.
> 5. Empty state B16: CTA "Registrar primera promesa ahora".
>
> **B17 Veda Electoral:** badge "Puede publicar" OK; si veda activa → borde rojo intenso.
>
> **B18 Violencia Política:** si % sube → categorizar (insultos / amenazas / violencia de género).
>
> **Recomendación final:** agrupar B11-B18 en 3 zonas (Autenticidad / Narrativa / Legal-Riesgo).
