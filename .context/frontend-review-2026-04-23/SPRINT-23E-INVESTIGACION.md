# Sprint 23-E · Motor sentimiento con afiliación — investigación

**Clasificación:** 🔴 ESTRUCTURAL §9.8 (no tocar en esta sesión — solo documentar).
**Findings cubiertos:** F-23-01 (Tema Urgente + Alertas de Crisis) y F-23-06 (Sentiment Prom. ficha dirigente).

## Estado real del motor (2026-04-23)

### Existe un framework político de 3 capas (D-NLP-01)

`backend/app/services/political_framework.py`:

```python
Rol = Literal["oficialismo", "oposicion", "independiente"]
Tono = Literal["critico", "propositivo", "celebratorio", "informativo",
               "solidario", "ataque", "personal"]
Target = Literal["gobierno", "oposicion", "ciudadania", "medios",
                 "autopromocion", "tema_especifico", "otro"]

async def get_political_score(db, org_id, rol, tono, target, version="v1") -> dict:
    # Returns {score_tenant, score_default, is_override, descripcion}
```

Arquitectura documentada:
- **Layer 1:** NLP técnico (pysentimiento + HF) → raw sentiment
- **Layer 2:** LLM contextual (Gemma3) → tono + target
- **Layer 3:** Framework rules (este módulo) → sentimiento_politico_ajustado

**Memory Sprint NLP Framework:** "2026-04-13. Framework político 3 capas + admin panel + 95 posts clasificados manuales. Commit 118ce13."

### Lo que NO está conectado

Endpoint `GET /overview/kpi` (`dashboard.py:215-230`):

```python
# tema_urgente: most recent active crisis alert title
tema_query = select(AlertaCrisis).where(...).limit(1)
```

El `tema_urgente` toma el título crudo de `AlertaCrisis`. **No aplica `get_political_score` ni consulta el rol del dirigente.** Si Laura (oposición, MC) recibe una alerta "TikTok · sentimiento negativo avg -0.67" sobre posts que critican a Morena, el frontend lo muestra como riesgo negativo aunque para la oposición sea neutral/positivo.

Misma raíz para:
- `SentimentBadge` en cards y dashboard
- Sentiment Prom. en ficha dirigente (`-59%` que molesta al CEO en F-23-06)
- Alertas de Crisis (`CrisisAlertList` lee severity + sentimiento crudo)

## Gap funcional

| Lugar | Usa framework político? | Qué hace hoy | Qué debería hacer |
|---|---|---|---|
| `tema_urgente` en KPI overview | ❌ No | Muestra alerta cruda | Re-polarizar según rol del dirigente |
| `SentimentBadge` en post cards | ❌ No | sentiment_score directo | Ajustar por (rol, target) |
| Sentiment Prom. ficha dirigente | ❌ No | Agregación simple | Agregación con `score_tenant` |
| Alertas de Crisis | ❌ No | `severity` crudo | Opcional: bajar severity si tono alineado |
| Layer 2 batch (Gemma3) | ✅ Sí (genera tono+target) | Persiste clasificación | — |
| Admin Classification | ✅ Sí (visualización) | Permite overrides | — |

## Propuesta §9.8 para 2026-05-20

### Fase 1 · Persistir `score_tenant` por post (migration)

- Agregar `political_score: Integer | None` a `social_posts` (valor calculado de Layer 3 durante batch).
- Backfill: re-correr Layer 3 sobre los ~1,200 posts actuales (ya tienen tono + target de Layer 2).
- Migration alembic + downtime ventana.

### Fase 2 · Exponer `political_score` en API

- `SocialPostResponse.political_score: int | None`
- Endpoints que agregan sentimiento (ficha dirigente, sentiment-timeline, tema_urgente) consumen `political_score` en lugar de `sentiment_score` cuando el rol del dirigente está definido.

### Fase 3 · Opcional — Re-evaluar severidad de alertas

- `AlertaCrisis.severity` recalculado considerando alineación (rol, tono, target).
- Crítica a Morena por dirigente MC → severity bajada de `alta` a `media/baja`.

### Fase 4 · Frontend

- `SentimentBadge` acepta `politicalScore` opcional y lo prefiere sobre `sentiment_score` cuando está presente.
- Tema Urgente filtra alertas con severity ajustada.

## Riesgos

- **Datos del piloto actual:** 2 dirigentes activos (Piña, Ballesteros) y 6 shadow. Re-clasificar afecta su dashboard entre un deploy y otro. Requiere ventana + comunicación.
- **Overrides de matriz:** ya permitidos por tenant — cualquier cambio estructural debe respetar lo que el tenant ya sobreescribió.
- **Benchmark ya publicado:** los números que el CEO ha visto en presentaciones pueden moverse. Coordinar con comunicación cliente.

## Decisión recomendada

- **Hoy:** no ejecutar (§9.8 hard).
- **Próxima revisión §9.8 2026-05-20:** presentar esta propuesta junto a las ya acumuladas (P2 + P3 de Sprint 23-B) como paquete "Integridad semántica de sentimiento + schema hardening social_posts".
- **Interim:** la UI actual muestra sentimiento crudo. Añadir un disclaimer en el Tema Urgente del dashboard explicando "Sentimiento crudo — no considera afiliación política" podría ser un 🟡 CALIB si el CEO lo pide antes del 2026-05-20.
