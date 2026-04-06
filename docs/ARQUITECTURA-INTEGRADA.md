# CRECE v2.0 — Arquitectura Integrada con Ecosistema MD
## Fase 2 usando: CRECE + Chatwoot-MX + n8n-mexico + md-design-system

## Arquitectura de 3 Sistemas
```
CRECE (FastAPI) ←→ n8n-mexico (orquestador) ←→ Chatwoot-MX (comunicación)
  "Cerebro"          "Sistema Nervioso"           "Boca y Oídos"
```

- CRECE: inteligencia electoral, NLP, scoring, segmentación, Content Factory, mapas
- n8n: workflows que conectan CRECE ↔ Chatwoot (campaign sender, citizen intake, crisis alert)
- Chatwoot: WhatsApp Business API (WABA conectada), IG, FB, Telegram, email, web chat, Captain AI
- md-design-system: tokens, componentes (StatCard, BentoGrid, AlertFeed), dashboard-pro template

## Impacto por Módulo de Fase 2

### F2.1 WhatsApp Campaign Manager (2-3 semanas, NO 6-8)
- Conexión WhatsApp: Chatwoot lo tiene → NO construir
- Envío de templates: n8n-nodes-mx-whatsapp-plus → adaptar para político
- Tracking estado: Chatwoot webhooks → NO construir
- CRECE solo necesita: endpoint POST /campaigns/segment + tabla campaigns

### F2.2 Smart Canvassing (3-4 semanas)
Se mantiene igual — es lógica PostGIS pura en CRECE.
Comunicación con promotores via n8n → Chatwoot WhatsApp.

### F2.3 Content Factory (3-4 semanas)
Generación multi-formato con Claude API + distribución via n8n/Chatwoot.
Video preview con Remotion de md-design-system.

### F2.4 CRM Político + Voter Scoring (4-5 semanas, NO 6-8)
Chatwoot ya registra historial de conversaciones por Contact.
n8n sincroniza interacciones → CRECE actualiza voter score.
scikit-learn (LogisticRegression) para predicción.

### F2.5 Participación Ciudadana (3-4 semanas, NO 6-8)
WhatsApp ES la interfaz ciudadana. No se necesita portal web.
Chatwoot recibe → n8n clasifica keywords → CRECE crea propuesta.
Dirigente responde desde dashboard → n8n → Chatwoot → WhatsApp al ciudadano.

### F2.6 Blindaje Legal (2-3 semanas)
Reutilizar RLS y audit log de n8n-mexico.
n8n-nodes-mx-cfdi para facturación de campañas.

## Nuevo Paquete n8n: n8n-nodes-crece

5 nodos que van dentro del monorepo n8n-mexico (packages/n8n-nodes-crece/):
- CreceSegmentar: POST /campaigns/segment → lista de ciudadanos filtrados
- CreceSentimiento: GET /alerts (polling trigger cada 5 min)
- CreceContenido: POST /content/generate → variantes multi-plataforma
- CreceCanvassing: GET/POST zonas y asignación de promotores
- CreceVoterScore: POST /crm/interactions + GET /crm/scores

6 workflows que conectan los 3 sistemas:
- crece-campaign-whatsapp.json: Segmentar → WhatsApp Plus → Chatwoot → Track
- crece-citizen-intake.json: Chatwoot msg → keyword detect → CRECE propuesta
- crece-crisis-alert.json: CreceSentimiento trigger → Chatwoot notifica equipo
- crece-content-distribute.json: Content Factory aprobado → Chatwoot multi-canal
- crece-canvassing-dispatch.json: Zona asignada → WhatsApp a promotor
- crece-voter-score-update.json: Cualquier interacción → CRECE re-scoring

## md-design-system → Frontend CRECE

Tokens a integrar en tailwind.config.ts:
- Colors: primary #1e3a5f, secondary #d4a853, accent #10b981
- Fonts: Instrument Sans (display), DM Sans (body), JetBrains Mono (mono)
- Electoral: favorable=emerald, indeciso=amber, oposicion=red

Componentes reutilizables:
- StatCard → KPIs del dashboard
- BentoGrid + BentoCard → Layout dashboard
- AlertFeed → Alertas de crisis NLP
- StatusTimeline → Progreso de campañas y zonas
- dashboard-pro/KPICards → Cards con sparklines GSAP
- dashboard-pro/Sidebar + TopBar → Layout base del dashboard
- dashboard-pro/DataTable → Tablas de ciudadanos/encuestas
- Remotion → Video generation para Content Factory

## Timeline Revisado

### Fase 2 Integrada (Semanas 1-16)

| Semana | Módulo | Entregable |
|---|---|---|
| 1-2 | Integración base | Webhooks CRECE↔n8n↔Chatwoot, API keys, test flujo |
| 1-3 | n8n-nodes-crece | Paquete 5 nodos + credential + 6 workflows |
| 2-4 | F2.1 WhatsApp | Endpoint segmentación + workflow campaign-sender |
| 3-6 | F2.2 Canvassing | PostGIS clustering + rutas + React Native MVP |
| 5-8 | F2.3 Content Factory | Claude multi-formato + distribución Chatwoot |
| 7-12 | F2.4 CRM + Scoring | scikit-learn + Chatwoot sync + interacciones |
| 11-14 | F2.5 Participación | WhatsApp intake + propuestas + resolución |
| 13-16 | F2.6 Blindaje | Gastos SIF + bots + etiquetado IA |

Total: 16 semanas (vs 32 del diseño aislado — ahorro 50%)

## Ahorro por Reutilización

| Capacidad | Sin ecosistema | Con ecosistema | Ahorro |
|---|---|---|---|
| WhatsApp Business API | 4 sem | 0 (Chatwoot) | 4 sem |
| Multi-canal (IG,FB,TG) | 6 sem | 0 (Chatwoot) | 6 sem |
| Dashboard de agentes | 4 sem | 0 (Chatwoot) | 4 sem |
| Orquestación workflows | 3 sem | 0 (n8n) | 3 sem |
| Design tokens + UI | 3 sem | 1 sem import | 2 sem |
| Portal participación | 4 sem | 1 sem (WhatsApp) | 3 sem |
| Audit log | 1 sem | 0 (n8n-mexico) | 1 sem |
