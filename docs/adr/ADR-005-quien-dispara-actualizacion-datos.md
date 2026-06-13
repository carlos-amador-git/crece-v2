# ADR 005: Quién dispara la actualización de datos

**Estado:** Proposed
**Fecha:** 2026-06-13
**Autor:** Gemini CLI

## Contexto
La arquitectura de datos de CRECE v2 depende de RADAR para la recolección de métricas sociales. RADAR no es un proceso "live" o en tiempo real absoluto; es un proceso atendido que genera bundles de datos (json) depositados en MinIO.

Se requiere definir quién tiene la autoridad de disparar la sincronización (ingesta) de estos bundles hacia la base de datos productiva de CRECE y quién simplemente consume la información de "frescura".

## Decisión
1. **Trigger de Sincronización:** Exclusivo para roles `ADMIN` y `ANALYST`.
2. **Visibilidad de Frescura (Badge):** Disponible para todos los roles, incluyendo `VIEWER` (Dirigente).
3. **Mecánica:** El botón "Sincronizar con RADAR" operará sobre el último bundle disponible en MinIO. Si no hay bundle nuevo, el sistema reportará "Sin novedades" en lugar de fallar o re-ingestar lo mismo.

## Racional
* **SLA de Consultoría:** La actualización de datos es parte de la entrega de servicio de ConsultoríaMD. No es una funcionalidad de self-service para el cliente final.
* **Control de Costos/Recursos:** Ingestar bundles grandes consume recursos (Celery, LLM para NLP). Limitar el trigger a personal experto evita ejecuciones redundantes o innecesarias.
* **Transparencia:** El Dirigente (VIEWER) debe saber qué tan frescos son sus datos para contextualizar sus decisiones, pero no debe ser responsable de la "fontanería" técnica de la ingesta.

## Consecuencias
* Se requiere implementar guards de RBAC en el nuevo endpoint `POST /api/v1/ingest/sync/{dirigente_id}`.
* El frontend del dashboard de Dirigente (VIEWER) no mostrará botones de acción de sincronización, solo indicadores de estado.
