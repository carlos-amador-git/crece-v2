# Operación MD — Clasificación Política Semanal

**Audiencia:** Marx Chávez (CEO MD Consultoría) + analistas futuros
**Cadencia:** Semanal (aprox. 30-60 min por org)
**Resultado:** Cada cliente ve su dashboard actualizado con scores políticos
deliberados por 3 IAs y revisados por humano.

---

## Filosofía

CRECE v2 NO corre LLMs automatizados. El flujo es:
1. Un humano (tú / analista MD) dispara el pipeline semanal
2. 3 IAs deliberan externamente (Claude Code + Gemini CLI + Perplexity web)
3. El framework político rule-based (configurable por tenant) traduce las decisiones de las IAs en scores
4. El cliente ve el resultado, nunca interactúa con LLMs

**Por qué:**
- $0 costo de infraestructura (no pagamos APIs LLM)
- Privacidad total (ningún dato del cliente pasa por servidores LLM de 3ros)
- Control humano en el loop (imposible que el sistema se engañe solo)
- Diferenciador comercial "deliberado por 3 IAs de última generación"
- Roadmap natural: cuando tengamos 500+ validaciones por tenant, entrenamos
  modelo propio (fine-tune BETO) que automatice el pipeline con la misma
  calidad — sin deuda técnica.

---

## Flujo semanal (por cada org activa)

### Paso 1 — Abrir panel admin
**URL:** `http://localhost:3005/dashboard/admin/clasificacion`
(en prod: `<dominio>/dashboard/admin/clasificacion`)

Solo visible con `role=admin` (MD Consultoría).

### Paso 2 — Ver cobertura actual
El panel muestra una tabla con cada org:
- Posts totales
- Posts clasificados
- Posts pendientes
- Última clasificación

Prioriza orgs con cobertura < 80% o con última clasificación > 7 días.

### Paso 3 — Generar prompt
1. Selecciona org (MC-CDMX / GOB-OAXACA / CDMX-IND)
2. Ajusta límite (default 30 posts — más alto al inicio, luego 10-20 por semana)
3. Click **"Generar prompt"**
4. El sistema construye un prompt con:
   - Matriz política del tenant (incluye overrides si los hay)
   - Top N posts pendientes ordenados por engagement
   - Schema JSON esperado de respuesta

### Paso 4 — Deliberación de 3 IAs

Abre **Claude Code** en una terminal nueva:
```bash
cd /Users/marxchavez/Projects/crece-v2
claude
# pegar el prompt copiado
```

Claude devuelve un JSON array con clasificaciones.

**Cross-audit Gemini:**
```bash
gemini -m gemini-2.5-flash -p "$(cat <<EOF
Valida estas clasificaciones políticas. Flag si discrepas:
<pegar el prompt + JSON de Claude>
EOF
)"
```

**Casos controvertidos (3-5 posts ambiguos):**
- Abre [Perplexity web](https://perplexity.ai) y pega el texto del post con rol del dirigente
- Perplexity agrega research en web para temas políticos específicos
- Decide la clasificación final integrando las 3 opiniones

### Paso 5 — Subir clasificaciones
1. Vuelve al panel admin
2. Selecciona fuente IA: **"Ensamble (3 IAs deliberaron)"** si hiciste cross-audit completo, o la IA específica si fue rápida
3. Pega el JSON en el textarea del paso 2
4. Click **"Aplicar clasificaciones"**
5. El backend:
   - Valida que los posts existen y pertenecen a la org
   - Aplica la matriz del tenant → calcula `sentimiento_politico_ajustado`
   - Persiste con audit trail (quién, cuándo, qué IA)
   - Actualiza el dashboard del cliente

### Paso 6 — Verificar
- Vuelve al dashboard del cliente (tenant switcher → esa org)
- Confirma que los KPIs y scores reflejan la nueva data
- Badge "Análisis Contextual · 3 IAs deliberaron" visible

---

## Tiempo estimado por org

| Escenario | Posts | Tiempo |
|---|---|---|
| Onboarding inicial | 60 top engagement | ~45-60 min |
| Mantenimiento semanal | 20-40 nuevos | ~20-30 min |
| Casos controvertidos (Perplexity) | 3-5 posts | +10-15 min |

---

## Checklist pre-cada-semana

- [ ] Backup reciente de DB (cron automático Coolify)
- [ ] Revisar `framework_audit_log` por cambios del cliente en su matriz
- [ ] Validar que ningún override esté fuera de rango ±1 del default
- [ ] Revisar `encuestas_publicas` — ¿hay nuevas encuestas Oraculus/Demoscopía?
      (pipeline de scraper aún por construir — ver `docs/NLP-MODELOS-INVESTIGACION.md`)

---

## Escalamiento futuro

**Umbrales para automatizar:**
- 20+ orgs activas → contratar analista político MD full-time
- 500+ posts validados por org → entrenar LoRA sobre BETO con ese corpus
- 50+ orgs → considerar API Claude Haiku para batch nocturno ($40-60/mes por org)

**No es deuda técnica** — es evolución natural. Cada etapa acumula el dataset
de validación que permite la siguiente automatización.

---

## Archivos relacionados

- **Admin panel:** `frontend/src/app/dashboard/admin/clasificacion/page.tsx`
- **API endpoints:** `backend/app/api/v1/endpoints/admin_classification.py`
- **Framework service:** `backend/app/services/political_framework.py`
- **Prompt generator:** backend genera dinámicamente con matriz del tenant
- **Schema DB:** columnas `tono_discurso`, `target_politico`,
  `sentimiento_politico_ajustado`, `llm_modelo`, `llm_razon`, `llm_processed_at`
- **Matriz defaults:** `docs/POLITICAL-FRAMEWORK-DEFAULTS.md`
- **Decisiones:** `.context/DECISIONS.md` D-NLP-01 a D-NLP-05
