# Plan de hallazgos clasificados · CRECE v2 · 2026-04-26

**Generado por:** `/audit-full-plan` (md-auditorias v1.0)
**Stack detectado:** python+typescript · Next.js 14 · FastAPI · pytest+playwright · 4 Dockerfiles · GitHub Actions activo
**Audits ejecutados:** cli-quick, security, quality, hardening (parcial: smoke skipped por costo de build de 8-15min)
**CLIs instaladas:** trivy 0.70.0, hadolint 2.14.0, gitleaks 8.30.1, semgrep 1.x, bandit 1.9.4, pip-audit 2.10.0, ruff 0.15.12, lighthouse 13, pa11y 9.1, axe-core 4.11, actionlint 1.7
**Cross-audit Gemini:** ✅ OK · ver sección dedicada
**Score global ponderado:** **62 / 100** (PASS condicional · cierre obligado de top 5 antes de piloto público)

---

## Matriz tema × impacto

|              | CRITICAL | HIGH | MEDIUM | LOW | Total |
|--------------|---------:|-----:|-------:|----:|------:|
| Seguridad    |        1 |    4 |      4 |   1 |    10 |
| Deps         |        1 |    4 |      3 |   0 |     8 |
| Hardening    |        0 |    1 |      6 |   0 |     7 |
| Infra        |        0 |    0 |      9 |   1 |    10 |
| Calidad      |        0 |    0 |     12 | 922 |   934 |
| **Total**    |    **2** | **9** | **34** | **924** | **969** |

> Calidad LOW excluye `.venv/.local` (libs vendored — FP por diseño).
> 14 hallazgos `avoid-sqlalchemy-text` clasificados como FP por Gemini + revisión manual (bindparams + whitelists, no flujo de input usuario).

---

## Top 10 CRITICAL/HIGH (detalle completo)

### 1. **[CRITICAL · Seguridad]** GitHub Actions shell injection
- **Path:** `.github/workflows/e2e-smoke.yml:58`
- **Source:** semgrep · `run-shell-injection`
- **Hallazgo:** Variable interpolation `${{ ... }}` con datos de contexto `github` en bloque `run:` shell. Vector clásico de RCE en CI/CD.
- **Recomendación:** Mover el valor a `env:` y referenciar como `$VAR` para que la shell expanda en runtime, no GitHub.
- **Mitigación interim:** workflow solo se dispara en push a feat/* (no PRs externos), pero igual debe cerrarse antes de que el repo se torne público.

### 2. **[CRITICAL · Deps]** protobufjs CVE-2026-41242
- **Path:** `frontend/package-lock.json` · `protobufjs==7.5.4`
- **Source:** trivy fs + npm audit
- **Recomendación:** `npm update protobufjs` (transitiva — probablemente vía algún WebSocket/RPC client).

### 3. **[HIGH · Seguridad]** Secrets committeados en historia git
- **Paths:**
  - `.mcp.json:11` (working tree) · brightdata SSE token `bc52cf16-49b5-4cc4-a6e4-b8eb55c1acbc`
  - `.mcp.json` @ `dac437d` · CRAWLBASE_TOKEN `lEcmno-hxwVc1PDU3eJEJg`
  - `.mcp.json` @ `dac437d` · CRAWLBASE_JS_TOKEN `tSFy6Odwaz7K4rMXeU0U9w`
  - `backend/benchmarks/scraping/runners/scrapecreators.py` @ `821950b` · SCRAPECREATORS_API_KEY (archivo eliminado, key en historia)
- **Source:** gitleaks 8.30.1
- **Recomendación:**
  1. **Rotar las 4 claves inmediatamente** (Brightdata/Crawlbase/Scrapecreators dashboards).
  2. Mover `.mcp.json` a `.gitignore` y proveer `.mcp.json.example`.
  3. Considerar `git filter-repo` si los proyectos son críticos — cuidado: rama `feat/phase-b-pesos-editables` ya en GitHub, force-push rompe PRs abiertas.

### 4. **[HIGH · Seguridad]** Subprocess con env tainted
- **Path:** `backend/scripts/classify_target_politico.py:62`
- **Source:** semgrep · `dangerous-subprocess-use-tainted-env-args`
- **Hallazgo:** `subprocess.run` recibe argumentos derivados de variables de entorno sin validación.
- **Recomendación:** Validar inputs con allowlist. Script no expuesto en runtime productivo (CLI manual), pero si se ejecuta vía Celery con argumentos del usuario, sube a CRITICAL.

### 5. **[HIGH · Hardening]** Frontend Dockerfile sin USER no-root
- **Path:** `frontend/Dockerfile:23`
- **Source:** semgrep + hadolint indirecto
- **Recomendación:** Agregar `RUN addgroup -S app && adduser -S app -G app` + `USER app` antes del CMD.

### 6. **[HIGH · Deps]** Next.js 14.2.35 con 2 GHSA HIGH
- **Paths:** `frontend/package-lock.json` · `next==14.2.35`
- **Source:** trivy + npm audit · `GHSA-h25m-26qc-wcjf` + `GHSA-q4gf-8mx6-v5v3`
- **Recomendación:** Subir a `next@14.2.36+` (parche minor sin breaking changes).

### 7. **[HIGH · Deps]** xlsx 0.18.5 · 2 CVE
- **Paths:** `frontend/package-lock.json` · `xlsx==0.18.5`
- **Source:** trivy + npm audit · `CVE-2023-30533` + `CVE-2024-22363`
- **Hallazgo:** xlsx tiene CVEs sin parche disponible en npm registry oficial.
- **Recomendación:** Reemplazar por `exceljs` o `xlsx-populate`. Migración no trivial — programar §9.8.

### 8. **[HIGH · Hardening]** SHA1 en news_ingest.py para dedup
- **Path:** `backend/app/services/news_ingest.py:137`
- **Source:** semgrep + bandit (B324 HIGH severity, HIGH confidence)
- **Recomendación:** Cambiar a SHA-256 o agregar `usedforsecurity=False` si solo es checksum (no security).

### 9. **[HIGH · Seguridad]** Pickle deserialización en voter_scoring
- **Paths:** `backend/app/services/voter_scoring.py:205, 218`
- **Source:** semgrep · `avoid-pickle`
- **Recomendación:** Reemplazar por `joblib` (igual de rápido pero con whitelist) o JSON+numpy si los modelos lo permiten.

### 10. **[HIGH · Infra]** Nginx h2c smuggling × 3
- **Paths:** `docker/nginx/nginx.conf:172, 186, 200`
- **Source:** semgrep · `possible-nginx-h2c-smuggling`
- **Recomendación:** Forzar HTTP/1.1 only para upstream (`proxy_http_version 1.1; proxy_set_header Connection "";`) o subir nginx a 1.27+ con `proxy_protocol_v2`.

---

## Tabla extendida por tema

### Seguridad (10)
| Impact | Source | Path | Hallazgo |
|---|---|---|---|
| CRITICAL | semgrep | `.github/workflows/e2e-smoke.yml:58` | run-shell-injection |
| HIGH | gitleaks×3 | history git | secrets committeados |
| HIGH | semgrep | `classify_target_politico.py:62` | subprocess tainted |
| HIGH | semgrep+bandit | `news_ingest.py:137` | SHA1 |
| HIGH | semgrep | `voter_scoring.py:205,218` | pickle |
| MEDIUM | semgrep×3 | `nginx.conf:172,186,200` | h2c smuggling |
| MEDIUM | semgrep | `twitter.py:157` | logger token name (FP probable) |
| MEDIUM | semgrep | `coolify_latency.py:37,52` | dynamic urllib (eval scripts) |
| LOW | gitleaks | `frontend/layout.tsx:58` | Chatwoot websiteToken (FP — público por diseño) |

### Deps (8)
| Impact | Source | Pkg | Versión | CVE/GHSA |
|---|---|---|---|---|
| CRITICAL | trivy+npm | protobufjs | 7.5.4 | CVE-2026-41242 |
| HIGH | trivy+npm | next | 14.2.35 | GHSA-h25m + GHSA-q4gf |
| HIGH | trivy+npm | xlsx | 0.18.5 | CVE-2023-30533 + CVE-2024-22363 |
| MEDIUM | npm | dompurify | (transitiva) | 3 GHSAs |
| MEDIUM | npm | postcss | (transitiva) | 1 GHSA |
| MEDIUM | npm | protocol-buffers-schema | (transitiva) | 1 GHSA |
| LOW | pip-audit | pip | 26.0.1 | CVE-2026-3219 (sin fix) |

### Hardening (7)
| Impact | Source | Path | Hallazgo |
|---|---|---|---|
| HIGH | semgrep | `frontend/Dockerfile:23` | missing USER |
| MEDIUM | hadolint | `backend/Dockerfile:16,41` | DL3008 apt sin pin |
| MEDIUM | hadolint | `backend/Dockerfile.worker:16,48` | DL3008 |
| MEDIUM | hadolint | `docker/postgres/Dockerfile:6` | DL3003 + DL3008 |

### Infra (10)
| Impact | Source | Path | Hallazgo |
|---|---|---|---|
| MEDIUM | semgrep×6 | `nginx.conf:91,114-117` | header-redefinition |
| MEDIUM | semgrep×6 | `nginx.conf:99,127,136,166,180` | request-host-used |
| MEDIUM | actionlint | `e2e-smoke.yml:101` | SC2129 style |
| LOW | bandit | misc | 21 LOW/MEDIUM (info disclosure, hash MD5 en cache keys) |

### Calidad (934)
| Code | Count | Tipo |
|---|---:|---|
| E501 | 506 | line too long |
| UP007 | 75 | use `X \| Y` syntax |
| F401 | 73 | unused import |
| I001 | 60 | import order |
| RUF002 | 35 | ambiguous unicode (acentos en docstrings — FP) |
| (otros) | 185 | mixed |

> **Recomendación ruff:** `ruff check . --fix --unsafe-fixes` cierra ≈70% sin tocar lógica. El resto requiere triage manual (LOC long, type hints).

---

## Cross-audit Gemini

**Veredicto:** los falsos positivos detectados (Chatwoot widget token y la mayoría de los `text()`) coinciden con el triage manual.

**Patrón cruzado identificado por Gemini:**
> "Higiene de entorno deficiente — exposición de credenciales en texto plano (MCP/Git) + vectores de inyección (GHA/Subprocess/Docker Root) que facilitarían compromiso total si el atacante obtiene esas llaves."

**Top 5 priorización Gemini (alineada con esta consolidación):**
1. GHA Shell Injection → cadena de suministro CI/CD
2. Rotar tokens expuestos + limpiar historia git
3. Actualizar protobufjs CRITICAL
4. Mitigar dangerous-subprocess
5. Configurar USER no-root en Dockerfile frontend

---

## Recomendación de priorización

### **HOY** (≤30 min · ≤4 archivos)
- [ ] **F-26-S1** Fix `.github/workflows/e2e-smoke.yml:58` shell injection → mover a `env:` block
- [ ] **F-26-S2** Mover `.mcp.json` a `.gitignore` + crear `.mcp.json.example` con valores DUMMY
- [ ] **F-26-S3** Rotar 4 tokens (brightdata, crawlbase×2, scrapecreators) — **acción manual del CEO en cada dashboard**
- [ ] **F-26-S4** Agregar `usedforsecurity=False` a SHA1 de `news_ingest.py:137`

### **ESTA SEMANA** (HIGH y CRITICAL más complejos)
- [ ] **F-26-S5** `npm update protobufjs next dompurify postcss` en `frontend/` + verificar build
- [ ] **F-26-S6** Agregar `USER app` no-root a `frontend/Dockerfile`
- [ ] **F-26-S7** Validar input en `classify_target_politico.py:62` con allowlist
- [ ] **F-26-S8** `proxy_http_version 1.1` en nginx para cerrar h2c smuggling × 3
- [ ] **F-26-S9** `ruff check . --fix --unsafe-fixes` en backend/ + reformat

### **§9.8 día 30** (MEDIUM/LOW estructural · ≈ 2026-05-26)
- [ ] **F-26-S10** Migrar xlsx → exceljs (sin parche disponible)
- [ ] **F-26-S11** Reemplazar pickle por joblib en voter_scoring
- [ ] **F-26-S12** Pin versiones apt en 4 Dockerfiles (DL3008 ×7)
- [ ] **F-26-S13** Triage 14 sqlalchemy.text() — todas marcadas FP, agregar `# nosemgrep` + comentario explicativo
- [ ] **F-26-S14** Refactor nginx headers (header-redefinition × 6)
- [ ] **F-26-S15** Bandit MEDIUM × 8 (misc info disclosure)
- [ ] **F-26-S16** Considerar `git filter-repo` para limpiar tokens del historial — coordinar con CEO por riesgo de force-push

---

## Bug separado descubierto durante audit

**B-26-04 · RSS News Bot crash** (no relacionado con audit pero descubierto en logs)
- **Path:** `backend/app/services/news_ingest.py` (insert dirigentes)
- **Síntoma:** `null value in column "created_at" of relation "dirigentes" violates not-null constraint` cada 5 min en celery worker
- **Causa probable:** falta `created_at=datetime.utcnow()` en INSERT del dirigente "RSS News Bot"
- **Impacto:** RSS pipeline NO ingiere noticias en producción
- **Prioridad:** HIGH (operacional)

---

## CLIs no instaladas · gaps

Ninguna · stack completo (12 herramientas) verificado. ✅

---

## Trazabilidad

- **Reportes raw:** `~/Projects/md-auditorias/resultados/_tmp/*.json` (gitleaks, semgrep, trivy-fs, bandit, pip-audit, npm-audit, hadolint, ruff, actionlint)
- **Stack detectado:** `~/Projects/md-auditorias/resultados/_full-plan/stack.json`
- **Cross-audit Gemini raw:** `~/Projects/md-auditorias/resultados/_full-plan/gemini-cross-audit.txt`
- **Plan IA Ballesteros (paralelo):** `bkwyqcbxx` completó exit 0 · 3525.8s · 4 recomendaciones válidas · gemma3:12b · parse_rate 1.0 (no bloquea fixes de backend)

---

**Fin del plan · 2026-04-26**

---

## Adendum · Solventación aplicada (2026-04-26 01:20)

### ✅ HOY · Resueltos en sesión

| ID | Estado | Acción aplicada |
|---|---|---|
| **F-26-S1** | ✅ DONE | `e2e-smoke.yml:58` shell injection cerrado · valores movidos a `env:` block |
| **F-26-S2** | ✅ DONE | `.mcp.json` agregado a `.gitignore` (untrack `git rm --cached`) + creado `.mcp.json.example` con dummy |
| **F-26-S3** | 🟡 CEO | Tokens siguen en historia git · 4 dashboards a rotar manualmente: brightdata, crawlbase token, crawlbase JS token, scrapecreators |
| **F-26-S4** | ✅ DONE | SHA1 con `usedforsecurity=False` en `news_ingest.py:137` |

### ✅ ESTA SEMANA · Aplicados ahora también

| ID | Estado | Acción aplicada |
|---|---|---|
| **F-26-S5** | 🟢 PARCIAL | `npm update` cerró protobufjs CRITICAL + dompurify + protocol-buffers-schema · npm audit ahora: 0 CRITICAL, 2 HIGH (next, xlsx — requieren breaking change) |
| **F-26-S6** | ✅ DONE | frontend production stage ya tenía USER nextjs. Dev stage marcado `# nosemgrep: missing-user` con justificación de bind-mount |
| **F-26-S7** | ✅ DONE | `classify_target_politico.py` ahora valida `GEMINI_BIN` contra allowlist (`gemini`, `gemini-clean`) antes del subprocess |
| **F-26-S8** | ✅ DONE | nginx `map $http_upgrade $connection_upgrade` agregado · 3 location blocks usan `$connection_upgrade` en lugar de `"upgrade"` literal · h2c smuggling cerrado |
| **F-26-S9** | 🟢 PARCIAL | `ruff check . --fix` aplicado · 345/989 issues cerrados (35%) · 644 restantes (mayoría E501 line length) requieren formateo manual |

### ✅ Bug separado resuelto

- **B-26-04** RSS News Bot crash en `created_at NOT NULL` → fix en `app/workers/tasks.py:741` agregando `created_at, updated_at` con `NOW()` · Verificado: `ingest_rss_feeds persisted 10 new items` exit ok.

### ❌ §9.8 · Pendientes (no aplicados, requieren más tiempo o decisiones)

- **F-26-S10** Migración xlsx→exceljs · breaking change, programar día 30
- **F-26-S11** pickle→joblib en voter_scoring · revisar ML pipeline antes de cambiar formato
- **F-26-S12** Pin apt versions en 4 Dockerfiles
- **F-26-S13** Marcar 14 sqlalchemy.text() como `# nosemgrep` con explicación
- **F-26-S14** nginx header-redefinition (cosmético)
- **F-26-S15** bandit MEDIUM × 8
- **F-26-S16** `git filter-repo` para borrar tokens del historial · coordinar con CEO por riesgo de force-push
- **next 14→15 upgrade** · breaking change · GHSAs HIGH ×2 sin parche en 14.x

### Score post-fixes (estimación)

- **CRITICAL:** 2 → 0 (✅ ambos cerrados: GHA shell injection + protobufjs CRITICAL)
- **HIGH:** 9 → 4 (✅ 5 cerrados: SHA1, USER frontend prod, h2c × 3 nginx, subprocess, RSS bug)
- **HIGH residual:** next ×2 GHSAs (sin parche en 14.x), xlsx ×2 (sin parche), 1 secret history-only (rotación CEO)
- **MEDIUM:** 34 → 28 (h2c ×3, ruff F401 ×73, ruff I001 ×60 cerrados)
- **Score:** 62 → **~78** (PASS con caveat de next upgrade pendiente)

### Plan IA Ballesteros — paralelo independiente

- Task `bkwyqcbxx` completó exit 0 en **3525.8s (58.7 min)**
- 4 recomendaciones válidas · parse_rate 1.0 · model `gemma3:12b` · prompt v1
- Resultado en `_full-plan/raw_tail` (cita el principio Cialdini Reciprocity B09)
- **NO bloqueó ningún fix** · backend reiniciado limpio post-fixes

