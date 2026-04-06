# CRECE v2 — Sprint Fase 2.0: Endpoints de Integración
# Leer CLAUDE.md y docs/ARQUITECTURA-INTEGRADA.md antes de empezar.

## Objetivo
Crear los endpoints que n8n-mexico consumirá para conectar CRECE con Chatwoot-MX.
Prerequisito para TODA la Fase 2.

## 1. Nuevas tablas (migración Alembic)

### campaigns
- id UUID PK, org_id FK organizaciones, nombre, tipo DEFAULT 'whatsapp'
- segmentacion JSONB (secciones, intencion_voto, rango_edad, genero, etc.)
- tipo_nudge VARCHAR(50) (aversion_perdida, prueba_social, escasez, null)
- total_destinatarios, enviados, entregados, leidos, respondidos (INTEGER)
- estado (borrador/programado/enviando/completado/pausado/cancelado)
- chatwoot_campaign_id VARCHAR(100), programado_para TIMESTAMPTZ
- creado_por_id FK users

### contenido_piezas
- id UUID PK, org_id FK, dirigente_id FK dirigentes
- tema VARCHAR(500), contexto TEXT, tono VARCHAR(50)
- variantes JSONB (twitter, instagram_reel, carrusel, facebook, whatsapp)
- modelo_ia VARCHAR(100), prompt_usado TEXT, tokens_usados INTEGER
- estado (borrador/en_revision/aprobado/publicado/rechazado)
- aprobado_por FK users, aprobado_at TIMESTAMPTZ

### alertas_crisis
- id SERIAL PK, org_id FK, perfil_id FK social_profiles
- tipo (toxicity_spike, negative_trend, coordinated_attack, viral_negative)
- severidad (baja/media/alta/critica), descripcion TEXT
- post_ids JSONB, estado (nueva/vista/atendida/descartada)

### crm_interacciones
- id BIGSERIAL PK, org_id FK, ciudadano_id FK ciudadanos
- tipo (visita_puerta, whatsapp_enviado, whatsapp_respondido, llamada, evento_asistio, encuesta_completada, propuesta_ciudadana)
- canal (whatsapp/telefono/presencial/redes/app)
- resultado (positivo/neutro/negativo/sin_respuesta)
- notas TEXT, referencia_tipo VARCHAR, referencia_id VARCHAR
- promotor_id FK users

### voter_scores
- id BIGSERIAL PK, org_id FK, ciudadano_id FK UNIQUE
- score_favorable FLOAT, score_persuadible FLOAT, score_asistencia FLOAT
- features JSONB, modelo_version VARCHAR(50)

### ia_content_registry (compliance etiquetado IA)
- id BIGSERIAL PK, org_id FK
- tipo_contenido, referencia_tabla, referencia_id
- modelo_ia VARCHAR(100), prompt_hash VARCHAR(64)
- publicado BOOLEAN, created_at TIMESTAMPTZ

## 2. API Key auth para n8n

n8n no puede hacer login JWT. Crear middleware alternativo:
- Tabla: api_keys (id, org_id, key_hash, name, permissions JSONB, is_active)
- Keys formato Stripe: crece_live_xxxxxxxxxxxx
- Header: X-API-Key
- Middleware que acepta JWT O API Key

## 3. Endpoints nuevos

### POST /api/v1/campaigns/segment
Segmentación dinámica de ciudadanos. Construye WHERE clauses desde JSONB.
Input: {secciones[], intencion_voto[], rango_edad[], genero[], programa_social, excluir_contactados_dias}
Output: {total: N, ciudadanos: [{id, nombre, telefono, colonia, seccion, intencion_voto}]}
SIEMPRE filtrar por org_id. SIEMPRE excluir sin teléfono.

### POST /api/v1/content/generate
Genera contenido multi-formato con Claude API.
Seguir patrón de plan_generator.py: gather_context → build_prompt → Claude.
Input: {dirigente_id, tema, contexto, tono, plataformas[]}
Output: {id, variantes: {twitter:{}, instagram_reel:{}, ...}, modelo_ia, estado}
Registrar en ia_content_registry para compliance.
También crear /content/generate/stream (SSE) y /content/pieces/{id}/approve.

### GET /api/v1/alerts
Alertas de crisis NLP. Filtros: severity, status, since.
Modificar worker NLP: cuando toxicity_score > 0.7 en 2+ posts de un perfil
en 2 horas → crear alerta_crisis automáticamente.

### POST /api/v1/crm/interactions
Registrar interacción con ciudadano. n8n llama cada vez que hay contacto.
Input: {ciudadano_id, tipo, canal, resultado, notas, referencia_tipo, referencia_id}

### GET /api/v1/crm/scores/{ciudadano_id}
Consultar voter score. Si no tiene, retornar 404.
GET /api/v1/crm/scores para ranking con filtros.

### POST /api/v1/webhooks/chatwoot
Recibe eventos pre-procesados por n8n (NO raw Chatwoot).
Header: X-N8N-Signature (HMAC-SHA256).
CRECE nunca recibe webhooks directos de Chatwoot — siempre via n8n.

## 4. Servicio content_factory.py
Crear NUEVO servicio siguiendo patrón de plan_generator.py.
Reutilizar _gather_context(). Prompt pide JSON con variantes por plataforma.
SIEMPRE registrar modelo_ia en ia_content_registry.

## 5. Registrar routers en main.py
campaigns, content_factory, alerts, crm, webhooks

## 6. Tests
- test_campaigns.py — segment con filtros
- test_content_factory.py — generate (mock Claude API)
- test_alerts.py — CRUD alertas
- test_crm.py — interactions + scores
- test_webhooks.py — firma HMAC válida/inválida

## 7. Orden
1. Modelos + migración Alembic
2. API key auth
3. campaigns/segment
4. crm/interactions + scores
5. content/generate
6. alerts + lógica en worker NLP
7. webhooks/chatwoot
8. Tests
