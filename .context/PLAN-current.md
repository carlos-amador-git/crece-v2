# CRECE v2.0 — Sprint: Scrapers Reales + Corrección de Librerías
## Estado: EN EJECUCIÓN
## Fecha: 2026-04-05
## Validado por: Gemini cross-audit (aprobado con observaciones)

---

## Contexto
El CEO detectó que se escribió código custom en vez de usar las librerías del plan original.
Las reglas de calidad están actualizadas en CLAUDE.md.
Patrón de resiliencia: Librería → Custom fallback → Apify.

## Sprint 1: Probar Instagram scraper con datos reales (30 min)
**Objetivo:** Ejecutar instaloader contra @alejandro.pinha y obtener posts reales.
**Archivos:** `backend/app/scrapers/instagram.py`
**Criterio:** Posts reales de Piña en la BD. Cero mocks.
**Dependencias:** Docker up (PostgreSQL), instaloader instalado.
**Plan:**
1. Verificar que instaloader está instalado en el venv/container
2. Escribir script de prueba que use instaloader directamente (no el wrapper custom)
3. Ejecutar contra @alejandro.pinha (perfil público)
4. Si funciona → evaluar si el wrapper actual agrega valor o solo complejidad
5. Si falla → documentar error exacto, proponer alternativa

## Sprint 2: Probar Twitter scraper con datos reales (30 min)
**Objetivo:** Ejecutar twscrape/httpx contra @Alejandro_Pinha.
**Archivos:** `backend/app/scrapers/twitter.py`
**Criterio:** Tweets reales o diagnóstico claro de por qué falla.
**Dependencias:** Sprint 1 no bloquea este.
**Plan:**
1. Probar httpx fallback (syndication endpoint, no requiere auth)
2. Si funciona → tenemos datos de Twitter sin configuración extra
3. Si falla → documentar, evaluar twscrape con cuenta auth
4. Evaluar scrapetube para YouTube como bonus

## Sprint 3: NLP sobre posts reales (30 min)
**Objetivo:** Ejecutar pysentimiento + spaCy sobre posts obtenidos en Sprint 1-2.
**Archivos:** `backend/app/nlp/analyzer.py`
**Criterio:** Sentiment scores reales, no de seed data.
**Dependencias:** Sprint 1 o Sprint 2 debe tener posts.
**Plan:**
1. Tomar posts reales de BD (de Sprint 1/2)
2. Ejecutar NLPAnalyzer.analyze() contra cada post
3. Verificar que modelos se cargan (primera vez lento)
4. Guardar resultados en SocialPost (sentiment_score, sentiment_label)

## Sprint 4: Voter Scoring fallback (20 min)
**Objetivo:** Ejecutar voter scoring rule-based con datos seed.
**Archivos:** `backend/app/services/voter_scoring.py`
**Criterio:** Scores calculados para los 5 ciudadanos del seed.
**Dependencias:** Ninguna.
**Plan:**
1. Ejecutar score_all() vía endpoint o script directo
2. Verificar que el fallback rule-based produce scores coherentes
3. Documentar: cuántos ciudadanos hay, qué scores produce

## Sprint 5: Corregir dependencias y actualizar plan (20 min)
**Objetivo:** Actualizar pyproject.toml con librerías correctas.
**Archivos:** `backend/pyproject.toml`
**Criterio:** Dependencias alineadas con plan corregido.
**Plan:**
1. Agregar scrapetube>=2.6.0
2. Reemplazar facebook-scraper por facebook_page_scraper
3. Actualizar TikTokApi a >=7.3.0
4. Documentar resultados de todos los sprints en STATUS.md

---

## Riesgos identificados (Gemini cross-audit)
- CRITICAL: IPs de datacenter bloqueadas por Meta/X (no aplica hoy, pruebas son locales)
- HIGH: Threads y Telegram no cubiertos (Fase 2+)
- MEDIUM: Facebook Capa 2 necesita Playwright, no httpx
- Proxies residenciales necesarios para producción (~$25-75/mes)

## Decisión de hoy
Probar local (Mac del CEO) donde no hay problema de IPs.
Si los scrapers funcionan local → después resolvemos Coolify + proxies.
