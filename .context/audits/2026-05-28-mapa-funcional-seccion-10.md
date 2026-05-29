YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Ripgrep is not available. Falling back to GrepTool.
# Auditoría sección §10 — Admin (admin/analyst MD scope)
**Fecha:** 2026-05-28
**Auditor:** Gemini

## Citas verificadas
- **Endpoints Backend:** Se confirmó la existencia y ubicación exacta de los siguientes handlers:
    - `admin_overview.py:76` (`GET /admin/overview`) ✅
    - `admin_classification.py:98` (`GET /pending`), `:153` (`GET /prompt`), `:218` (`POST /batch`), `:317` (`GET /stats`) ✅
    - `admin_compliance.py:115` (`POST /purge-hash`), `:205` (`GET /purge-audit`) ✅
    - `admin_promesas.py:56` (`POST /admin/promesas`), `:86` (`GET /admin/promesas/{id}`) ✅
    - `hitl_evaluation.py`: `:158` (sample), `:386`/`:463` (comments), `:494`/`:562` (posts), `:593` (audit) ✅
- **Vistas Frontend:** Las 4 páginas citadas existen en `frontend/src/app/dashboard/admin/`:
    - `overview/page.tsx` ✅
    - `clasificacion/page.tsx` ✅
    - `plan-ia-review/page.tsx` ✅
    - `ranking/page.tsx` ✅
- **Arquitectura:** Se confirmó la **ausencia** de `use-admin.ts` centralizado, validando la convención de consumo ad-hoc para herramientas internas. ✅
- **Consumo inline:** Se verificó que `admin/overview/page.tsx` y `admin/clasificacion/page.tsx` consumen `api.get<>` directamente. ✅
- **HITL Bilateral:** Se confirmó en `hitl_evaluation.py:72` (`_check_dirigente_access`) que los mismos endpoints sirven tanto al cliente (scope restringido) como al admin (scope total), validando la nota cross-doc con §9. ✅

## Citas sin verificar / inventadas
- **Generalización de consumo FE (§10C):** La afirmación *"cada página admin/*/page.tsx hace api.get<> directo"* es **imprecisa**. 
    - `admin/plan-ia-review/page.tsx` consume hooks centralizados `useRecomendaciones` y `useTransicionarEstado` de `use-recomendaciones.ts`.
    - `admin/ranking/page.tsx` consume `useAdminCompetitorRankings` de `use-competitors.ts`.
    - El patrón "inline" solo se cumple rigurosamente en `overview` y `clasificacion`.

## Omisiones detectadas
- **Nombres de funciones Compliance:** El documento deja como `(verificar)` los endpoints de `admin_compliance.py`. Se confirmó que son `purge_by_hash` (POST) y `list_purge_audit` (GET).
- **Consistencia estructural:** El documento contiene una sección `## 10. Admin (no-cliente) 📝 Pendiente` al final que contradice el estado "✅ Documentado" del índice y el contenido ya redactado. Es un residuo de redacción que genera ruido documental.

## Sesgo del redactor
- **Optimismo en consistencia de patrones:** El redactor asumió que porque las herramientas de admin son "operativas" todas seguirían el patrón `api.get` inline, ignorando que los módulos que tocan lógica de negocio compartida (Planes IA, Competidores) prefieren reutilizar hooks existentes.
- **Deuda de limpieza:** El redactor dejó bloques "Pendiente" al final del archivo a pesar de haber completado la sección arriba, lo cual rompe la "referencia única" pretendida en el propósito del doc.

## Veredicto
⚠️ **PASA CON AJUSTES.**
La sección es técnicamente muy precisa en cuanto a endpoints y lógica de negocio, pero falla en la descripción de la arquitectura frontend y presenta desorden estructural (duplicidad de títulos con estados contradictorios).

**Acciones recomendadas:**
1. Actualizar §10C para reflejar que las páginas de admin reutilizan hooks cuando la lógica es compartida (`plan-ia-review`, `ranking`).
2. Eliminar el bloque duplicado `## 10. Admin (no-cliente) 📝` al final del archivo.
3. Reemplazar los marcadores `(verificar)` en §10B por los nombres/funciones confirmados.
