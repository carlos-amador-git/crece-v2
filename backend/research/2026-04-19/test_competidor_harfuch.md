# Test competidor resolution POC — Omar García Harfuch

**Fecha:** 2026-04-19
**Caso:** Omar García Harfuch · Secretario de Seguridad Pública y Protección Ciudadana (federal)
**Objetivo:** validar empíricamente el flujo propuesto en D-23 (Onboarding Wizard Sprint S5) y documentar modos de falla que justifican la confirmación humana como requisito de arquitectura
**Ejecutado por:** Joy (Claude Code sesión CRECE v2) via MCP Apify + Brightdata
**Script reproducible:** `backend/scripts/test_competidor_resolution.py`

---

## Flujo ejecutado y resultados empíricos

### Fase 1 · Búsqueda automática (SERP geo-MX)

**Actors probados:**

| Stack | Resultado |
|---|---|
| Brightdata MCP `search_engine` geo=mx | ❌ HTTP 400 "No active transport" (MCP offline) |
| Apify `sovereigntaylor/google-search-scraper` country=mx | ⚠️ 2 queries ejecutadas pero `totalOrganicResults=0` — Google bloqueando scraper sin proxies residenciales |
| Brightdata scraping_browser (no probado) | Pendiente — requiere residential proxy y sesión persistente, scope S5 real |

**Conclusión Fase 1:** la búsqueda automática SERP **NO es confiable** sin proxies residenciales pagados. Sin SERP hits, Fase 2 no tiene candidatos para validar. El flujo "cliente ingresa nombre → sistema encuentra cuentas" requiere inversión adicional en proxies residenciales ($20-40 USD/mes por sesión estable) o abandonar SERP y pedir al cliente que pegue URLs directamente.

### Fase 2 · Validación de perfiles (Apify IG profile scraper)

Al no tener candidatos de Fase 1, probé manualmente 4 handles plausibles para Harfuch basados en conocimiento público:

| Handle probado | Resultado | Diagnóstico |
|---|---|---|
| `omar_garcia_harfuch` | ❌ not_found | variante inválida |
| `omargarciaharfuch` | ❌ not_found | variante inválida |
| `ogarciaharfuch` | ❌ not_found | variante inválida |
| `omarharfuch` | ❌ not_found | variante inválida |
| `oharfuch` | ✅ FOUND pero **FALSO POSITIVO** | Es una tienda de joyería llamada *Rutherford* con 423 followers, bio "Established in 1952, Rutherford has earned a reputation for rare and unique jewellery, silver and pearls." · sin verified · posts de moda de 2020 |

**El falso positivo es el hallazgo más crítico del test.** Sin disambiguación humana, el sistema habría asociado a Omar García Harfuch (Secretario de Seguridad) con una tienda de joyería. Las consecuencias en producto serían catastróficas: benchmarks inventados, recomendaciones sin sentido, riesgo reputacional con el cliente.

**Corrección humana (input CEO 2026-04-19):** el handle real es `omargharfuch` (con "g" de García). Validado con el actor IG:

| Campo | Valor |
|---|---|
| username | `omargharfuch` |
| fullName | **Omar H García Harfuch** (match exacto del nombre buscado) |
| verified | **✅ TRUE** (badge azul Meta) |
| followersCount | **656,564** (Macro estrato) |
| postsCount | 179 |
| private | false |

Heurística de confianza (score automático del script):

| Señal | Peso | Aplica? |
|---|---|---|
| full_name match ≥2 tokens del nombre buscado | +0.4 | ✅ (Omar, García, Harfuch en ambos) |
| verified badge | +0.3 | ✅ |
| followers > 50K | +0.2 | ✅ |
| posts > 20 | +0.1 | ✅ |
| **Total** | | **1.0 (máximo)** |

Compárese con el falso positivo `@oharfuch` (jewelry store):

| Señal | Peso | Aplica? |
|---|---|---|
| full_name match ≥2 tokens | +0.4 | ❌ (full_name="OHarfuch" no contiene García ni Omar) |
| verified | +0.3 | ❌ |
| followers > 50K | +0.2 | ❌ (solo 423) |
| posts > 20 | +0.1 | ❌ (solo 7) |
| **Total** | | **0.0** |

Umbral propuesto de auto-aceptación: **≥ 0.7**. Por debajo, el sistema DEBE pedir confirmación humana al cliente. El falso positivo habría quedado en 0.0 automáticamente, pero sin validación contra candidato conocido no habría nada con qué comparar. La lógica debe ser: **presentar TODOS los candidatos al cliente con su score para que elija el correcto o pegue el handle manual**.

### Fase 3 · Scraping piloto (Apify X timeline 30d)

Ejecutado con el handle correcto `@OHarfuch` en X (Twitter):

**Muestra de posts capturados (2026-04-13 al 2026-04-18):**

| Tweet ID | Fecha | Likes | Reposts | Replies | Views |
|---|---|---|---|---|---|
| 2043801773396099116 | 2026-04-13 | 4,196 | 1,252 | 378 | 326,214 |
| 2045496088082169988 | 2026-04-18 | 4,114 | 1,339 | 162 | 132,270 |

Contenido: operativos federales coordinados (@Defensamx1, @SEMAR_mx, @FGRMexico, @GN_MEXICO_, @SSPCMexico) — coherente con cargo público de Secretario de Seguridad.

**Señales de autenticidad:**
- `authorLocation: "CDMX"` ✅
- Engagement ratio consistente con perfil Macro MX (ER ~1.4-2.0%, coherente con dataset Zenodo v1 celda Macro X)
- Cobertura temática coherente (seguridad federal)

**Scraping OK:** el actor devuelve tweets con métricas completas (likes, reposts, replies, views). Costo ~$0.024 USD para 30 posts a $0.0008/post en tier FREE.

---

## Errores y modos de falla documentados

1. **Brightdata SERP MCP offline** — el servicio de búsqueda Brightdata vía MCP respondió HTTP 400 "No active transport" durante toda la sesión. Si el Onboarding Wizard depende de Brightdata como primary, requiere monitoreo de disponibilidad + failover.

2. **Apify SERP sin proxies** → 0 resultados orgánicos. La búsqueda automática es inviable sin residential proxies. Alternativa: **pedir al cliente que pegue las URLs directamente** en el wizard, eliminando la fase SERP por completo.

3. **Falso positivo silencioso en IG** — el username `oharfuch` existe y devuelve datos VÁLIDOS de un perfil completamente distinto (tienda de joyería). El sistema automático no tiene forma de saberlo sin la heurística de score. **Esta es la razón arquitectónica más fuerte para la confirmación humana obligatoria.**

4. **Handles con variantes sutiles** — `omargharfuch` (con g) vs `omargarciaharfuch` (sin abreviar). Pequeñas diferencias ortográficas llevan a 4 de 5 variantes a not_found. El wizard debe sugerir los top-5 candidatos ordenados por score y permitir al cliente editar el handle manualmente.

---

## Recomendaciones de arquitectura para D-23 / Sprint S5

Basado en este test empírico, la arquitectura del Onboarding Wizard debe:

1. **NO depender de SERP como primary.** Pedir al cliente que pegue URLs directas es más confiable y cero-costo que SERP con proxies. SERP queda como asistencia opcional para "auto-llenar" con fallback a input manual.

2. **Implementar la heurística de score documentada** (match de tokens full_name + verified + followers + posts) como filtro de confianza. Umbral 0.7 para auto-aceptación, 0.4-0.7 para revisión manual, <0.4 para rechazo automático con sugerencia de edición.

3. **Siempre mostrar al cliente los top-N candidatos con su score** antes de activar scraping. Nunca asumir match automático sin confirmación. El wizard debe tener una UI de "¿cuál es correcta?" con botones explícitos.

4. **Stack probado y funcional:**
   - `apify/instagram-profile-scraper` → ✅ rápido, datos completos, ~$0.003/perfil
   - `delicious_zebu/advanced-x-twitter-profile-scraper` → ✅ timeline con métricas, ~$0.0008/post
   - SERP Apify → ⚠️ no confiable sin proxies, mejor opt-out
   - Brightdata MCP → ⚠️ intermitente, no primary

5. **Costo proyectado por cliente Onboarding:** ~$0.05-0.15 USD para resolver 5 plataformas (IG/FB/TT/YT/X) con 5-10 candidatos cada una. Compatible con la estimación D-23 de $3-5 USD/mes/cliente una vez sumado el scraping recurrente.

---

## Evidencia de ejecución empírica

- **Apify actor IG profile run id:** `khcjMhhtn0bqi2Yz8` · dataset `BQqtETZ5ogOUv5BWi`
- **Apify actor X posts run id:** `dMVMlkbPJgTpNBfxH` · dataset `hrvzuW0FUy003Z7hl`
- **Apify actor SERP run id:** `bQgdMxyLlnTWh3VE6` · dataset `Eu5hBM2gelLSo7jUO`
- **Handle IG confirmado por CEO:** `https://www.instagram.com/omargharfuch/` (input humano 2026-04-19)
- **Script reproducible:** `backend/scripts/test_competidor_resolution.py`

## Veredicto del test

**✅ PASS con hallazgos críticos para D-23.** El flujo 3-fases del Onboarding Wizard ES viable técnicamente pero **requiere confirmación humana obligatoria** — no opcional — en Fase 2. El falso positivo de la tienda de joyería es evidencia empírica de que la disambiguación automática sola es insuficiente.

D-23 queda **aprobado con ajuste de diseño:** el wizard NO depende de SERP como primary (cliente pega URLs), y SIEMPRE muestra los candidatos con score para que el cliente confirme antes de activar scraping. Esto reduce scope +1 día a scope +0.5 día (elimina integración SERP compleja).
