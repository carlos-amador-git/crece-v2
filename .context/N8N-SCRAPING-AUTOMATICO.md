# Instrucciones para Carlos — Activar Scraping Automático en n8n

## Contexto
CRECE v2 tiene scrapers funcionales para 6 plataformas (Twitter, Instagram, Facebook, TikTok, YouTube, Bluesky). Actualmente se ejecutan manualmente. Necesitamos que corran automáticamente cada día para acumular datos históricos.

## Prerequisitos
- n8n corriendo en: n8n.mdconsultoria-ti.org
- Admin: rafael.ramos@consultoriamd.com.mx
- API key: n8n-mexico-deploy (expira 5 May 2026)

## Paso 1: Configurar Credential "CRECE API"

1. Ir a n8n → Settings → Credentials → Add Credential
2. Tipo: **Header Auth**
3. Nombre: `CRECE API`
4. Header Name: `Authorization`
5. Header Value: `Bearer <TOKEN>`

Para obtener el token, ejecutar:
```bash
curl -s -X POST https://api-crece.mdconsultoria-ti.org/api/v1/auth/login \
  -d "username=admin@consultoriamd.com&password=crece2026!" \
  | jq -r .access_token
```

**Nota:** El token expira. Para producción, usar el endpoint de API Keys:
```bash
curl -s -X POST https://api-crece.mdconsultoria-ti.org/api/v1/api-keys \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "n8n-scraping", "expires_in_days": 365}'
```
Luego usar el header `X-API-Key` en vez de `Authorization: Bearer`.

## Paso 2: Crear Workflow "CRECE — Scraping Diario"

### Nodos:

1. **Schedule Trigger**
   - Tipo: Schedule
   - Frecuencia: Every day at 06:00 AM (America/Mexico_City)

2. **Get Dirigentes**
   - Tipo: HTTP Request
   - Method: GET
   - URL: `https://api-crece.mdconsultoria-ti.org/api/v1/dirigentes/`
   - Authentication: CRECE API (credential)
   - Response: JSON

3. **Split por Dirigente**
   - Tipo: Split In Batches
   - Batch Size: 1
   - Input: `{{ $json.items }}`

4. **Scrape Dirigente**
   - Tipo: HTTP Request
   - Method: POST
   - URL: `https://api-crece.mdconsultoria-ti.org/api/v1/social/scrape/{{ $json.id }}`
   - Authentication: CRECE API (credential)
   - Timeout: 300 seconds (scrapers pueden tardar)

5. **Wait** (entre dirigentes para no saturar)
   - Tipo: Wait
   - Duration: 30 seconds

6. **Log Result**
   - Tipo: Set
   - Guardar: dirigente_id, status, new_posts

### Flujo:
```
Schedule (6am) → Get Dirigentes → Split → Scrape → Wait 30s → Loop → Log
```

## Paso 3: Activar Workflows Existentes

Los 6 workflows ya importados necesitan la credential "CRECE API" configurada:

1. **CRECE — Actualizar Voter Score desde Chatwoot** → Toggle ON
2. **CRECE — Despacho de Canvassing a Promotor** → Toggle ON
3. **CRECE — Distribuir Contenido Aprobado** → Toggle ON
4. **CRECE — Alerta de Crisis (Polling)** → Toggle ON ← Este es clave, hace polling cada 15min
5. **CRECE — Intake Ciudadano desde Chatwoot** → Toggle ON
6. **CRECE — Campaña WhatsApp Masiva** → Toggle ON (manual trigger)

## Paso 4: Verificar

Después de activar, verificar en 24h:
```bash
# Verificar que hay posts nuevos
curl -s "https://api-crece.mdconsultoria-ti.org/api/v1/social/posts?page_size=5" \
  -H "Authorization: Bearer <TOKEN>" | jq '.items[0].scraped_at'
```

El `scraped_at` debe ser de hoy.

## Endpoints de Scraping Disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/social/scrape/{dirigente_id}` | POST | Scrape todas las plataformas de un dirigente |

El scraper automáticamente:
- Detecta qué plataformas tiene el dirigente (social_profiles)
- Ejecuta el scraper correspondiente (ensta, Scweet, yt-dlp, etc.)
- Deduplica posts por platform_post_id
- Actualiza followers/following counts

## Dirigentes Actuales

| ID | Nombre | Plataformas |
|----|--------|-------------|
| 1 | Alejandro Piña Medina | Twitter, Instagram, Facebook |
| 2 | Rafael Solano Pérez | Twitter, Instagram, Facebook, TikTok |

## Notas
- Los scrapers de Twitter necesitan `TWITTER_AUTH_TOKEN` en el .env del backend
- Facebook necesita cookies `FACEBOOK_C_USER` y `FACEBOOK_XS`
- Instagram (ensta) y YouTube (scrapetube) no necesitan auth
- Si un scraper falla, los demás continúan — no se detiene el pipeline
