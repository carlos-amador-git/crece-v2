# BACKLOG · CRECE v2

Tickets diferidos con contexto para retoma.

---

## Scraping (post-F1.1, requieren Joy)

### B-SCRAPE-01 · Fix stack scrapers · exitcode 1 en rescrape

**Origen:** sesión 2026-04-24 · intento scraping Máynez (id=7) falló 5 plataformas · 0 posts ingestados · reporte completo en `.context/SCRAPING-MAYNEZ-2026-04-24.md`.

**Bugs simultáneos identificados:**

1. **Twitter** · nested asyncio · `asyncio.run() cannot be called from a running event loop` en `app/scrapers/twitter.py:164, 201, 613` · afecta Scweet + twscrape. Hipótesis: Python 3.12+ en container post-rebuild, más estricto con nested event loops.
2. **Instagram** · `ensta 5.2.9` devuelve `None` contra perfiles verificados (login-wall sin JSON embedido) · fallback `instaloader` sin `INSTAGRAM_USERNAME`/`INSTAGRAM_PASSWORD` env vars.
3. **Facebook** · `webdriver-manager 4.0.2` baja chromedriver v114 legacy (URL Google Storage deprecated) · mismatch con chromium container v120+ · SIGSEGV.

**Datos pre-existentes para restauración:**
- `curl-cffi` extrajo 1 post FB sin Selenium · evidencia que el parser básico funciona · rumbo posible es remover dependencia Selenium del FB scraper.

**Requisitos:**
- Requiere Joy (revisor scrapers)
- Requiere post-F1.1 (reprocess_nlp se activa solo tras schema restaurado)
- Considerar configurar `INSTAGRAM_USERNAME`/`PASSWORD` burner en `.env.coolify.example` si se decide quedarse con `instaloader`

**Criterio de éxito:** Máynez + los 4 shadow MORENA + Piña + Ballesteros + Solano vuelven a scrapear sin exit 1 · ≥20 posts por plataforma activa · tests regression agregados.

---

### B-SCRAPE-02 · Decisión pipeline manual Chrome+IA vs stack interno

**Origen:** sesión 2026-04-24 · dos intentos con aproximaciones distintas y ambos tuvieron problemas:

| Approach | Experiencia |
|---|---|
| Chrome + Claude AI manual (Cravioto 2026-04-23) | Output JSON no alineado con ORM `SocialPost` · 6 decisiones de mapping necesarias · falso negativo IG (`@cesarcravioto` existe pero no probó ese handle) |
| Stack interno (Máynez 2026-04-24) | 5 bugs runtime paralelos · 0 posts ingestados · exit 1 |

**Pregunta de diseño:** ¿dedicar esfuerzo a fixear stack interno (B-SCRAPE-01) o formalizar pipeline manual con contract?

**Costos a evaluar:**
- Stack interno: mantenimiento de ~6 libs (Scweet, twscrape, ensta, instaloader, curl-cffi, Selenium) · rate limits · fingerprinting · CI regression check
- Manual con contract: dependencia operativa de sesión humana/agente para cada scrape · latencia · inconsistencia entre corridas
- Híbrido: stack interno para shadows rutinarios · manual para onboarding nuevo (Máynez) o cuando stack falla

**Requisitos:**
- Sesión dedicada con análisis costo/beneficio
- Considerar integración con Apify/Brightdata pagados (ya hay credenciales parciales en `.env`) como tercera opción
- Output: decisión documentada en MASTER + tickets consecuentes

---

### B-SCRAPE-03 · Monitoreo salud scrapers · regression check

**Origen:** sesión 2026-04-24 · el script `scrape_new_dirigentes.py` funcionó en 2026-04-11 con 4 shadow MORENA y falló en 2026-04-24 con Máynez · no había forma de saber que el stack se había roto hasta intentarlo en caliente.

**Entregables propuestos:**
- Cron diario (o semanal) que ejecute smoke scraping contra 1 dirigente con datos conocidos · alerta webhook Discord si `0 new posts` contra expectativa
- Test integration por plataforma · mock de respuestas HTTP conocidas para validar parsers
- Dashboard mínimo en `/dashboard/admin/scraping-health` · última corrida por plataforma · éxito/fallo · posts ingestados

**Requisitos:**
- Post-B-SCRAPE-01 (que haya stack funcional primero)
- Consumo mínimo de rate limits (shadow rotatorio · 1 plataforma × 1 dirigente × día)

---

## Schema (estructurales · §9.8)

### B-SCHEMA-01 · Agregar columna `social_profiles.verification_note`

**Origen:** sesión 2026-04-24 · CEO propuso columna textual para registrar razón de verificación manual (ej. Cravioto IG post-falso-negativo Chrome AI). La columna no existe · se creó `.context/HANDLES-VERIFICATIONS-2026-04-24.md` como SSOT temporal.

**Propuesta:** `verification_note TEXT` en `social_profiles` · poblar desde `HANDLES-VERIFICATIONS-2026-04-24.md` al migrar.

**Requisitos:** §9.8 revisor · D-OPS-10 · incluir en misma ventana que F1.1 si aplica.

---

## Housekeeping

(agregar tickets aquí cuando surjan)
