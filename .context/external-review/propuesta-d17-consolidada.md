# Propuesta D-17 (consolidada): Cierre de ciclo del Plan IA con seguimiento de recomendaciones activas

**Para insertar en CRECE_PRODUCT_MASTER.md §6 Decisiones vivas.**
**Estado:** 🟢 APROBADA con las cuatro decisiones CEO del 19 de abril de 2026 ya integradas.
**Autor de la propuesta:** Claude.ai Opus 4.7 sobre planteamiento CEO 2026-04-19.
**Autor de las decisiones:** CEO Marx Chávez 2026-04-19 en chat directo con Claude.ai.
**Relación con otras decisiones:** complementa D-16 unificación provider LLM (Gemini CLI) y D-18 endpoint ARCO purge-hash.
**Implicaciones:** afecta Sprint S1 Backend Foundations y Sprint S4 Plan IA LLM. Expande MVP en 2 bloques y 3-4 días de desarrollo adicional.

---

## Entrada para §6 tabla de decisiones

Insertar como fila nueva en la tabla principal de la sección 6, después de D-16 y antes de D-18.

| ID | Fecha | Decisión | Razón | Status | Ref |
|---|---|---|---|---|---|
| D-17 | 2026-04-19 | Cierre de ciclo del Plan IA con seguimiento de recomendaciones activas. Añadir bloques #10.5 (Seguimiento de Recomendaciones Activas) y #10.7 (Memoria del Plan IA) al inventario, tabla `recomendaciones_plan_ia` a BD, y flujo completo de cinco fases generación-decisión-ejecución-seguimiento-cierre | El Plan IA del Sprint S4 original generaba recomendaciones pero no rastreaba ejecución ni medía resultado real. Sin cierre de ciclo el cliente no podía distinguir recomendaciones exitosas de fallidas, el sistema no aprendía de su histórico, y la conversación comercial se quedaba en promesas cualitativas. El CEO identificó el gap con ejemplo concreto del video de TikTok sobre fallas del Metro y aprobó la expansión del MVP a 4-5 semanas para entregar el ciclo completo desde el primer piloto | 🟢 APROBADA con matices · MVP expandido · 4 parámetros de diseño fijados | §6.3 este doc · §3.2 inventario bloques #10.5 y #10.7 · §5 Sprint S1 + S4 expansión |

---

## Desarrollo extendido de la decisión

Insertar como subsección §6.3 después de §6.2 (desarrollo de D-16 provider LLM).

### §6.3 — Desarrollo de D-17: Cierre de ciclo del Plan IA

**Problema identificado por CEO (chat directo 2026-04-19 post-PR #16):**

El diseño original del Plan IA en Sprint S4 genera recomendaciones con anatomía completa de la §2.6.7, pero no cierra el ciclo entre recomendación generada, acción ejecutada y medición de resultado real.

Ejemplo textual del CEO para anclar el diseño: si el Plan IA recomienda publicar un video vertical de TikTok sobre fallas del Metro con estructura narrativa similar a un video de Instagram exitoso del pasado, el cliente espera ver durante los días posteriores cómo evoluciona ese post específico en seguidores ganados, penetración real y comentarios específicos, no solo recibir la recomendación y olvidarla.

**Tres limitaciones graves del diseño sin cierre de ciclo (ya resueltas por D-17):**

1. Imposibilidad de distinguir empíricamente recomendaciones exitosas de fallidas
2. Sistema incapaz de aprender del histórico para calibrar recomendaciones futuras
3. Conversación comercial limitada a promesas cualitativas sin evidencia cuantitativa de desempeño acumulado (bloqueaba la métrica de tracción comercial a 90 días de §7.4)

**Diseño aprobado del ciclo en cinco fases:**

1. **Generación:** el Plan IA produce recomendación con anatomía completa §2.6.7 y la persiste en tabla `recomendaciones_plan_ia` con estado `propuesta`
2. **Decisión:** cliente acepta, rechaza o modifica la recomendación desde UI dedicada. Estado pasa a `aprobada`, `rechazada` o `modificada`
3. **Ejecución:** cliente publica el contenido. Sistema vincula `post_ejecutor_id` FK al post publicado. Estado pasa a `ejecutada`
4. **Seguimiento:** durante la ventana temporal configurada (default 14 días) el sistema rastrea métricas predichas y observadas, mostrando evolución contra baseline en UI dedicada
5. **Cierre:** al vencer la ventana, el sistema calcula veredicto automático (`exitosa`, `parcial`, `fallida`) por cumplimiento numérico del criterio. Estado pasa a `completada`. El cliente puede editar el veredicto si lo solicita. Resultado alimenta memoria del Plan IA

### §6.3.1 — Cuatro parámetros de diseño fijados por CEO

Las cuatro preguntas abiertas de la propuesta original quedan cerradas con las siguientes decisiones del CEO del 19 de abril de 2026:

**Parámetro 1 — Expansión del MVP:**
APROBADA expansión de 3-4 semanas a 4-5 semanas a cambio del cierre de ciclo completo desde el primer piloto. Razón CEO: un Plan IA sin seguimiento tiene techo comercial bajo porque el cliente sofisticado detecta la limitación en la primera conversación de venta.

**Parámetro 2 — Numeración de bloques nuevos:**
APROBADA numeración 10.5 y 10.7 sin renumerar el inventario completo de 30 bloques. Los bloques nuevos quedan como extensiones naturales del bloque #10 Start/Stop/Continue, preservando la numeración original que ya está referenciada en documentos de research y comunicación interna. Nueva suma total del inventario: 32 bloques efectivos.

**Parámetro 3 — Ventana de seguimiento:**
APROBADA ventana configurable por tipo de recomendación con default fijo de 14 días. Razón CEO enmarcada en economía del comportamiento: el default de 14 días establece el anchor cognitivo (Kahneman §2.6.1) apropiado para la mayoría de recomendaciones de consolidación digital, suficientemente largo para capturar evolución orgánica pero suficientemente corto para mantener cadencia semanal de revisión. La configurabilidad preserva agencia del cliente para casos donde el conocimiento contextual justifique ventana distinta (ejemplo: 7 días para posts virales de reacción rápida, 30 días para narrativas de mediano plazo sobre temas estructurales).

**Parámetro 4 — Mecánica del veredicto:**
APROBADO veredicto automático por cumplimiento numérico del criterio de éxito declarado en la recomendación original, con opción de edición por parte del cliente si lo solicita explícitamente. Razón CEO enmarcada en economía del comportamiento: el veredicto automático elimina la carga cognitiva de evaluación semanal (principio de System 1 vs System 2 de Kahneman §2.6.1) y preserva objetividad, mientras que la opción de edición manual preserva la autoridad profesional del cliente para casos donde el contexto no capturado por los números justifique ajuste. Esta arquitectura es superior al veredicto puramente automático porque preserva agencia sin sacrificar rigor, y superior al veredicto puramente manual porque no genera fricción operativa de revisión semanal obligatoria.

### §6.3.2 — Bloques nuevos agregados al inventario

Insertar en §3.2 Tier 1 Core del diagnóstico después del bloque #10:

**Bloque #10.5 — Seguimiento de Recomendaciones Activas**
- **Pregunta:** ¿Cómo evoluciona el post que publiqué siguiendo la recomendación de la semana pasada?
- **Fidelity:** T1 funciona con métricas públicas (likes, comments, shares, views). T3 enriquece con reach exacto, watch time y demographics de cohorte
- **Inputs:** tabla `recomendaciones_plan_ia` + `social_posts.id` del post ejecutor + snapshot diario de métricas + ventana temporal declarada (default 14 días, configurable)
- **Ejemplo visual:** sección permanente del dashboard con tarjetas de recomendaciones activas. Cada tarjeta muestra el texto de la recomendación original, el post ejecutor vinculado como preview embebido, gráfico temporal de métrica predicha versus observada durante la ventana, días restantes de evaluación, y semáforo de cumplimiento preliminar actualizado diariamente
- **Fuente:** D-17 (CEO 2026-04-19)
- **Componentes React requeridos:** adaptación de `KanbanBoard` existente (marcado 🟢 agnóstico en §3.5) más componente nuevo `RecommendationFollowUpCard` específico para este bloque

**Bloque #10.7 — Memoria del Plan IA**
- **Pregunta:** ¿De las últimas recomendaciones ejecutadas, cuáles funcionaron y cuáles no? ¿Qué patrones emergen?
- **Fidelity:** T1 funciona con data acumulada de seguimiento. Mejora cualitativa en T3 por precisión de métricas subyacentes
- **Inputs:** histórico completo de tabla `recomendaciones_plan_ia` con veredicto final, categorizado por tipo de acción, tema, plataforma y principio conductual de §2.6 que activó
- **Ejemplo visual:** dashboard histórico agregado mostrando tasa de éxito por categoría. Ejemplo textual: "Recomendaciones de video vertical sobre infraestructura: 8 exitosas de 10. Recomendaciones de réplica a crítico con fuente oficial INEGI: 5 exitosas de 7. Recomendaciones de post humanizante: 2 exitosas de 6". Incluye drill-down por recomendación individual con su evolución histórica y permite al cliente editar veredicto si lo considera necesario
- **Fuente:** D-17 (CEO 2026-04-19)
- **Función comercial:** este bloque alimenta la conversación de venta con evidencia documentada de desempeño acumulado en lugar de promesas. Crítico para cumplir la métrica de tracción comercial a 90 días de §7.4

### §6.3.3 — Tabla nueva de base de datos

Agregar al Sprint S1 Backend Foundations como migración Alembic adicional:

```sql
CREATE TABLE recomendaciones_plan_ia (
  id SERIAL PRIMARY KEY,
  plan_ia_id INTEGER REFERENCES planes_ia(id),
  dirigente_id INTEGER REFERENCES dirigentes(id),
  org_id INTEGER REFERENCES organizaciones(id),
  tipo VARCHAR(20) CHECK (tipo IN ('start', 'stop', 'continue')),
  accion_texto TEXT NOT NULL,
  ventana_inicio TIMESTAMP,
  ventana_fin TIMESTAMP,
  ventana_duracion_dias INTEGER DEFAULT 14,
  criterio_exito JSONB,
  principio_conductual VARCHAR(100),
  evidencia_respaldo JSONB,
  estado VARCHAR(20) DEFAULT 'propuesta' CHECK (estado IN (
    'propuesta', 'aprobada', 'rechazada', 'modificada',
    'ejecutada', 'completada', 'fallida'
  )),
  post_ejecutor_id INTEGER REFERENCES social_posts(id) NULL,
  metricas_predichas JSONB,
  metricas_observadas JSONB,
  veredicto VARCHAR(20) NULL CHECK (veredicto IN ('exitosa', 'parcial', 'fallida') OR veredicto IS NULL),
  veredicto_editado_por_cliente BOOLEAN DEFAULT FALSE,
  veredicto_original VARCHAR(20) NULL,
  notas_cliente TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_recom_dirigente_estado ON recomendaciones_plan_ia(dirigente_id, estado);
CREATE INDEX idx_recom_ventana_activa ON recomendaciones_plan_ia(ventana_fin) WHERE estado = 'ejecutada';
CREATE INDEX idx_recom_veredicto ON recomendaciones_plan_ia(dirigente_id, veredicto) WHERE estado = 'completada';
```

Notas sobre el esquema. El campo `ventana_duracion_dias` captura el parámetro 3 con default 14 y permite configurabilidad por recomendación. Los campos `veredicto_editado_por_cliente` y `veredicto_original` capturan el parámetro 4 preservando el veredicto automático del sistema cuando el cliente lo edita, para mantener trazabilidad de la diferencia entre evaluación algorítmica y juicio humano. Esta trazabilidad es valiosa para el bloque #10.7 Memoria del Plan IA porque permite identificar patrones de discrepancia sistemática entre sistema y cliente que pueden indicar recalibración necesaria del criterio de éxito.

### §6.3.4 — Impacto en roadmap de sprints

Actualizar §5 con los siguientes cambios.

**Sprint S1 Backend Foundations:** se añade migración Alembic para tabla `recomendaciones_plan_ia`. Impacto estimado: +1 hora al sprint. Nueva estimación total: 5-6 horas.

**Sprint S4 Plan IA LLM:** se expande el alcance original. El LLM ahora genera recomendaciones con formato estructurado persistible en tabla (no solo texto libre), la UI agrega flujo de decisión del cliente sobre cada recomendación con capacidad de aprobar, rechazar o modificar, se implementa lógica de seguimiento de ventana temporal con cálculo de veredicto automático al vencimiento, y se construye el bloque #10.7 Memoria del Plan IA como dashboard agregado con drill-down. Impacto estimado: +3-4 días al sprint. Nueva estimación total: 6-8 días.

**Sprint S2 Diagnóstico Tier 1:** sin impacto directo. Los dos bloques nuevos #10.5 y #10.7 se construyen en Sprint S4, no en S2.

**Sprint S3 Diferenciadores Tier 2:** sin impacto directo.

**Sprint S5 Meta OAuth activable:** sin impacto directo.

**Nuevo total del MVP:** 4-5 semanas en lugar de 3-4 semanas. Expansión formalmente aprobada por CEO en parámetro 1.

### §6.3.5 — Implicación UX secundaria positiva

La acción central del cliente cambia de "leer el reporte semanal" a "tomar decisión sobre cada recomendación propuesta y revisar seguimiento de recomendaciones activas". Esto convierte al producto en workflow activo en lugar de dashboard pasivo, generando hábito de uso semanal recurrente. Los productos analíticos consumidos como reporte tienen tasas de abandono altas después de la novedad inicial; los productos que demandan decisión explícita semanal generan compromiso recurrente. Este punto refuerza la retención del cliente y por tanto la métrica de tracción comercial a 90 días de §7.4.

### §6.3.6 — Actualización requerida de §7.4 métricas MVP

Modificar en §7.4 las métricas de MVP para reflejar el nuevo timeline de 4-5 semanas y agregar criterio específico del cierre de ciclo. Las tres métricas de tracción comercial a 90 días de §7.4 ya contemplan implícitamente el cierre de ciclo en la segunda métrica (caso documentado de recomendación ejecutada con resultado medible). Con D-17 aprobada, esta métrica queda técnicamente soportada por los bloques #10.5 y #10.7 en lugar de depender de evidencia reconstruida manualmente.

---

## Nota final para Joy

Esta propuesta consolidada ya incorpora las cuatro respuestas del CEO del 19 de abril de 2026 y se marca como 🟢 APROBADA directamente. No requiere ronda adicional de preguntas abiertas.

Cuando integres el MASTER v2.3 con los seis ajustes críticos de Gemini, agrega D-17 junto con D-16 (provider LLM) y D-18 (endpoint ARCO purge-hash) como el paquete completo de decisiones nuevas de la sesión del 19 de abril de 2026. El orden sugerido en la tabla de §6 es D-16, D-17, D-18 para preservar la llegada cronológica de las propuestas al proceso de decisión.

Los cambios downstream en otras secciones del MASTER que requiere D-17 son: actualizar §3.2 inventario con los dos bloques nuevos, actualizar §3.5 componentes React con la mención de `RecommendationFollowUpCard` como componente nuevo a construir, actualizar §5 Sprint S1 con la migración adicional, actualizar §5 Sprint S4 con el alcance expandido y nueva estimación, y modificar §7.4 métricas MVP para reflejar el timeline de 4-5 semanas.
