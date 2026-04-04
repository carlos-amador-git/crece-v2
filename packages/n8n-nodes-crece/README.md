# n8n-nodes-crece

n8n community nodes for the **CRECE v2.0** political intelligence platform.

## Overview

This package provides 5 nodes that connect n8n workflows to the CRECE API, enabling automated political campaign operations:

| Node | Description |
|------|-------------|
| **CRECE Segmentar** | Filter and count citizens by electoral section, demographics, voting intention, and voter score |
| **CRECE Sentimiento** | Analyze sentiment of political text (pysentimiento + spaCy) or retrieve post-level sentiment |
| **CRECE Contenido** | Generate AI-powered political content (posts, scripts, speeches) for dirigentes |
| **CRECE Canvassing** | Generate optimized door-to-door routes, list routes, track visited points |
| **CRECE Voter Score** | Run voter scoring, retrieve individual scores, view segment distributions |

## Installation

### In n8n (community nodes)

1. Go to **Settings > Community Nodes**
2. Enter `n8n-nodes-crece`
3. Click **Install**

### Manual (development)

```bash
cd ~/.n8n/custom
npm install /path/to/n8n-nodes-crece
# or link for development:
npm link n8n-nodes-crece
```

## Credentials

All nodes require the **CRECE API** credential with two fields:

| Field | Description |
|-------|-------------|
| API URL | Base URL of the CRECE API (e.g. `http://localhost:8000/api/v1`) |
| API Token (JWT) | Bearer token obtained from `POST /auth/login` |

The credential includes a built-in test that calls `GET /auth/me` to validate the token.

## Node Details

### CRECE Segmentar

| Operation | Endpoint | Description |
|-----------|----------|-------------|
| Segment | `GET /ciudadanos/` | Retrieve filtered list of citizens |
| Count | `GET /ciudadanos/?count_only=true` | Count matching citizens |

**Filters:** seccion_id, intencion_voto, edad_rango, escolaridad, es_simpatizante, score_min, score_max

### CRECE Sentimiento

| Operation | Endpoint | Description |
|-----------|----------|-------------|
| Analyze Text | `POST /social/analyze` | Real-time sentiment analysis |
| Get Post Sentiment | `GET /social/posts/{id}/sentiment` | Pre-computed post sentiment |

### CRECE Contenido

| Operation | Endpoint | Description |
|-----------|----------|-------------|
| Generate | `POST /contenido/generate` | AI content generation |
| List | `GET /contenido/` | List generated content |
| Update Status | `PATCH /contenido/{id}/estado` | Change content status |

**Formats:** post_twitter, post_instagram, post_facebook, guion_tiktok, guion_youtube, comunicado_prensa, discurso, infografia

### CRECE Canvassing

| Operation | Endpoint | Description |
|-----------|----------|-------------|
| Optimize Route | `POST /canvassing/optimize` | Generate optimized route |
| List Routes | `GET /canvassing/routes` | List existing routes |
| Mark Visited | `PATCH /canvassing/routes/{id}/punto/{pid}` | Mark point visited |

### CRECE Voter Score

| Operation | Endpoint | Description |
|-----------|----------|-------------|
| Score All | `POST /voter-scoring/run` | Trigger full scoring run |
| Get Score | `GET /voter-scoring/{id}` | Get individual score |
| Get Segments | `GET /voter-scoring/segments` | Segment distribution |

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Watch mode
npm run dev

# Type check
npm run typecheck

# Run tests
npm run test
```

## License

MIT - MD Consultoria SC
