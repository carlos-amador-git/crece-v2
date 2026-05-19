# Prompt · Investigación scraper propio para CRECE (electoral + negocios)

Copia-pega esto a una sesión nueva de claude.ai (o ChatGPT/Gemini para
contrastar) y pídele análisis técnico + económico + arquitectónico.

---

## CONTEXTO DE NEGOCIO

Soy MD Consultoría TI. Tengo dos productos relacionados pero distintos:

### Producto 1 · CRECE Electoral (B2G/B2P)
Plataforma de inteligencia política para clientes que son dirigentes,
candidatos o partidos en México (MORENA, MC). Casos activos:
- Saymi Pineda (Secretaria Turismo Oaxaca, MORENA) — piloto en marcha
- Alejandro Piña, Rafael Solano, Yesenia Nolasco, Gabriela Jiménez,
  César Cravioto, Jorge Álvarez Máynez, Laura Ballesteros, Pepe Monroy
  — 8 dirigentes más activos o en onboarding

**Scraping necesario por dirigente** (de redes sociales):
- Posts/contenido de su perfil (FB, IG, X, TT, YT)
- Métricas agregadas (followers, engagement rate)
- **Followers** nominales (quién los sigue) — para feature de seguidores
- **Reactors/likers** de cada post — para detectar "fantasmas vs activos"
  + match con watchlist nominada por el cliente
- Comments + sentiment analysis (NLP)
- Competidores políticos (modelo ligero, mensual)

### Producto 2 · CRECE Negocios (B2B)
Plataforma de inteligencia de mercado para PyMEs en México. Cliente típico:
empresa local (restaurante, gimnasio, consultorio, hotel boutique) que
quiere monitorear su mercado.

**Scraping necesario por cliente B2B** (cosas DIFERENTES a electoral):
- **Reviews de su negocio** (Google Maps, Tripadvisor, Foursquare,
  ZonaTuristica, Facebook Pages reviews)
- **Reviews de competidores locales** (mismo sector + 5km radio)
- **Listados directorios empresariales** (Páginas Amarillas MX, DataMx,
  INEGI DENUE, Sección Amarilla)
- **Precios/menús competencia** (cuando publican públicamente)
- **Eventos locales** (Eventbrite, Facebook Events, ciudades.com.mx)
- **Calidad de servicio en redes** (menciones del negocio en Twitter/X,
  hashtags locales, queja consumidor)
- **Listados de proveedores y mayoristas** (B2B marketplace tipo
  Mercado Libre Empresas, Alibaba, MakaroSupply)
- **Permisos/sanciones gobierno** (COFEPRIS, SAT padrón, PROFECO)

## STACK ACTUAL

**In-house gratuito (validado funciona)**:
- `Scweet 5.3` para X (tweets + followers + user_info, sin auth de
  desarrollador, con `auth_token` cookie)
- `ensta` + `instaloader` para IG (posts + perfil con Guest mode)
- `yt-dlp` para TikTok + YouTube (metadata + posts + transcripción)
- `youtube_privileged.py` con OAuth (sólo subscribers visibles del
  propio canal del dirigente)
- Backend FastAPI + PostgreSQL + Celery workers + Redis

**De pago (lo que pagamos hoy)**:
- Apify · pool de 3 cuentas free tier ($5/mes c/u, rotación automática
  por budget disponible)
- Usado para: `apify/facebook-likes-scraper` ($0.005/item) y
  `scraper_one/facebook-reactions-scraper` (PAY_PER_EVENT $0.002/result)
  porque NO hay alternativa gratuita estable para FB reactors

**Bloqueado por privacy / plataforma**:
- X removió endpoint público `Favoriters` en 2023 (no se puede listar
  quién likeó un tweet) — esto es decisión de la plataforma, NO hay scraper
  que lo resuelva
- IG no expone likers de un post a Guest mode (sí con auth pero bloqueado
  para no-amigos)
- TT no expone lista de likers
- YT nunca expuso likers (privacy desde 2010)

**Hallazgos clave de hoy (2026-05-14)**:
- Apify ata trials de paid actors al humano (IP + device fingerprint +
  cookies persistentes incluso en incógnito), NO al email. Creamos 3
  cuentas con emails distintos y los trials siguen expirados
  cross-cuenta para los mismos actors. Renting Apify ($19.99/mo)
  es el único path para los actors paid.
- FB privacy oculta ~60-75% de reactors públicos. apify/facebook-likes-scraper
  captura ~25% del total con limit alto.
  `scraper_one/facebook-reactions-scraper` captura `reactorId` numérico
  estable (100% IDs extraíbles) hasta 20 results/post en free tier.
- Playwright con `storage_state` capturado vía login en vivo del CEO
  funciona para extraer reactors de FB. Limitación: el popup ordena por
  relevancia al viewer, así que reactors que el CEO no conoce aparecen al
  final del scroll. Cookies frescas duran ~30 días.

## PREGUNTAS QUE QUIERO QUE RESPONDAS

1. **Análisis técnico**: para los 2 productos (electoral + negocios B2B),
   ¿qué arquitectura de scraping es óptima a 12-24 meses considerando:
   - Stack actual + lo que ya pagamos
   - Volumen esperado (10 clientes electoral + 50 clientes negocios)
   - Mantenimiento (FB cambia HTML cada 2-3 meses; Google Maps lo mismo)
   - Riesgo de baneo de cuentas y compliance legal (TOS de cada plataforma)
   - Calidad y completitud de datos (público vs autenticado vs privado)

2. **Análisis económico**: en función de los 2 productos, calcula
   - Costo total escenarios: 10 / 50 / 200 clientes
   - Apify pool (lo que hago hoy) vs Apify Starter $49/mes vs scraper propio
     Nivel 1/2/3 vs híbrido
   - Punto de inflexión donde scraper propio se vuelve rentable
   - Costo del tiempo de mantenimiento (8h/mes Nivel 1, 16h/mes Nivel 2,
     40h/mes Nivel 3) valorado a tarifa MX de senior dev ($800-1500
     MXN/h)

3. **Arquitectura recomendada para CRECE Negocios específicamente**:
   - Google Maps Reviews scraping: ¿Apify (apify/google-maps-reviews-scraper)
     vs `googlemaps-scraper` Python lib vs scraper propio con Playwright?
   - INEGI DENUE: ¿API oficial gratuita vs scraper?
   - Tripadvisor reviews: ¿qué libs gratuitas existen?
   - B2B marketplaces (Mercado Libre Empresas, Alibaba): ¿APIs oficiales?
   - Reviews FB Pages: ¿incluido en lo que ya pagamos a Apify o requiere
     actor distinto?

4. **Riesgos legales/compliance**: ¿qué advertencias debo darle al cliente
   sobre datos scrapeados? ¿LFPDPPP México qué dice de:
   - Almacenar identidades nominales de reactors/likers (consentimiento)?
   - Hashear con SHA256 + salt ya cumple?
   - Compartir entre clientes (cross-tenant) es problemático?

5. **Recomendación final**: en orden de prioridad, dame 3-5 acciones
   concretas para los próximos 30 días que mejoren la economía del
   scraping en CRECE sin sacrificar calidad ni romper compliance.

## CONTEXTO ADICIONAL ÚTIL

- Empresa: MD Consultoría TI (consultoria-md.com), ~5 años, equipo
  pequeño (1 CEO técnico + agentes IA + colaboradores contratados)
- Stack común: FastAPI Python 3.12 · Next.js 14 · PostgreSQL 16 · Celery
- Mercado: México (principal) + LATAM hispanohablante a futuro
- Filosofía: NO inventar datos, NO usar mocks en producción, usar libs
  probadas antes que código custom, "calidad > velocidad"
- Compliance ya implementado: LFPDPPP (hash SHA256+salt LFPDPPP-compliant
  para identidades, RLS multi-tenant en PostgreSQL, audit logs)

Da respuesta estructurada, con números concretos cuando sea posible.
NO me digas "depende" sin dar 2-3 escenarios cuantificados.

---

**Notas para mí (CEO):**
- Comparar respuesta con la que dará la sesión actual de Linda/CRECE
- Si las 2 sesiones convergen → decisión sólida
- Si divergen → contexto faltante por mi lado, investigar más
- Compartir respuesta clave a Linda para que actualice plan
