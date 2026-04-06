# CRECE v2.0 — Status

## Estado: SCRAPERS REESCRITOS — 5 PLATAFORMAS INTEGRADAS
## Fecha: 2026-04-05

## Sprint actual: Scrapers reales (validado por Gemini)

### Resultados de pruebas (datos reales, ZERO mocks)

| Scraper | Librería | Funciona? | Bloqueante |
|---------|----------|-----------|------------|
| YouTube | scrapetube v2.6 | SI — 5 videos reales de Piña | Ninguno |
| Instagram | instaloader v4.15 | NO — 403 Forbidden | Requiere INSTAGRAM_USERNAME + PASSWORD |
| Twitter | twscrape | NO — 0 cuentas en pool | Requiere cuenta dedicada de X |
| Twitter | httpx syndication | NO — 429 Rate limit | Rate-limited o necesita proxies |
| Facebook | facebook_page_scraper v5 | NO — crash import | Bug selenium-wire (blinker._saferef) |
| TikTok | TikTok-Api v7.3.2 | No probado aún | Necesita Playwright |

### Cambios realizados esta sesión
1. pyproject.toml actualizado: facebook-scraper → facebook_page_scraper, TikTokApi >=7.3, scrapetube agregado
2. config.py: OLLAMA_MODEL cambiado a gemma3:12b
3. docker-compose.yml: OLLAMA_MODEL cambiado a gemma3:12b
4. CLAUDE.md: Reglas de calidad agregadas (no custom code, no mocks, librerías obligatorias)
5. Instrucciones Coolify para Carlos: .context/OLLAMA-COOLIFY-DEPLOY.md

### Próximos pasos (por prioridad)
1. Configurar credenciales Instagram (INSTAGRAM_USERNAME/PASSWORD)
2. Crear cuenta dedicada de X para twscrape
3. Fix facebook_page_scraper (downgrade blinker o usar alternativa)
4. Probar NLP sobre datos de YouTube obtenidos
5. Probar Voter Scoring fallback con seed data
6. Carlos: deploy Ollama en Coolify (instrucciones listas)

## Inventario (heredado de sesión anterior)

### Backend (105 archivos Python)
- 25 modelos, ~90 endpoints, 11 servicios
- 123 tests (119 green, 4 enum casing)
- Dual AI: Claude API + Ollama/Gemma3 local

### Frontend (80+ archivos TS/TSX)
- 16 páginas, 15 hooks React Query
- Build limpio, 0 errores TypeScript

### Docker
- PostgreSQL: 5438, Redis: 6383, MinIO: 9006/9007, Backend: 8002, Frontend: 3001
