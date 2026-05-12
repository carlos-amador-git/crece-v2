# SPRINT-S5-SCOPING — Meta OAuth Activable (track paralelo)

**Fecha:** 2026-04-19
**Autor:** Joy (Claude Code · sesión CRECE v2)
**Tipo de entregable:** Documento de scoping + diseño (NO implementación)
**Estado:** 🟡 PROPUESTA pendiente validación CEO
**Supersedes:** diseño original `.context/S5-DESIGN.md` (si difiere, este doc manda)

**Referencias normativas leídas:**
- `CRECE_PRODUCT_MASTER.md` §5 Sprint S5 (líneas 716-727) · §4 dual-mode (528-570) · §3.1 inventario · §6.4 DIFERIDO-02 (839) · D-02 (744) · D-04 (746) · D-19 (X=T3 permanente)
- `docs/META-OAUTH-SETUP.md` (144 líneas, 8 pasos)
- `backend/research/2026-04-19/FIDELITY_LOGIC.md` (algoritmo T1/T2/T3 · matriz 8×5)

---

## 1 · Alcance real de S5

### 1.1 Plataformas que soportan OAuth en S5

| Plataforma | OAuth disponible | Proveedor | Scope requerido | Tier post-OAuth |
|---|---|---|---|---|
| **Instagram** | ✅ Sí | Meta Graph API (IG Business) | `instagram_basic`, `instagram_manage_insights` | T3 |
| **Facebook Page** | ✅ Sí | Meta Graph API | `pages_show_list`, `pages_read_engagement`, `business_management` | T3 |
| **TikTok** | ✅ Condicional | TikTok for Business API | `user.info.basic`, `video.list`, `research` (si aplica) | T3 solo si cuenta es Business/Creator verificada |
| **YouTube** | ✅ Sí | YouTube Data API v3 + Google OAuth 2.0 | `youtube.readonly`, `yt-analytics.readonly` | T3 si el dirigente tiene canal |
| **X / Twitter** | ❌ NO (D-19) | — | X API Basic $100/mes descartado para MVP | **T3 permanente** vía stack Apify+Scrapling |
| **Facebook Personal Profile** | ❌ NO | Meta no expone Graph para perfiles personales | — | T2/T3 scraping únicamente |

**Conclusión alcance:** S5 cubre **4 plataformas OAuth** (IG · FB Page · TikTok Business · YouTube). X queda fuera por decisión comercial D-19. Facebook perfil personal (no Page) queda fuera técnicamente.

### 1.2 Qué % de los 8 dirigentes piloto requieren OAuth pre-piloto vs post-contrato

Según la matriz §3 de `FIDELITY_LOGIC.md` (40 celdas pobladas):

| Bucket | Dirigentes | % | Necesidad OAuth pre-piloto |
|---|---|---|---|
| Cuentas con volumen T3 scrapeable ≥10 items/90d | 8/8 | 100% | **No** — piloto opera completamente T3 público |
| Cuentas privadas/bloqueadas que solo abriría OAuth | 0/8 | 0% | N/A |
| Dirigentes que ganan "reach exacto" al firmar | 8/8 | 100% | Post-contrato (upgrade comercial) |

**Conclusión pre-piloto:** **cero** dirigentes requieren OAuth para que el piloto funcione. D-02 se confirma: *OAuth Meta = upgrade comercial post-venta por-dirigente · NO bloqueador piloto*.

### 1.3 Dev Mode Meta ≤25 dirigentes (DIFERIDO-02)

- Sin App Review, Meta App "CRECE v2" permite hasta **25 Administrators** (no Testers — D-02 léxico corregido)
- Piloto es 8 dirigentes → margen de **17 clientes adicionales** antes de forzar App Review
- App Review toma **4-8 semanas post-submission** (ver §5 este doc)
- Trigger sugerido (DIFERIDO-02): **cliente firmado #15** (buffer de 10 entre submission y crisis)

---

## 2 · Arquitectura del onboarding wizard

### 2.1 Wireframe texto del flujo

```
[PANTALLA 1 — DETECCIÓN DE PERFIL] ────────────────────────────────────────
  Entrada: dirigente_id ya creado en BD por MD (seed D-14)
  Lee: dirigentes.perfil (politico_activo | funcionario | precampaña | empresario)
  Muestra:
    "Bienvenido, {nombre}. Antes de activar tu diagnóstico, vamos a conectar
     tus redes oficiales. Esto mejora la precisión de reach e impresiones de
     estimación a oficial Meta/TikTok/YouTube."

  CTA primario: [Comenzar conexión →]
  CTA secundario: [Más tarde · operar en modo estimación]

[PANTALLA 2 — INVENTARIO DE CUENTAS] ──────────────────────────────────────
  Muestra 5 filas · uno por plataforma detectada en dirigentes_social:
    ┌──────────────────────────────────────────────────────────────────┐
    │ [IG]  @alejandro.pinha  ·  2,231 seg.  ·  Tier actual: T3        │
    │       [ Conectar Meta OAuth ]  ← acción primaria                 │
    │       ⓘ Al conectar subirás a T1 con reach oficial              │
    ├──────────────────────────────────────────────────────────────────┤
    │ [FB]  Page Alejandro Piña MC · 1,800 seg. · Tier actual: T3      │
    │       [ Conectar Meta OAuth ]  (mismo flujo IG, token único)     │
    ├──────────────────────────────────────────────────────────────────┤
    │ [TT]  Sin cuenta detectada                                        │
    │       [ Agregar handle ] — opcional                              │
    ├──────────────────────────────────────────────────────────────────┤
    │ [YT]  Sin canal detectado                                         │
    │       [ Agregar canal ] — opcional                               │
    ├──────────────────────────────────────────────────────────────────┤
    │ [X]   @Alejandro_Pinha · 3,100 seg. · Tier actual: T3            │
    │       ⚠ OAuth no disponible (API de pago)                        │
    │       Operamos siempre en estimación pública — D-19              │
    └──────────────────────────────────────────────────────────────────┘

[PANTALLA 3 — PRE-FLIGHT IG BUSINESS/CREATOR] ─────────────────────────────
  Solo si usuario presiona [Conectar IG]:
  Valida vía Graph API que la cuenta IG está en modo Professional y vinculada
  a FB Page. Si falla:
    "Tu cuenta de Instagram está configurada como Personal. Para conectar
     necesitas activar Cuenta Profesional:
       1. Abre Instagram → Configuración → Cuenta → Cambiar a Profesional
       2. Vuelve aquí cuando termines."
    [Validar de nuevo]  [Saltar y dejar en T3]

[PANTALLA 4 — POPUP META OAUTH] ────────────────────────────────────────────
  window.open(https://www.facebook.com/v21.0/dialog/oauth?...)
  Usuario autoriza los 5 scopes → Meta redirige a:
    {API_BASE}/api/v1/auth/callback/meta?code=...&state=...
  Backend canjea code → short-lived token → long-lived token (60d)
  Backend encripta con pgcrypto y persiste en oauth_tokens_by_platform

[PANTALLA 5 — CONFIRMACIÓN + BACKFILL] ─────────────────────────────────────
  "✅ Instagram y Facebook Page conectados. Estamos descargando los últimos
   90 días de insights oficiales. Esto puede tardar 5-15 min."

  Celery dispara backfill_graph_insights_task(dirigente_id, platform, 90d)
  data_fidelity_tier: T3 → T1 (upgrade)
  Emite evento data_origin_checkpoint (§4.5 MASTER)
  Dashboard refresca y muestra badge 📊 Oficial

[PANTALLA 6 — ONBOARDING COMPLETO] ────────────────────────────────────────
  Muestra estado final:
    IG  → 📊 Oficial
    FB  → 📊 Oficial
    TT  → 📊 Estimación (o T1 si conectó TikTok Business)
    YT  → 📊 Estimación (o T1 si conectó Google OAuth)
    X   → 📊 Estimación (permanente D-19)
```

**Decline path:** si usuario sale del wizard, estado queda `oauth_onboarding_status='pending'` y dashboard banner muestra *"Te faltan 2 redes por conectar · [Completar ahora]"*.

### 2.2 Schema propuesto tabla `oauth_tokens_by_platform`

```sql
-- Migration Alembic S5 T5.2
CREATE TABLE oauth_tokens_by_platform (
  id SERIAL PRIMARY KEY,
  dirigente_id INTEGER NOT NULL REFERENCES dirigentes(id) ON DELETE CASCADE,
  org_id INTEGER NOT NULL REFERENCES organizaciones(id),
  platform VARCHAR(20) NOT NULL CHECK (platform IN (
    'instagram', 'facebook_page', 'tiktok', 'youtube'
  )),
  -- Token encriptado con pgcrypto (KEY rotable vía PII_ENCRYPTION_KEY §7.2)
  access_token_encrypted BYTEA NOT NULL,
  refresh_token_encrypted BYTEA NULL,  -- Google OAuth YT usa refresh
  token_type VARCHAR(20) DEFAULT 'bearer',
  scope TEXT NOT NULL,  -- scopes concedidos concatenados
  -- Metadatos plataforma
  platform_user_id VARCHAR(100) NOT NULL,    -- IG user_id, FB page_id, etc
  platform_username VARCHAR(100),            -- handle visible
  -- Lifecycle
  issued_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,             -- Meta LLT ~60d, Google sin expiry si hay refresh
  last_refreshed_at TIMESTAMP,
  refresh_attempts INTEGER DEFAULT 0,
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN (
    'active', 'expired', 'revoked_by_user', 'refresh_failed', 'pending_relink'
  )),
  -- Auditoría
  granted_by_user_agent TEXT,
  granted_from_ip INET,
  revoked_at TIMESTAMP NULL,
  revoked_reason TEXT NULL,
  -- Constraint: un dirigente solo puede tener 1 token activo por plataforma
  CONSTRAINT uq_dirigente_platform_active UNIQUE (dirigente_id, platform, status)
    DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_oauth_refresh_due ON oauth_tokens_by_platform(expires_at)
  WHERE status = 'active';
CREATE INDEX idx_oauth_dirigente ON oauth_tokens_by_platform(dirigente_id, platform);
CREATE INDEX idx_oauth_org ON oauth_tokens_by_platform(org_id) WHERE status = 'active';

-- Audit log de cada acción sobre tokens (compliance LFPDPPP §7.1)
CREATE TABLE oauth_token_audit_log (
  id SERIAL PRIMARY KEY,
  token_id INTEGER REFERENCES oauth_tokens_by_platform(id),
  dirigente_id INTEGER NOT NULL,
  action VARCHAR(30) NOT NULL CHECK (action IN (
    'granted', 'refreshed', 'revoked', 'used_for_backfill',
    'used_for_insights_call', 'refresh_failed', 'expired'
  )),
  detail JSONB,
  occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
  actor VARCHAR(50)  -- 'user', 'celery_refresh_job', 'admin_md', etc
);
CREATE INDEX idx_oauth_audit_token ON oauth_token_audit_log(token_id, occurred_at DESC);
```

### 2.3 Job Celery `refresh_oauth_tokens_daily`

```python
# backend/app/workers/oauth_refresh.py (propuesto S5 T5.4)
@celery_app.task(bind=True, max_retries=3, default_retry_delay=3600)
def refresh_oauth_tokens_daily(self):
    """
    Cron: daily 04:00 UTC-6.
    Refresca tokens que expiran en <14 días para evitar cortes.
    """
    now = datetime.utcnow()
    threshold = now + timedelta(days=14)

    due = db.query(OAuthToken).filter(
        OAuthToken.status == 'active',
        OAuthToken.expires_at < threshold,
    ).all()

    for tok in due:
        try:
            if tok.platform in ('instagram', 'facebook_page'):
                new_token = meta_refresh_long_lived(tok)
            elif tok.platform == 'tiktok':
                new_token = tiktok_refresh(tok)
            elif tok.platform == 'youtube':
                new_token = google_refresh(tok)  # usa refresh_token
            tok.access_token_encrypted = encrypt(new_token.access_token)
            tok.expires_at = new_token.expires_at
            tok.last_refreshed_at = now
            tok.refresh_attempts = 0
            audit_log(tok, 'refreshed')
        except TokenRevokedByUser:
            tok.status = 'revoked_by_user'
            notify_md_team(f'{tok.dirigente_id} revocó token {tok.platform}')
            # Downgrade T1 → T3 en dirigentes.data_fidelity_tier para esa plataforma
            downgrade_tier(tok.dirigente_id, tok.platform, to='T3')
            audit_log(tok, 'revoked')
        except Exception as e:
            tok.refresh_attempts += 1
            if tok.refresh_attempts >= 3:
                tok.status = 'refresh_failed'
                notify_md_team(f'Refresh falló 3× para {tok.dirigente_id}')
            audit_log(tok, 'refresh_failed', detail={'error': str(e)})
    db.commit()
```

---

## 3 · Implicación en bloques #01-#32

Matriz rápida: cómo cambia cada bloque al pasar T3 → T1 vía OAuth.

| # | Bloque | Con T3 (pre-OAuth) | Con T1 (post-OAuth) | Gana con S5? |
|---|---|---|---|---|
| 01 | ER normalizado | ER estimado `likes+comments+views/followers` | ER exacto + reach oficial (denominador real Graph) | 🟢 Alto |
| 02 | Breakout Scale Brookings | Proxy `views/followers` | `unconnected_reach` exacto | 🟢 Muy alto |
| 03 | Matriz 2x2 contenido | Funciona pleno con públicos | Sin cambio material | ⚪ Neutro |
| 04 | Benchmark vs competidores | T3 ambos lados (simétrico) | Asimétrico · competidor queda T3 | ⚪ Neutro (ambos deben ser T1 para comparación pareja) |
| 05 | Sentiment Plutchik | NLP sobre comments públicos | Sin cambio (comments son públicos) | ⚪ Neutro |
| 06 | Crisis Spike | Mentions + sentiment | Sin cambio | ⚪ Neutro |
| 07 | Growth Attribution | Snapshot followers diario público | + Unique profile views, reach por post | 🟢 Alto |
| 08 | Share of Voice | Funciona pleno | Sin cambio | ⚪ Neutro |
| 09 | Share-to-Like Ratio | IG sin saves (parcial) | + IG saves + swipe-to-next | 🟢 Medio |
| 10 | Plan IA Start/Stop/Continue | Inputs T3 | Inputs más precisos → recs mejor calibradas | 🟡 Indirecto |
| 10.5 | Seguimiento recomendaciones | Métricas públicas | + Reach exacto · watch time · demográficos cohorte | 🟢 Alto (argumento venta) |
| 10.7 | Memoria Plan IA | — | + Calibración histórica de rec con métricas oficiales | 🟡 Indirecto |
| 11 | Cross-Partisan Validation | Clasificación autor comment | Sin cambio | ⚪ Neutro |
| 12 | CIB Detector | Signals públicos | Sin cambio | ⚪ Neutro |
| 13 | Filtro de Realidad | Funciona pleno | Sin cambio | ⚪ Neutro |
| 14 | Topic Drift | TF-IDF caption vs comments | Sin cambio | ⚪ Neutro |
| 15 | Rage Click Flag | Sentiment + velocity | Sin cambio | ⚪ Neutro |
| 16 | Promesas Campaña | Co-ocurrencia NLP | Sin cambio | ⚪ Neutro |
| 17 | Veda INE | Texto post | Sin cambio | ⚪ Neutro |
| 18 | Violencia Política | Diccionario hate speech | Sin cambio | ⚪ Neutro |
| 19 | Termómetro Territorial | Geo inferida | + Demographics Meta (ciudad, edad, género cohorte) | 🟢 Muy alto |
| 20 | Humanización Score (IA Vision) | Media pública | Sin cambio | ⚪ Neutro |
| 21 | Alerta Oportunidad trending | Funciona pleno | Sin cambio | ⚪ Neutro |
| 22 | Gap Respuesta | reply rate público | + DMs (si permiso solicitado) | 🟡 Opcional |
| 23 | Eficiencia Táctica Formato | Views públicos | + Reach exacto por formato | 🟢 Alto |
| 24 | Horarios Fricción Óptima | Engagement público | + Hora pico real de audiencia cohorte | 🟢 Medio |
| 25 | Fatiga/Saturación | Frecuencia pública | Sin cambio | ⚪ Neutro |
| 26 | Churn Rate Político | Snapshot diario | Sin cambio (IG/FB no exponen unfollower list) | ⚪ Neutro |
| 27 | Influencers Proxy | Mentions públicos | Sin cambio | ⚪ Neutro |
| 28 | Pre-Mortem Simulator | Backtesting histórico | Con reach exacto histórico → más calibrado | 🟡 Indirecto |
| 29 | Message Stickiness | Citas terceros | Sin cambio | ⚪ Neutro |
| 30 | ROI/CPA Político | **Bloqueado sin FB Ads API** | **Desbloqueado** con FB Ads scope (requiere App Review) | 🔴 T3-only permanente sin Review · requiere DIFERIDO-02 |

**Resumen matriz:** S5 mejora **8 bloques de alta fidelidad** (#01, #02, #07, #09, #10.5, #19, #23, #30 condicional). Bloque #30 ROI/CPA requiere scope `ads_read` que SÍ necesita App Review (no Dev Mode). Los 22 bloques restantes son neutros (ya funcionan pleno con T3).

**Columna BD `data_fidelity_tier` por plataforma:** ya existe como migración pendiente S1 T1 (ver `FIDELITY_LOGIC.md` §7). S5 la consume sin crear nada nuevo en ese aspecto.

---

## 4 · Estimación de esfuerzo

### 4.1 Desglose de tareas

| Tarea | Descripción | Horas | Paralelizable con |
|---|---|---:|---|
| **T5.1** Onboarding wizard frontend | 6 pantallas Next.js App Router `/dashboard/configuracion/redes` · Framer Motion transiciones · shadcn/ui · responsive · estados loading/error/success. Usa `BentoCard`, `KpiCard`, nuevo `PlatformConnectCard` | **6-8h** | S3/S4 backend |
| **T5.2** OAuth Meta backend (IG + FB Page) | Endpoints `/api/v1/auth/connect/meta/start` + `/api/v1/auth/callback/meta` · canje code → LLT · encriptación pgcrypto · schema `oauth_tokens_by_platform` + Alembic migration · validación IG Business pre-flight · backfill service `backfill_graph_insights_task` 90d | **8-10h** | S3/S4 |
| **T5.3** OAuth TikTok + YouTube | TikTok for Business OAuth flow + YouTube Data API v3 + Google OAuth 2.0 con refresh_token. Dos providers porque TikTok y Google son protocolos distintos aunque reusan estructura endpoint | **6-8h** | S3/S4 y T5.2 |
| **T5.4** Cron refresh daily | Tarea Celery `refresh_oauth_tokens_daily` · lógica revoke/expiry/refresh · integrar con Redis celery-beat · audit log · tests unitarios mock de proveedores | **3-4h** | Tras T5.2/T5.3 |
| **T5.5** Upgrade T3 → T1 automático | Al completar OAuth exitoso: (a) `data_fidelity_tier` de la plataforma específica sube a T1; (b) emite `data_origin_checkpoint` (§4.5 MASTER); (c) dispara backfill 90d; (d) frontend refresca badges. Test E2E que valida series temporales muestran línea discontinua checkpoint | **4-5h** | Tras T5.1/T5.2 |
| **T5.6** Dashboard onboarding status admin | Admin panel MD `/dashboard/admin/oauth-status` con tabla: dirigente × plataforma × tier × token_expiry × last_refreshed. CTA "enviar recordatorio re-link" si status=expired. Solo visible para org_id MD interno (rol admin §D-14) | **3-4h** | Tras T5.5 |
| **T5.7** URLs legales faltantes | Crear `/legal/terminos` + `/legal/eliminacion-datos` (Meta exige). `/legal/privacidad` ya existe Sprint C. Copy legal Meta-compliant (LFPDPPP art 10-IV) | **2-3h** | Paralelizable con cualquiera |
| **T5.8** Meta App Business setup (manual CEO) | Paso 1-3 de `META-OAUTH-SETUP.md`: verificar Business Manager MD · crear App "CRECE v2" · obtener App ID/Secret · configurar redirect URIs · solicitar 5 scopes. **Requiere CEO + docs legales MD** | **2h CEO** | Independiente (bloqueador de T5.2 prod) |
| **T5.9** Documentación cliente | Doc onboarding lista para enviar a cliente firmado: script email + tutorial con screenshots + FAQ common errors + diagrama flujo | **2-3h** | Al final |

**Total ingeniería:** **34-45h** (~1 semana developer dedicado · 1.5-2 semanas con interrupciones)
**Total manual CEO:** **2h** (App Meta setup — bloquea T5.2 producción pero no desarrollo local)

### 4.2 Dependencias con S1/S2/S3/S4

| Dependencia | Tipo | Impacto |
|---|---|---|
| **S1 T1** · columna `data_fidelity_tier` + `oauth_meta_token` | **Dura** | Bloquea T5.5 (upgrade auto requiere la columna) |
| **S1 T1** · columna `data_origin` en snapshots | **Dura** | Bloquea T5.5 (checkpoint series tiempo) |
| **S1 T7** · endpoint ARCO purge-hash | **Blanda** | No bloquea. S5 ejecuta sin él pero refuerza compliance |
| **S2** · componentes `KpiCard`, `DataFidelityBadge` | **Dura** | Wizard los consume. Si S2 aún no los produjo, S5 los adelanta (costo adicional 2h) |
| **S3** | **Ninguna** | Paralelizable 100% |
| **S4** · Plan IA con §10.5 seguimiento | **Blanda mutual** | S5 mejora inputs de S4 post-OAuth. S4 funciona sin S5 con T3. Mejora narrativa venta |
| **Extterno** · Business Manager MD verificado | **Dura externa** | T5.8 requiere acta constitutiva + RFC · 1-2 días wall-clock |
| **Externo** · cuentas IG dirigente en Business/Creator | **Dura externa** | Pre-flight wizard lo valida. Si dirigente no tiene, queda bloqueado hasta que migre (gratis 1-click pero depende del dirigente) |

### 4.3 Paralelización con S3/S4

**Confirmación:** S5 es **100% paralelizable con S3 y S4** porque:
- S3 (CIB, Filtro Realidad, Topic Drift, etc.) opera sobre data ya ingerida — no toca flujo OAuth
- S4 (Plan IA con Gemma 3:12b) opera sobre inputs agregados — el tier no cambia su pipeline, solo la calidad del número
- Los 4 bloques que S5 "mejora a T1" (#01, #02, #07, #19) siguen funcionando en T3 mientras S5 se construye

**No paralelizable con S1** — requiere las migraciones de schema como precondición dura.

**Recomendación timing:** arrancar S5 después de S1 cerrado, en paralelo con S3 (el desarrollador de S5 no pisa los servicios NLP/CIB de S3). S4 puede seguir ruta propia. Ventana realista: **semanas 3-4 del roadmap** (asumiendo S0 2026-04-19 cerrado, S1 semana 1, S2 semana 1-2, S3+S4+S5 paralelos semanas 2-4).

---

## 5 · App Review Meta (DIFERIDO-02 — disparo y entregables)

### 5.1 Cuándo disparar

**Trigger propuesto:** primer cliente firmado **#15**.
- Dev Mode soporta 25 Administrators → umbral 15 da buffer 10 para cubrir 4-8 semanas de submission
- Confirmado por CEO en §6.4 DIFERIDO-02: *"arrancar cuando lleguemos a 15-20 dirigentes contratados"*

**Sub-trigger adicional:** si se quiere habilitar bloque **#30 ROI/CPA** (scope `ads_read`) para CUALQUIER cliente, requiere App Review aunque sean <25. Decisión comercial CEO.

### 5.2 Entregables que Meta pide para App Review

| Entregable | Responsable | Tiempo preparación |
|---|---|---|
| **App Description** ≥100 palabras con casos de uso por permiso | MD + Joy redacción | 2h |
| **Privacy Policy URL** pública accesible sin login · LFPDPPP + GDPR cláusulas | Ya existe `/legal/privacidad` · revisar conformidad Meta | 1h revisión |
| **Terms of Service URL** pública | T5.7 de este sprint | Incluido |
| **Data Deletion Instructions URL** pública con flujo ARCO | T5.7 + D-18 endpoint purge-hash | Incluido |
| **App Icon** 1024×1024 PNG | Diseño MD | 1h |
| **Demo Video** 3-5 min mostrando: (a) login OAuth · (b) uso real de cada scope · (c) cómo el usuario controla/revoca | MD + Joy guion + captura | 4-6h |
| **Test Users** 2 cuentas Meta con IG Business + FB Page que reviewer pueda usar | MD provee 2 burner + 1 Page demo | 2h setup |
| **Screencast de uso de cada permiso solicitado** | Joy con Chrome DevTools MCP | 2h |
| **Business Verification completa** de MD Consultoría (ya iniciada Paso 1 `META-OAUTH-SETUP.md`) | CEO · docs legales | Wall-clock 3-7 días Meta |

**Total preparación interna:** ~15h ingeniería+diseño.
**Tiempo wall-clock post-submission:** Meta responde típicamente **4-8 semanas** (puede ser menos con uso real documentado).

### 5.3 Scopes a solicitar en App Review

**Ya cubiertos en Dev Mode:**
- `pages_show_list`, `pages_read_engagement`, `instagram_basic`, `instagram_manage_insights`, `business_management`

**Adicionales para sacar partido pleno (opcionales · decisión comercial):**
- `ads_read` → desbloquea bloque #30 ROI/CPA
- `pages_read_user_content` → comments más profundos en FB Pages
- `instagram_manage_comments` → responder desde CRECE (si producto lo ofrece)

---

## 6 · Riesgos operativos

### 6.1 Rate limits Meta Graph API

| Limit | Valor oficial | Mitigación |
|---|---|---|
| **IG Graph** per-user-token | 200 calls/hora | Backfill 90d no excede (promedio 60-90 llamadas). Celery throttling `rate_limit='180/h'` por token |
| **FB Graph Page** per-page-token | 200 calls/hora/Page | Idéntico |
| **BUC (Business Use Case)** global app | 200 × usuarios activos en ventana 1h | Dev Mode seguro. Live Mode requiere calibración post App Review |
| **Insights queries** históricas | 93 días máx ventana | Backfill queda en 90d por diseño (buffer 3d) |

### 6.2 Revocación de token por usuario

**Flujo detección:**
1. Celery refresh_oauth_tokens_daily falla con error 190 (Meta) o 401 (Google)
2. Marca token `status='revoked_by_user'`
3. Downgrade automático `data_fidelity_tier` de esa plataforma: T1 → T3
4. Emite evento `data_origin_checkpoint` inverso
5. Notifica al equipo MD (email + Slack webhook opcional)
6. Dashboard muestra banner al dirigente: *"Tu conexión de Instagram se desconectó. [Reconectar]"*

**Timing:** detección en ≤24h (siguiente corrida del cron). Aceptable para un flujo admin, no para crisis monitoring. Si se requiere <1h detección, añadir `oauth_health_check_hourly` (scope reducido).

### 6.3 Token expiry

| Provider | Tipo token | Duración | Estrategia |
|---|---|---|---|
| **Meta (IG + FB)** | Long-Lived User Token | 60 días | Refresh a los 45d vía endpoint `/oauth/access_token?grant_type=fb_exchange_token` |
| **Meta Page Token** | Long-Lived Page | **Sin expiry** si derivado de User LLT | Refresh solo User, Page regenera |
| **TikTok for Business** | access_token + refresh_token | 24h access · 365d refresh | Refresh daily obligatorio |
| **Google (YouTube)** | access_token + refresh_token | 1h access · indefinido refresh | Refresh on-demand ante 401 |

**Monitoreo:** vista SQL `oauth_tokens_expiring_7d` alimenta dashboard admin T5.6.

### 6.4 Riesgos adicionales

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Dirigente tiene IG Personal (no Business) · OAuth falla silenciosamente | ALTA | MEDIO | Pre-flight pantalla 3 wizard valida antes de abrir popup |
| Cuenta FB del dirigente no tiene Page política (solo perfil personal) | MEDIA | MEDIO | Wizard solo ofrece FB Page si detecta `pages_show_list` devuelve ≥1. Si 0, skip FB |
| Meta cambia política App Review post-submission | BAJA | ALTO | Monitorear changelog Meta trimestral. Plan B: continuar Dev Mode hasta 25 admins |
| Dirigente revoca token 2 veces seguidas | MEDIA | BAJO | Escalación MD: llamada soporte. NO re-invitar automáticamente (espera acción manual) |
| Cliente sofisticado exige ver cómo borrar sus datos | MEDIA | ALTO | D-18 endpoint `/admin/compliance/purge-hash` + doc pública `/legal/eliminacion-datos` |

---

## 7 · Criterio acceptance binario del S5

| # | Check | Binario | Evidencia |
|---|---|---|---|
| 1 | **5+ dirigentes firmados con OAuth activo en ≥1 plataforma** | pass/fail | Query `SELECT COUNT(DISTINCT dirigente_id) FROM oauth_tokens_by_platform WHERE status='active'` ≥ 5 |
| 2 | **Upgrade T3→T1 automático funcional en prueba E2E** | pass/fail | Test Playwright: conecta OAuth mock → verifica `data_fidelity_tier` pasa de T3 a T1 + evento checkpoint + badge UI cambia a 📊 Oficial |
| 3 | **Endpoint `GET /api/v1/dirigentes/{id}/oauth/status` operativo** | pass/fail | Test API: devuelve JSON `{"instagram": {"tier": "T1", "expires_at": "..."}, ...}` con 5 keys plataforma |
| 4 | **Documentación onboarding lista para cliente** | pass/fail | `docs/ONBOARDING-CLIENTE-OAUTH.md` revisado por CEO |
| 5 | **Cron refresh funciona por 7 días sin intervención manual** | pass/fail | Log audit: 7 corridas sin `refresh_failed > 0` en ≥1 token activo |
| 6 | **Paso manual CEO completado** | pass/fail | App "CRECE v2" en Meta Business Manager con App ID productivo + 5 scopes + Business verification ✓ |

**Umbral pass del sprint:** 6/6 en check binario. Check 1 admite degradación a 2+ si no hay 5 clientes firmados aún (en cuyo caso el sprint se cierra parcial y queda abierto el ítem "esperar adopción" como D-).

---

## 8 · Recomendación final

### 8.1 Timing sugerido: paralelo con S3

**Secuencia recomendada:**
```
Semana 1: Sprint S1 (secuencial, bloquea todo)
Semana 2: Sprint S2 inicio (core MVP)
Semana 2-3: Sprint S2 cierre + Sprint S3 arranca
Semana 3-4: Sprint S3 + Sprint S4 + Sprint S5 EN PARALELO
Semana 4-5: cierre S3 + S4 + S5
```

**Por qué paralelo con S3 (no S4):**
- S3 no toca tokens ni OAuth → cero colisión
- S4 consume tier — si Plan IA Gemma corre sobre data T1 vs T3 NO cambia el pipeline, pero la narrativa de venta se beneficia si S5 cierra primero. Idealmente S5 cierra **antes** que S4 entre a producción comercial
- Si hay solo 1 developer disponible: S3 → S5 → S4 es orden con mejor valor comercial

### 8.2 Dependencias que podrían bloquear S5 al arranque

**Duras:**
1. Migración S1 T1 con columnas `data_fidelity_tier`, `data_origin`, `oauth_meta_token` — sin esto S5 no arranca
2. CEO completa Meta Business Manager + App "CRECE v2" verificada (~2h + 3-7d wall-clock Meta) — sin esto S5 dev local funciona pero prod no

**Blandas:**
3. Componentes `DataFidelityBadge` + `KpiCard` del S2 (si S2 se retrasa, S5 los adelanta +2h)
4. 5+ clientes firmados para validar check binario #1 (si no se alcanza, sprint cierra parcial)

### 8.3 Estimación total S5

**Ingeniería:** 34-45h (~1 semana developer dedicado)
**CEO manual:** 2h + wall-clock Business verification Meta (3-7 días)
**Total wall-clock realista:** 1.5-2 semanas si paralelizado con S3

---

## 9 · Siguientes pasos (no accionables hoy)

Cuando S1 cierre y se decida arrancar S5:

1. Validar con CEO el timing (¿paralelo S3 o post-S3?)
2. CEO ejecuta T5.8 (Meta Business + App setup) — bloquea T5.2 producción
3. Planificar sesión dedicada S5 con handoff desde este documento
4. Migrar este scoping a `.context/PLAN-current.md` cuando se arranque sprint
5. Si el ecosistema escala a 15+ clientes antes que S5 se complete, disparar DIFERIDO-02 (App Review submission) en paralelo

---

**Fin del documento de scoping. No hay código que implementar en esta tarea.**
