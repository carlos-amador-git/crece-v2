# CRECE v2.0 — Guion Demo Interna (30 min)

**Audiencia:** Equipo MC CDMX + dirigentes piloto
**Fecha sugerida:** Abril 2026
**Prerrequisitos:**
- Docker containers corriendo (`make dev` o `docker compose up -d`)
- Ollama local con gemma3:12b (`curl http://localhost:11434/api/tags`)
- Browser abierto en `http://localhost:3005`

**Credenciales:**
- Admin: `admin@consultoriamd.com` / `crece2026!`
- Piña: `pina@crece.mx` / `demo2026!`
- Solano: `solano@crece.mx` / `demo2026!`

---

## Escena 1 — Intro (0:00 - 2:00)

**Login:** No loggearse todavía. Mostrar la pantalla de login.

**Hablar:**
> "CRECE v2.0 reemplaza el sistema Oracle APEX que usaban. Mismo objetivo —
> inteligencia electoral para MC CDMX — pero con tecnología moderna:
> análisis de redes sociales en tiempo real, mapas interactivos,
> planes de acción generados por IA, y datos de 9,723 ciudadanos reales
> de las 3 alcaldías piloto."

**Mostrar:** Los 3 botones de acceso demo (Admin, Piña, Solano).

> "Cada usuario ve SOLO sus datos. Piña no ve los de Solano.
> El admin ve todo. Vamos a empezar como Piña."

---

## Escena 2 — Dashboard del Político (2:00 - 8:00)

**Login como Piña** (click botón "Alejandro Piña").

### 2a. Overview (2:00 - 4:00)
- Mostrar los 4 KPIs: Audiencia Total, posts monitoreados, alertas
- Señalar el periodo selector (Hoy / 7d / 30d) — cambiar y ver que refresca
- Sidebar: notar que dice "Alejandro Piña" con su rol

### 2b. Social (4:00 - 6:00)
- Ir a `/dashboard/social`
- Mostrar la lista de posts con sentimiento real (NLP pysentimiento)
- Señalar: "Esto NO es un mockup — son posts reales scrapeados de @Alejandro_Pinha y @alejandro.pinha"
- Filtrar por plataforma (Twitter vs Instagram)
- Mostrar el pie chart de sentimiento — distribución real, no 100% neutral
- Si hay trends card: mostrar trending en alcaldía

### 2c. Dirigentes (6:00 - 8:00)
- Ir a `/dashboard/dirigentes`
- Mostrar que Piña ve SOLO su perfil (RLS en acción)
- Mostrar IPD score, plataformas conectadas, followers

**Punto clave:**
> "Todo esto es automático. Los scrapers corren cada X horas,
> el NLP procesa sentimiento, y los KPIs se actualizan solos."

---

## Escena 3 — Mapa de Canvassing (8:00 - 14:00)

**Logout → Login como Admin.**

### 3a. Vista general (8:00 - 10:00)
- Ir a `/dashboard/canvassing`
- Mostrar stats bar: "9,723 ciudadanos, 9,631 con geolocalización"
- Señalar el mapa con clusters

> "Estos son los 9,723 ciudadanos reales del sistema CRECE original.
> 99% tienen coordenadas GPS. Los importamos de Oracle APEX."

### 3b. Filtros en acción (10:00 - 12:00)
- Filtrar por **Benito Juárez** → mapa se actualiza a 812 ciudadanos
- Cambiar a **Cuauhtémoc** → 6,642 ciudadanos
- Filtrar por **estrato "MUY BAJO"** → ver las zonas rojas
- Cambiar color mode a **"Por Participación"** → colores cambian

> "Esto es la killer feature: saber exactamente a quién visitar y dónde,
> segmentado por volatilidad electoral y estrato socioeconómico."

### 3c. Detalle de ciudadano (12:00 - 14:00)
- Hacer zoom hasta ver puntos individuales
- Click en un punto → popup con datos: nombre, sección, colonia, estrato, volatilidad
- Señalar: "Sin datos sensibles en el mapa. Email, teléfono, clave electoral
  están encriptados y solo el admin los puede ver con auditoría."

---

## Escena 4 — Wizard Onboarding (14:00 - 18:00)

**Como Admin:**

### 4a. Crear político nuevo (14:00 - 16:00)
- Ir a `/dashboard/sistema/onboarding`
- Step 1: Datos básicos (nombre ficticio "Demo Político", cargo, email)
- Step 2: Handles redes (pueden ser ficticios para demo)
- Step 3: Confirmar

> "Un admin puede dar de alta un político nuevo en menos de 5 minutos.
> El sistema automáticamente scrapea sus redes, analiza sentimiento,
> y calcula su Índice de Penetración Digital."

### 4b. Progress (16:00 - 18:00)
- Mostrar la barra de progreso del onboarding
- Si hay chain en curso: señalar las etapas (scraping → NLP → IPD)
- Si no: mostrar que el dirigente ya aparece en la lista

---

## Escena 5 — Plan IA + Kanban (18:00 - 22:00)

**Login como Piña** (o seguir como admin).

### 5a. Generar plan (18:00 - 20:00)
- Ir a `/dashboard/planes`
- Click "Generar Plan" (si el botón existe)
- Mostrar que usa Gemma 3 local (no cloud, $0 de costo)
- Esperar generación (~3-4 min con gemma3:12b)

> "El plan se genera con IA local. Cero costo. Basado en los datos reales
> de las redes del político: sentimiento, plataformas débiles, temas urgentes."

### 5b. Kanban (20:00 - 22:00)
- Ir al kanban del plan generado
- Mostrar las 3 columnas: Por Hacer / En Progreso / Completado
- Mover una tarea entre columnas
- Completar una tarea con métrica real

---

## Escena 6 — Datos Legacy + PII (22:00 - 26:00)

**Como Admin:**

### 6a. Listado safe (22:00 - 24:00)
- Ir a `/dashboard/ciudadanos` o usar API directa
- Mostrar listado de ciudadanos_legacy filtrado por alcaldía
- Señalar: nombres, sección, colonia, nivel educativo — todo visible
- Señalar: NO hay email, teléfono ni clave electoral en la lista

### 6b. Acceso PII auditado (24:00 - 26:00)
- Acceder a PII de un ciudadano específico
- Mostrar que el acceso queda loggeado en `data_access_log`
- Mencionar: "Cada acceso a datos personales deja huella. Cumplimiento LFPDPPP."

> "Los datos sensibles están encriptados con pgcrypto. Solo el admin puede
> descifrarlos, y cada acceso queda registrado con usuario, IP y timestamp."

---

## Escena 7 — Q&A + Cierre (26:00 - 30:00)

### Puntos a cubrir si preguntan:

| Tema | Respuesta |
|---|---|
| ¿Cuánto cuesta? | IA local (Gemma3, $0). Infraestructura ~$20/mes VPS. |
| ¿Cuándo se puede usar? | Backend listo. Falta deploy a Coolify (1-2 días). |
| ¿Se puede añadir más alcaldías? | Sí, el import es idempotente. Solo falta el CSV. |
| ¿Es seguro? | PII encriptado, RLS multi-tenant, audit trail, LFPDPPP. |
| ¿Qué falta? | WhatsApp campaigns, content factory, voter scoring real. |

### Roadmap visual:
> "Fase 1 (hoy): Dashboard + Social + Canvassing + Planes IA
> Fase 2 (próxima): WhatsApp campaigns, content factory, voter scoring ML,
> participación ciudadana, blindaje legal."

---

## Checklist pre-demo

- [ ] `docker ps | grep crece` — 8 containers UP
- [ ] `curl http://localhost:8002/api/v1/health/` — 200
- [ ] `curl http://localhost:11434/api/tags` — gemma3:12b
- [ ] Login admin funciona
- [ ] Login Piña funciona
- [ ] `/dashboard/canvassing` muestra mapa con puntos
- [ ] Filtros de alcaldía funcionan
- [ ] Plan IA se puede generar (o tener uno pre-generado)
- [ ] Screenshot de respaldo del mapa por si algo falla

## Respaldo: si algo falla en vivo

1. **Mapa no carga:** Mostrar el screenshot guardado en `.context/screenshots/`
2. **Ollama no responde:** "La IA corre local, a veces tarda ~4 min. Tenemos un plan pre-generado aquí."
3. **Login falla:** Mostrar las credenciales, reiniciar backend (`docker restart crece-backend`)
4. **API 500:** `docker logs crece-backend --tail 20` para debug rápido
