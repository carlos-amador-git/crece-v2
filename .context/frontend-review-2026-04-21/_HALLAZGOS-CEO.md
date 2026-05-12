# Hallazgos review frontend 2026-04-21 — CEO review manual

**Sesión:** 2026-04-21
**Reviewer:** CEO (MarxCha · manual, captura por captura)
**Capturas revisadas:** 13 PNG en `.context/frontend-review-2026-04-21/`
**Baseline de referencia:** 68 PNG en `.context/frontend-review-2026-04-20/`
**Scope:** Opción B · rutas críticas piloto + admin + puntos de entrada + dark mode + sesión Ballesteros
**Context operacional:** Revisor §9.8 (Claude.ai) al límite de uso hasta jueves. D-OPS-10 aplica unilateralmente desde Joy hasta restablecimiento.

---

## Resumen ejecutivo

**52 hallazgos** detectados · numeración F-17 → F-68 (continúa serie post-gate F-06..F-16) · distribuidos en 13 capturas y 11 rutas únicas.

### Severidad (lectura preliminar Joy)

| Severidad | Count | Ejemplos |
|---|---|---|
| 🔴 Crítica | 3 | F-28 `FODA[D]` literal al cliente · F-46 "Iniciar sesion" sin tilde · F-47 "Contrasena" sin ñ |
| 🟠 Funcional | 16 | Jerga interna, i18n en inglés, empty states sin patrón, landing sin prueba social, promesas sin contexto temporal |
| 🟡 Consistencia | 23 | Padding, formato fechas, paridad contadores, chevrons sin tooltip |
| 🟢 Nice-to-have | 10 | Sparklines, mejoras estéticas menores |

### Patrones globales (preliminar Joy — espera síntesis CEO)

1. **Jerga técnica expuesta al cliente** — 8+ instancias en 5 rutas (`FODA[D]`, `B11 T2`, `HITL §3.6`, `3 IAs deliberaron`, `Jaccard sobre captions`, `CIB (ITESO/DFRLab)`, `Fantasmas`, `rol_politico`).
2. **Acentuación española rota** — 3 instancias en login + branding (`sesion`, `Contrasena`, `ConsultoriaMD`). Impacta percepción calidad producto B2B mexicano.
3. **Inconsistencia empty states / error components** — 3 patrones distintos en 4 rutas (card vacío sin ícono en `/aceptacion`, "Failed to fetch" en inglés en `/admin/overview`, cerebro vs bandeja entre rutas).
4. **Paridad visual desigual** — Overview (p4-11) pulido + detalle dirigente (p1-05) radar vacío + gráfico ilegible. Gate pre-piloto priorizó Overview, detalle con backlog.
5. **Contexto temporal faltante** — 4+ instancias de números sin ventana (`0/12 promesas`, `↗ 100%`, `0 secciones`, `14 abr 2026, 12:27 a.m.` vs estándar mexicano).
6. **Prueba social ausente en landing** — único hallazgo crítico B2B. Ningún testimonial, logo de cliente, caso de estudio.
7. **Scope tenant vs dirigente ambiguo** — 2 instancias (alertas de org mostradas como si fueran del dirigente en p5-13, 4 recomendaciones MD-aprobadas de Ballesteros no aparecen como "planes" en p5-14).

### Índice por ruta

| Ruta | Captura | Hallazgos | IDs |
|---|---|---|---|
| /dashboard/planes (Piña) | p1-01 | 4 | F-17..F-20 |
| /dashboard/planes/13 | p1-02 | 4 | F-21..F-24 |
| /dashboard/planes/13/kanban | p1-03 | 4 | F-25..F-28 |
| /dashboard/aceptacion (UX, independiente del 500) | p1-04 | 2 | F-29..F-30 |
| /dashboard/dirigentes/1 (Piña, redirect) | p1-05-06 | 4 | F-31..F-34 |
| /dashboard/admin/plan-ia-review | p2-07 | 3 | F-35..F-37 |
| /dashboard/admin/overview (UX, independiente del 500) | p2-08 | 3 | F-38..F-40 |
| / (landing sin login) | p3-09 | 5 | F-41..F-45 |
| /login | p3-10 | 5 | F-46..F-50 |
| /dashboard dark (Piña) | p4-11 | 6 | F-51..F-56 |
| /dashboard/diagnostico-tier2/1 dark | p4-12 | 6 | F-57..F-62 |
| /dashboard (Ballesteros) | p5-13 | 4 | F-63..F-66 |
| /dashboard/planes (Ballesteros) | p5-14 | 2 | F-67..F-68 |

---

## Detalle por hallazgo

### F-17 — Tag versión compite con tag tipo en card Plan IA
- **Ruta:** /dashboard/planes
- **Captura:** p1-01-planes-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Primer card tiene tag `CONSOLIDACION` verde + `v2` gris oscuro; segundo `DIAGNOSTICO` azul + `v1` gris; tercero `CONSOLIDACION` verde + `v1` gris. La relación color↔tipo queda clara pero el chip de versión compite visualmente con el de tipo.
- **Propuesta:** Jerarquía: tipo dominante, versión secundaria (más chica o menos contraste).
- **Status:** pendiente

### F-18 — Formato fechas `a.m./p.m.` con punto inusual en español
- **Ruta:** /dashboard/planes
- **Captura:** p1-01-planes-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Formato `"14 abr 2026, 12:27 a.m."` — el formato es uniforme dentro de la captura pero `a.m./p.m.` en minúscula con punto es inusual en español mexicano. Normalmente sería `AM/PM` o formato 24h.
- **Propuesta:** Normalizar a formato 24h (`14 abr 2026, 00:27`) o AM/PM mayúscula sin punto.
- **Status:** pendiente

### F-19 — Chip "Borrador" indistinguible de botón filtro "Borrador"
- **Ruta:** /dashboard/planes
- **Captura:** p1-01-planes-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** El botón "Borrador" del filtro se ve visualmente idéntico al chip "Borrador" dentro de cada card. Confunde: "¿el chip del card es un botón filtro clickeable?" No es.
- **Propuesta:** Diferenciarlos — chip con border-only (status), botón con fondo sólido (filtro).
- **Status:** pendiente

### F-20 — IPD + followers pegados al nombre del dirigente en sidebar
- **Ruta:** /dashboard/planes (sidebar global)
- **Captura:** p1-01-planes-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** `IPD 2.6/10` + `12.8K` al pie del sidebar están muy pegados al nombre "Alejandro Piña Medina". Info útil pero sin aire vertical.
- **Propuesta:** Agregar padding vertical entre nombre y métricas secundarias.
- **Status:** pendiente

### F-21 — "0 de 5 tareas completadas" desalineado respecto al 0%
- **Ruta:** /dashboard/planes/13
- **Captura:** p1-02-plan-detalle-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** El label "0 de 5 tareas completadas" queda al extremo derecho de la barra, desconectado del número `0%`. Alineación rara.
- **Propuesta:** Label como subtítulo del `0%` o centrado bajo la barra.
- **Status:** pendiente

### F-22 — Contadores pendientes/curso/hechas con densidad baja
- **Ruta:** /dashboard/planes/13
- **Captura:** p1-02-plan-detalle-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Los 3 contadores (`5 pendientes` / `0 en curso` / `0 hechas`) están centrados cada uno en su tercio. Mucho espacio para 3 números pequeños.
- **Propuesta:** Más compacto o agregar sparkline / indicador visual.
- **Status:** pendiente

### F-23 — Input + botón "Registrar avance real" con hueco grande en medio
- **Ruta:** /dashboard/planes/13
- **Captura:** p1-02-plan-detalle-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Input alineado al borde izquierdo del container, botón "Actualizar" pegado al derecho, hueco grande de aire en medio.
- **Propuesta:** Input crece o quedan más juntos.
- **Status:** pendiente

### F-24 — Header card demasiado alto (padding vertical excesivo)
- **Ruta:** /dashboard/planes/13
- **Captura:** p1-02-plan-detalle-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Tags del header (`foda-derived-v3`, metadata derecha) bien, pero el card del header es muy alto. Puede ser 20-30% más compacto.
- **Propuesta:** Reducir padding vertical del header card.
- **Status:** pendiente

### F-25 — Columnas vacías Kanban = bloques de color sin empty state
- **Ruta:** /dashboard/planes/13/kanban
- **Captura:** p1-03-plan-kanban-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Columnas `En curso = 0` y `Hecho = 0` se ven como grandes bloques de color (amarillo/verde) sin contenido. Desproporcionado visualmente.
- **Propuesta:** Empty state explícito ("Ninguna tarea en curso" con ícono tenue).
- **Status:** pendiente

### F-26 — Progreso redundante con headers de columnas Kanban
- **Ruta:** /dashboard/planes/13/kanban
- **Captura:** p1-03-plan-kanban-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Progreso arriba dice `"0% ejecutado · Total: 5 · Hecho: 0 · En curso: 0 · Por hacer: 5"` — redundante con los headers de columnas (Por hacer = 5, En curso = 0, Hecho = 0).
- **Propuesta:** Quitar redundancia o mostrar progreso como indicador único más visual.
- **Status:** pendiente

### F-27 — Chevrons al fondo de cada card Kanban sin tooltip/label
- **Ruta:** /dashboard/planes/13/kanban
- **Captura:** p1-03-plan-kanban-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Los chevrons `>` al fondo de cada card — no queda claro qué hacen. ¿Expanden? ¿Navegan?
- **Propuesta:** Tooltip o label explícito ("Avanzar estado" / "Expandir detalles").
- **Status:** pendiente

### F-28 — `FODA[D]:` literal expuesto al cliente
- **Ruta:** /dashboard/planes/13/kanban
- **Captura:** p1-03-plan-kanban-pina.png
- **Severidad:** 🔴 crítica (nomenclatura interna visible al usuario final)
- **Observación:** Tipografía `"FODA[D]:"` al inicio de cada tarea — código/tag técnico expuesto al usuario final. Piña no debería ver `FODA[D]` literalmente.
- **Propuesta:** Etiqueta humana ("Debilidad detectada:") o ícono distintivo sin código.
- **Status:** pendiente

### F-29 — Mensaje de error demasiado discreto en /aceptacion
- **Ruta:** /dashboard/aceptacion
- **Captura:** p1-04-aceptacion-pina.png
- **Severidad:** 🟠 funcional (independiente del bug de schema D-OPS-07)
- **Observación:** "No se pudo cargar el Índice de Aceptación" en texto plano dentro de card vacío. Sin ícono de error, sin color de severidad, sin CTA de "reintentar" o "contactar soporte". Para Piña parece "la página no existe".
- **Propuesta:** Componente de error unificado — icono alerta naranja/rojo + mensaje + acción sugerida (retry/soporte).
- **Status:** pendiente

### F-30 — "Fantasmas" jerga interna en subnavegación sidebar
- **Ruta:** sidebar (global)
- **Captura:** p1-04-aceptacion-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Sidebar abre sección "Indice Aceptacion" con subitems (Overview/Por dirigente/Fantasmas). "Fantasmas" es jerga interna del framework NLP.
- **Propuesta:** Rename a "Sin datos" / "Cuentas dormidas" según semántica real.
- **Status:** pendiente

### F-31 — Gráfico Sentimiento (30 días) ilegible
- **Ruta:** /dashboard/dirigentes/1
- **Captura:** p1-05-06-dirigente-redirect-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Masa compacta de barras verticales rojas/verdes/amarillas tan juntas que no se distingue ninguna lectura. Eje X tiene muchas fechas mezcladas con formato ambiguo (`13/5`, `1/12`, `12/1`, `9/5`). Aún seleccionando "Línea" y "%" el render es ilegible. Los toggles Línea/Barras + %/N del cherry-pick `7f44130` están presentes pero el layout de datos no lo aprovecha.
- **Propuesta:** Revisar densidad de datos, formato de fecha (`dd/MM/yy` completo) y separadores visuales.
- **Status:** pendiente

### F-32 — Radar IPD vacío/casi vacío — empty state confuso
- **Ruta:** /dashboard/dirigentes/1
- **Captura:** p1-05-06-dirigente-redirect-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Solo se ve un pequeño triángulo en YouTube, resto en cero. Un radar con valores cerca de 0 se ve "roto" aunque sea data real.
- **Propuesta:** Empty state explícito cuando todos los valores son < threshold, o pintar los ejes con mayor contraste para diferenciar "sin data" vs "data baja".
- **Status:** pendiente

### F-33 — "0 secciones" sin contexto en header
- **Ruta:** /dashboard/dirigentes/1
- **Captura:** p1-05-06-dirigente-redirect-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** `"0 secciones"` aparece sin contexto. ¿Secciones de qué? ¿Electorales? ¿Territoriales?
- **Propuesta:** Tooltip o label explícito (`"0 secciones electorales con datos"`).
- **Status:** pendiente

### F-34 — Botones handle social sin el handle real visible
- **Ruta:** /dashboard/dirigentes/1
- **Captura:** p1-05-06-dirigente-redirect-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Botones de red social muestran literalmente `"@"` + ícono de plataforma, sin el handle real (`@alejandro.pinha`).
- **Propuesta:** Mostrar el `@nombre` real como label visible, o tooltip al hover.
- **Status:** pendiente

### F-35 — "HITL §3.6" jerga de protocolo en título admin
- **Ruta:** /dashboard/admin/plan-ia-review
- **Captura:** p2-07-admin-plan-ia-review.png
- **Severidad:** 🟠 funcional
- **Observación:** Título `"Plan IA · Cola MD Review (HITL §3.6)"` — código de sección MASTER interno. Si otro admin entra (Bruno, Rafael) los confunde.
- **Propuesta:** Tooltip con expansión ("Human-In-The-Loop") o quitar el código del título. Admin sabe qué revisa.
- **Status:** pendiente

### F-36 — "9 aprobadas visibles" sin contexto de a quién
- **Ruta:** /dashboard/admin/plan-ia-review
- **Captura:** p2-07-admin-plan-ia-review.png
- **Severidad:** 🟡 consistencia
- **Observación:** Badge dice `"9 aprobadas visibles"` — OK pero ¿visibles para quién? ¿Al cliente? ¿Al admin?
- **Propuesta:** `"9 aprobadas publicadas al cliente"` o equivalente explícito.
- **Status:** pendiente

### F-37 — "Refrescar" button con icono ambiguo
- **Ruta:** /dashboard/admin/plan-ia-review
- **Captura:** p2-07-admin-plan-ia-review.png
- **Severidad:** 🟢 nice-to-have
- **Observación:** Botón "Refrescar" con ícono spinner. Label genérico.
- **Propuesta:** Label más explícito: `"Actualizar cola"` o similar.
- **Status:** pendiente

### F-38 — i18n bug: "Failed to fetch" en inglés en UI español
- **Ruta:** /dashboard/admin/overview
- **Captura:** p2-08-admin-overview.png
- **Severidad:** 🟠 funcional (independiente del bug de schema D-OPS-07)
- **Observación:** Error `"Failed to fetch"` en inglés en interfaz en español. El error del backend se filtra crudo al usuario.
- **Propuesta:** Mensaje localizado: `"No se pudieron cargar los datos"` + acción sugerida.
- **Status:** pendiente

### F-39 — "Operacion de flota" semántica dudosa en sidebar admin
- **Ruta:** sidebar admin
- **Captura:** p2-08-admin-overview.png
- **Severidad:** 🟡 consistencia
- **Observación:** Primer item sidebar admin dice `"Operacion de flota"`. "Flota" sugiere vehículos/logística. ¿Es el label correcto?
- **Propuesta:** Mirar con fresh eyes — posible `"Panel operativo"` / `"Operación de la plataforma"` / `"Operaciones"`.
- **Status:** pendiente · requiere clarificación CEO sobre intención semántica

### F-40 — Error component sin patrón unificado (replica F-29)
- **Ruta:** /dashboard/admin/overview
- **Captura:** p2-08-admin-overview.png
- **Severidad:** 🟠 funcional
- **Observación:** Mismo patrón que F-29 — error sin ícono de severidad, sin acción sugerida.
- **Propuesta:** Aplicar componente de error unificado (ver F-29).
- **Status:** pendiente · agrupar con F-29

### F-41 — Enorme espacio vertical vacío entre grid módulos y footer (landing)
- **Ruta:** / (landing)
- **Captura:** p3-09-landing-sinlogin.png
- **Severidad:** 🟠 funcional
- **Observación:** ~50% del scroll es vacío entre la grid de 6 módulos y el footer. Mata percepción de "página completa". Causas posibles: (a) secciones no cargadas por error render, (b) scroll animation que no disparó, (c) genuinamente vacío intencional.
- **Propuesta:** Diagnosticar causa, poblar con prueba social (ver F-44) o ajustar layout.
- **Status:** pendiente · diagnosticar causa primero

### F-42 — "48hrs" sin espacio — se ve como errata
- **Ruta:** / (landing)
- **Captura:** p3-09-landing-sinlogin.png
- **Severidad:** 🟢 nice-to-have
- **Observación:** `"48hrs"` junto sin espacio. Debería ser `"48 hrs"`.
- **Propuesta:** Agregar espacio.
- **Status:** pendiente

### F-43 — Mockup dashboard arriba-derecha muy pequeño y comprimido
- **Ruta:** / (landing)
- **Captura:** p3-09-landing-sinlogin.png
- **Severidad:** 🟠 funcional
- **Observación:** Los detalles del mockup no se leen. Parece decorativo más que probatorio. Si el objetivo es mostrar producto, debería ser más grande o tener zoom.
- **Propuesta:** Agrandar mockup o habilitar modal/lightbox zoom.
- **Status:** pendiente

### F-44 — Falta prueba social (crítico B2B)
- **Ruta:** / (landing)
- **Captura:** p3-09-landing-sinlogin.png
- **Severidad:** 🟠 funcional
- **Observación:** No hay logos de clientes, testimoniales, casos de estudio. Los números son abstractos (145+ endpoints). Para un SaaS B2B con ticket alto dirigido a dirigentes políticos, el "¿quién más lo usa?" es crítico.
- **Propuesta:** Agregar sección de prueba social. Candidatos iniciales: MC CDMX (MC logo + anonymized dirigente testimonial), ConsultoriaMD proyectos previos.
- **Status:** pendiente · requiere aprobación legal CEO para testimoniales

### F-45 — Nav "Métricas" ambiguo
- **Ruta:** / (landing nav superior)
- **Captura:** p3-09-landing-sinlogin.png
- **Severidad:** 🟡 consistencia
- **Observación:** Items nav `Capacidades / Proceso / Métricas` — limpio, pero "Métricas" es ambiguo. ¿Métricas del producto? ¿Métricas del cliente?
- **Propuesta:** Renombrar a `"Resultados"` / `"Indicadores"` / específico según sección destino.
- **Status:** pendiente

### F-46 — "Iniciar sesion" sin tilde
- **Ruta:** /login
- **Captura:** p3-10-login-sinbotones-demo.png
- **Severidad:** 🔴 crítica (producto B2B mexicano serio)
- **Observación:** `"Iniciar sesion"` sin tilde en título `h2` del form.
- **Propuesta:** `"Iniciar sesión"`.
- **Status:** pendiente · fix trivial

### F-47 — "Contrasena" sin ñ (label + placeholder)
- **Ruta:** /login
- **Captura:** p3-10-login-sinbotones-demo.png
- **Severidad:** 🔴 crítica (producto B2B mexicano serio)
- **Observación:** `"Contrasena"` aparece dos veces — en label y en placeholder `"Tu contrasena"`.
- **Propuesta:** `"Contraseña"` en ambos casos.
- **Status:** pendiente · fix trivial · CRÍTICO para percepción marca

### F-48 — "ConsultoriaMD" sin tilde y sin espacio — branding errata
- **Ruta:** /login (lado izquierdo)
- **Captura:** p3-10-login-sinbotones-demo.png
- **Severidad:** 🟠 funcional
- **Observación:** Muestra `"ConsultoriaMD"`. Branding real de la empresa es `"MD Consultoría SC"`.
- **Propuesta:** Corregir a `"MD Consultoría"` o `"MD Consultoría SC"` para consistencia con brand oficial.
- **Status:** pendiente · branding

### F-49 — Bullets de features del lado izquierdo con contraste bajo
- **Ruta:** /login (split panel izquierdo)
- **Captura:** p3-10-login-sinbotones-demo.png
- **Severidad:** 🟠 funcional (accesibilidad)
- **Observación:** Los 3 bullets con iconos + texto sobre fondo azul oscuro — color gris oscuro, apenas distinguibles. Accesibilidad WCAG AA cuestionable.
- **Propuesta:** Aumentar contraste del texto / iconos (blanco o gris claro).
- **Status:** pendiente · auditar WCAG

### F-50 — "CRECE v2.0" expuesto al cliente
- **Ruta:** /login (texto bajo formulario)
- **Captura:** p3-10-login-sinbotones-demo.png
- **Severidad:** 🟢 nice-to-have
- **Observación:** Versioning interno `"CRECE v2.0"` visible al cliente. OK si intencional, pero mejor reservarlo para footer o tooltip técnico.
- **Propuesta:** Mover a footer o tooltip.
- **Status:** pendiente

### F-51 — "3 IAs deliberaron" jerga interna en badge
- **Ruta:** /dashboard (dark mode, Piña)
- **Captura:** p4-11-dashboard-dark-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Badge verde `"Analisis Contextual · 3 IAs deliberaron"` — concepto bueno pero "3 IAs deliberaron" es jerga del framework NLP 3-capas.
- **Propuesta:** Tooltip expansivo (`"Análisis cruzado por 3 modelos de IA para mayor confiabilidad"`) o simplificar label.
- **Status:** pendiente

### F-52 — "↗ 100%" sin contexto de periodo
- **Ruta:** /dashboard (card Tu Audiencia)
- **Captura:** p4-11-dashboard-dark-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** `"↗ 100%"` junto a `"Tu Audiencia 12.8K"` — asume que el user sabe que 100% es crecimiento del periodo activo.
- **Propuesta:** `"+100% este mes"` o explícito con el filtro de periodo activo.
- **Status:** pendiente

### F-53 — "IPD sobre 10" con "—" ambiguo
- **Ruta:** /dashboard (card Presencia Digital)
- **Captura:** p4-11-dashboard-dark-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** `"2.6/10"` con `"—"` como indicador de cambio. ¿Sin cambio? ¿No hay datos históricos?
- **Propuesta:** Label explícito (`"sin cambio"` / `"sin historial"`).
- **Status:** pendiente

### F-54 — "320 posts ↗ 100%" relación no obvia
- **Ruta:** /dashboard (card Conversación)
- **Captura:** p4-11-dashboard-dark-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** `"320 Posts monitoreados en el periodo"` con `"↗ 100%"` al lado. ¿320 es crecimiento 100%? ¿O 320 posts crecieron 100%?
- **Propuesta:** Separar la métrica del delta, usar formato `"320 posts · +100% vs periodo anterior"`.
- **Status:** pendiente

### F-55 — Paridad Overview vs detalle dirigente desigual (crítico)
- **Ruta:** /dashboard vs /dashboard/dirigentes/1
- **Captura:** p4-11 (Overview excelente) vs p1-05-06 (detalle roto)
- **Severidad:** 🟠 funcional
- **Observación:** Overview (p4-11) tiene datos ricos, KPIs bien presentados, cards limpios. Detalle dirigente (p1-05) tiene radar vacío + gráfico ilegible. Gate pre-piloto priorizó Overview, detalle quedó menos pulido.
- **Propuesta:** Sprint dedicado a paridad de calidad en detalle dirigente — aplicar mismas prácticas de KPI + empty states + iconografía.
- **Status:** pendiente · sprint

### F-56 — Filtros de periodo compiten visualmente con header
- **Ruta:** /dashboard (header)
- **Captura:** p4-11-dashboard-dark-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Filtros `Hoy / 7 días / 30 días / 90 días` arriba derecha. Compiten visualmente con search, theme toggle, notif, avatar del mismo header.
- **Propuesta:** Agrupar en subheader separado o cambiar estilo (menos prominente).
- **Status:** pendiente

### F-57 — "B11 T2", "B12 T2" etc. — códigos de bloque expuestos al cliente
- **Ruta:** /dashboard/diagnostico-tier2/1
- **Captura:** p4-12-tier2-dark-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Etiquetas técnicas `B11 T2`, `B12 T2` ... `B18 T2` visibles como parte del título de cada bloque. Nomenclatura interna MASTER §3.2.
- **Propuesta:** Título solo con nombre humano (`"Cross-Partisan Validation"`), código en tooltip o metadata oculta.
- **Status:** pendiente · aplica a 8 bloques del Tier 2

### F-58 — "CIB Detector (ITESO/DFRLab)" acrónimos sin explicación
- **Ruta:** /dashboard/diagnostico-tier2/1 (bloque B12)
- **Captura:** p4-12-tier2-dark-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Acrónimos `CIB` (Coordinated Inauthentic Behavior) e `ITESO/DFRLab` sin explicación. Piña no sabe qué significa.
- **Propuesta:** Tooltip expansivo con glosario.
- **Status:** pendiente

### F-59 — Hashes de autor Twitter truncados sin handle legible
- **Ruta:** /dashboard/diagnostico-tier2/1
- **Captura:** p4-12-tier2-dark-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Hashes tipo `"f0c397abec68..."`, `"6558fd1bbb59..."` visibles. Son `author_hash` (privacidad LFPDPPP — correcto técnicamente) pero sin handle resuelto ni persona.
- **Propuesta:** Resolver a handle (`@user`) o persona name si se tiene cache, manteniendo hash hidden para privacidad.
- **Status:** pendiente · revisar implicaciones LFPDPPP

### F-60 — Tag "maestro_ceremonias" duplicado en mismo card
- **Ruta:** /dashboard/diagnostico-tier2/1 (bloque específico)
- **Captura:** p4-12-tier2-dark-pina.png
- **Severidad:** 🟡 consistencia
- **Observación:** Tag `"maestro_ceremonias"` aparece dos veces seguidas en el mismo card. Parece redundante.
- **Propuesta:** Revisar lógica de render — deduplicar tags o verificar si es intencional (ej. dos categorías distintas con mismo valor).
- **Status:** pendiente · bug posible

### F-61 — "Jaccard sobre captions" jerga técnica NLP
- **Ruta:** /dashboard/diagnostico-tier2/1 (bloque B14 Topic Drift)
- **Captura:** p4-12-tier2-dark-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Texto literal `"Jaccard sobre captions"` expone término de similitud estadística al cliente.
- **Propuesta:** Tooltip expansivo (`"Similitud Jaccard: mide overlap entre palabras de distintos posts"`) o reformular con lenguaje común.
- **Status:** pendiente

### F-62 — "Rastreador Promesas 0/12 cumplidas" sin contexto temporal
- **Ruta:** /dashboard/diagnostico-tier2/1 (bloque B16 Promesas)
- **Captura:** p4-12-tier2-dark-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** `"0/12 promesas cumplidas · Pendientes 12 · 100%"` con barra roja grande. Lectura demoledora. Asumiendo data real, valioso diferenciador pero necesita contexto: ¿cuándo se midió? ¿qué periodo? ¿fecha_compromiso ya vencida o aún en curso?
- **Propuesta:** Agregar ventana temporal explícita + distinguir "vencidas sin cumplir" vs "aún dentro de plazo".
- **Status:** pendiente · data integrity

### F-63 — Sidebar "Indice Aceptacion" expandido inconsistente entre sesiones
- **Ruta:** sidebar global (Piña vs Ballesteros)
- **Capturas:** p4-11 (Piña dark, no expandido) vs p1-04 (Piña claro, expandido) vs p5-13 (Ballesteros claro, expandido)
- **Severidad:** 🟡 consistencia
- **Observación:** Sidebar de Piña en dark mode (p4-11) NO muestra `"Indice Aceptacion"` expandido. Pero sí en modo claro (p1-04). Y sí para Ballesteros (p5-13, claro). Puede ser diferencia de scroll state, hover, o permisos.
- **Propuesta:** Verificar que ambos dirigentes vean la misma estructura independientemente de modo claro/oscuro y scroll state.
- **Status:** pendiente · bug state management posible

### F-64 — Alertas de Crisis compartidas por org — ambigüedad de scope
- **Ruta:** /dashboard (card Alertas de Crisis)
- **Captura:** p5-13-dashboard-ballesteros.png vs p4-11-dashboard-dark-pina.png
- **Severidad:** 🟠 funcional
- **Observación:** Misma lista de 3 alertas aparece para Ballesteros y Piña. ¿Las alertas son scoped por org (MC-CDMX) y no por dirigente? Tiene sentido conceptualmente pero puede confundir al usuario — Ballesteros espera ver SUS alertas.
- **Propuesta:** Clarificar visualmente que alertas son de org (label `"Alertas de Crisis · Movimiento Ciudadano CDMX"`) o scope a dirigente específico si ese es el intent.
- **Status:** pendiente · revisar intención de diseño

### F-65 — Facebook = 0 seguidores Ballesteros — ¿real o bug scraper?
- **Ruta:** /dashboard (card Seguidores por Plataforma, Ballesteros)
- **Captura:** p5-13-dashboard-ballesteros.png
- **Severidad:** 🟡 consistencia
- **Observación:** Twitter 55.6K, Instagram 32.0K, YouTube 1.2K, **Facebook 0**.
- **Propuesta:** Verificar si es data real (Ballesteros no tiene FB) o bug de scraper. Si real, empty state explícito (`"Sin perfil configurado"`).
- **Status:** pendiente · data validation

### F-66 — Total "88.8K" visible en Ballesteros pero no paridad confirmada en Piña
- **Ruta:** /dashboard (card Seguidores por Plataforma)
- **Captura:** p5-13 (Ballesteros) vs p4-11 (Piña)
- **Severidad:** 🟢 nice-to-have
- **Observación:** Total 88.8K aparece claramente abajo de lista en Ballesteros. No veo claramente el total en Piña (p4-11).
- **Propuesta:** Revisar paridad — ambos deben tener el total visible con mismo estilo.
- **Status:** pendiente

### F-67 — Discrepancia "No hay planes" vs 4 recomendaciones MD-aprobadas
- **Ruta:** /dashboard/planes (Ballesteros)
- **Captura:** p5-14-planes-ballesteros.png
- **Severidad:** 🟠 funcional (conceptual · scope de entidades)
- **Observación:** Ballesteros tiene 4 recomendaciones MD-aprobadas (context sesión). Pero `/dashboard/planes` dice "No hay planes". Discrepancia: las 4 recomendaciones ¿no son "planes"? ¿Viven en `/dashboard/recomendaciones`?
- **Propuesta:** Clarificar la distinción Plan vs Recomendación en UI — badge que cross-references (`"Ver también: 4 recomendaciones aprobadas"`) o unificar taxonomía.
- **Status:** pendiente · requiere decisión conceptual

### F-68 — Empty state iconografía inconsistente (cerebro vs bandeja)
- **Ruta:** /dashboard/planes (Ballesteros) vs /dashboard/admin/plan-ia-review
- **Capturas:** p5-14 (cerebro) vs p2-07 (bandeja)
- **Severidad:** 🟡 consistencia
- **Observación:** `/dashboard/planes` usa ícono cerebro para "No hay planes". `/dashboard/admin/plan-ia-review` usa ícono bandeja para "Cola vacía". Patrón inconsistente.
- **Propuesta:** Unificar criterio iconografía empty states — ícono debería representar la entidad ausente (plan = documento/checklist, cola = bandeja).
- **Status:** pendiente · design system coherence

---

## Clasificación operativa (post-hallazgo, pre-sprint)

### 🔴 Críticas (3) — fix inmediato antes de demo al cliente
- F-28 `FODA[D]:` literal al cliente (Kanban)
- F-46 "Iniciar sesion" sin tilde
- F-47 "Contrasena" sin ñ

### 🟠 Funcional (16) — atacar en sprints cortos
- Jerga técnica: F-29 (retry CTA), F-30 (Fantasmas), F-35 (HITL §3.6), F-38 (i18n), F-51 (3 IAs), F-57 (B11 T2 ×8 bloques), F-58 (CIB), F-61 (Jaccard)
- Empty states / errors: F-40 (admin/overview unificar con F-29)
- Landing: F-41 (espacio vacío), F-43 (mockup pequeño), F-44 (prueba social)
- Branding: F-48 (ConsultoriaMD)
- Accesibilidad: F-49 (contraste login)
- Paridad: F-55 (Overview vs detalle)
- Data: F-62 (promesas sin contexto)
- Scope: F-64 (alertas org vs dirigente), F-67 (planes vs recomendaciones)

### 🟡 Consistencia (23)
Todos los relacionados a padding, formato, alineación, label tuning — agrupables en sprint UI polish.

### 🟢 Nice-to-have (10)
Diferibles §9.8 intermedia o backlog.

---

## Pendiente de CEO (no escribir por Joy)

- Síntesis por patrones (versión CEO, no la preliminar de Joy)
- Recomendación de priorización (cuál sprint primero)
- Confirmación severidad F-28, F-46, F-47 como 🔴 críticas o ajuste
- Decisión sobre F-39 "Operacion de flota" — cuál es el label correcto
- Aprobación legal F-44 (testimoniales prueba social)
