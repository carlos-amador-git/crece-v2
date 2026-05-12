# Auditoría Gemini — CRECE_PRODUCT_MASTER v2.2

**Fecha:** 2026-04-19 (post-merge PR #16)
**Revisor:** Gemini CLI (Puerta 2 según §9.7 del MASTER)
**Revisor previo (Puerta 1):** Claude.ai Opus 4.7 — aprobado con distinción

---

**VEREDICTO GLOBAL: Aprobado con ajustes específicos.** (Puerta 2 superada, pero con riesgos críticos de SPOF técnico y gaps de gobernanza de datos).

---

### 1 · CONTRADICCIONES INTERNAS
**01 · ESTRUCTURA · §2.5 vs §3.5 · Dualidad del IPD**  
**CRÍTICA:** El plan declara que el IPD "muere o pivota" a métrica secundaria, pero el inventario de componentes (§3.5) y la UI de la Sidebar (§2.2) lo mantienen como headline.  
**SUGERENCIA CONCRETA:** (Mejora) Renombrar `IpdRadarChart` a `SecondaryContextRadar` y crear un nuevo `Tier1CoreGrid` como componente principal de entrada en el Dashboard.

**02 · IA · §3.1 #10 vs §6 D-15 · Provider de Plan IA**  
**CRÍTICA:** La definición del bloque #10 menciona "Claude/Gemma", pero la decisión D-15 formaliza a Gemma local como "Provider Primario". La ambigüedad en la fuente de verdad del LLM puede causar deriva de costos imprevista.  
**SUGERENCIA CONCRETA:** (Crítico - S1) Unificar todo el PRD técnico bajo Gemma 3:12b como baseline de desarrollo, dejando a Claude exclusivamente como "Expert Auditor" de seguridad.

---

### 2 · GAPS ESTRUCTURALES
**03 · ESCALABILIDAD · §4.2 · Límite Meta Dev Mode**  
**CRÍTICA:** El plan no contempla el límite de 25 usuarios/dirigentes del "App Mode: Development" de Meta. Llegar al dirigente 26 sin haber pasado App Review es un riesgo de negocio inminente.  
**SUGERENCIA CONCRETA:** (Mejora - S5) Incluir el hito "Meta App Review Submission" en el Sprint S5 para asegurar la transición de "Development" a "Live" antes de la escala comercial.

**04 · GOBERNANZA · §2.2 · Ciclo de Vida del Dato (ARCO)**  
**CRÍTICA:** Se menciona retención de 180 días, pero no existe un mecanismo para el borrado selectivo solicitado por un ciudadano (Derechos ARCO). El hash SHA256 ayuda, pero no exime de la obligación de purga.  
**SUGERENCIA CONCRETA:** (Crítico - S1) Implementar un endpoint `POST /admin/compliance/purge-hash` que elimine recursivamente comentarios y vectores asociados a un autor específico.

**05 · MIGRACIÓN · §4.4 · Reconciliación T1/T2 a T3**  
**CRÍTICA:** No se define qué ocurre con la serie de tiempo cuando un dirigente pasa de "Estimación" (scraping) a "Oficial" (API). La divergencia de datos romperá los gráficos de tendencias.  
**SUGERENCIA CONCRETA:** (Crítico - S1) Añadir un campo `data_origin_checkpoint` en la tabla de métricas para marcar visualmente en el frontend dónde termina la estimación y dónde empieza el dato oficial.

---

### 3 · RIESGOS NO DOCUMENTADOS (MX 2026-2027)
**06 · INFRAESTRUCTURA · §2.1 · SPOF de Hardware (Local LLM)**  
**CRÍTICA:** Operar producción sobre un solo Mac M4 local es un "Single Point of Failure" inaceptable para un SaaS. Un fallo de disco o luz detiene el Plan IA de todos los clientes.  
**SUGERENCIA CONCRETA:** (Crítico - S1) Definir un clúster de Ollama en Coolify (§8.6) como failover automático si el nodo local Mac M4 deja de responder (health-check).

---

### 4 · DEPENDENCIAS OCULTAS
**07 · ESTRATEGIA · §2.6 vs §5 S4 · Behavioral Prompting**  
**CRÍTICA:** El Sprint S4 (Plan IA) asume que el LLM conocerá la economía conductual, pero no hay una tarea de "Ingeniería de Prompts Conductuales" explícita.  
**SUGERENCIA CONCRETA:** (Mejora - S4) Crear un `behavioral_logic_library.json` que el RAG inyecte sistemáticamente al LLM para forzar la justificación conductual exigida en §2.6.7.

---

### 5 · OBSERVACIONES PLAN IA (SPRINT S4)
**08 · CALIDAD · §3.1 #10 · Alucinación en Recomendaciones**  
**CRÍTICA:** Gemma 12b en temas políticos mexicanos puede sugerir acciones que violen la veda o el tono institucional sin supervisión humana.  
**SUGERENCIA CONCRETA:** (Crítico - S4) Implementar un "Human-in-the-loop" flag para el equipo de MD Consultoría antes de que una recomendación del Plan IA sea visible para el cliente final.

---

### 6 · SPRINT S0 VALIDACIÓN
**09 · VALIDACIÓN · §5 S0 · Benchmarking de Emociones**  
**CRÍTICA:** El Sprint S0 valida ER y CIB, pero no valida si Gemma 12b es capaz de clasificar las 6 emociones Plutchik (§3.1 #05) con la precisión requerida para política.  
**SUGERENCIA CONCRETA:** (Crítico - S0) Añadir tarea T0.4: "Clasificación ciega de 100 comments (Plutchik) Gemma vs Humano". Aceptación: >75% de coincidencia en emoción dominante.

---

_Generado: 2026-04-19T14:13:00Z_
