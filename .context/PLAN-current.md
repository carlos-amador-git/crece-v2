ACTIVE: ninguno — sesión 2026-07-16/17 cerrada (actores políticos ADR-0009). NEXT abajo.
RECENT-CLOSED 2026-07-16/17: SEC-CRECE-1 retractado · BUG-CRECE-1 fix (b303329 pusheado) · feat actores rol_politico obligatorio (0ae8829 LOCAL, espera OK push) · ADR-0009 Proposed (espera flip CEO) · DISENO-actores-politicos-2026-07-16.md consenso tríada 3/3.
CERRADO 2026-07-17: push 0ae8829+cff16c7 (doble PASS) · ADR-0009 Accepted · PROD: Hannah al aire (org "Equipo Hannah de Lamadrid" slug equipo-hannah-de-lamadrid CON "de" = canónico · display "Hannah de Lamadrid" · rol oficialismo · pass sin tocar) · migración 5a6505d74dc7 aplicada en prod, roster backfilleado, CERO rol NULL · branch paralelo de Carlos descartado, cero duplicado.
PENDIENTE INMEDIATO: (a) CEO restaurar .env raíz (perdido en re-clone post-wipe; stack completo local no levanta) · (b) DECISIÓN CEO: rotar el password de seed de la cuenta admin (admin@consultoriamd.com) ahora que hay cliente real — sigue con el valor del bootstrap; escalado, fuera de perímetro agente (rotar credenciales requiere OK CEO). NO se documenta el valor literal aquí (credencial viva en prod).
DIFERIDO DECLARADO (ADR-0009): catálogo partido×ámbito→rol como sugerencia en wizard · multi-rol por ámbito · factory canónico fixtures tests (hallazgo codex baja) · barrido paths de creación alternos (seeders/scripts) contra NOT NULL.
RECENT-CLOSED 2026-06-13: botón "Sincronizar con RADAR" (PLAN-2026-06-13-boton-sincronizar-radar.md · ADR-005) + dedup fans por author_hash (ADR-006) + 3 dirigentes al día (Saymi/Pepe/Felipe). Todo en origin/main @ 342a52f. Verificado E2E en la app (Playwright).
PARTIAL 2026-06-11: PLAN-2026-06-11-auto-radar-crece.md (pipeline auto RADAR→CRECE) — endpoint /ingest/sync + watermark + Celery chain HECHOS y probados; workflow n8n desplegado INACTIVE (W3y311tQbS4TrstQ). FALTA activar: deploy Coolify + RADAR conecta push (su ADR D-050) + env MINIO_* + nodo Config.
NEXT (orden): (1) activar pipeline auto [deploy Carlos + D-050 RADAR] · (2) causa raíz dedup fans: UPSERT por author_hash en ingesta RADAR (ADR-006, sino watched_profiles crece 23%→50%/mes) · (3) NLP fine-tune cascada híbrida (DIAGNOSTICO-2026-06-12, faltan 2 de 3 Excels evaluadores) · (4) normalización nombres fans (18k variantes) · (5) recalibrar Misael VIP >514 (regla 12, PR CEO).
PREV-CLOSED 2026-06-04: PLAN-2026-06-04-3-fixes-cards.md (3 fixes cards Saymi · cerrado por sesiones intermedias)
PREV-ACTIVE: PLAN-2026-05-27-nlp-reingest-enrich.md (re-ingest 3 MC desde radar_db :5453 + enrich RAM-safe · Sonnet+medium · attended · post crash RAM 2026-05-27)
PREV-ACTIVE: PLAN-2026-05-26-cierre-pendientes-diagnostico.md (F0+F1 CERRADOS 2026-05-26 noche vía /sprint-implement · pendiente F2-opcional/F3.2/F4/F5/F6 · ver STATUS para detalle)
RECENT-CLOSED 2026-05-25 tarde: PLAN-2026-05-25-sprint-cierre-audit.md (9/10 items audit-full) + PLAN-2026-05-25-sprint-multi.md (5 bugs UI + B07 beat + B08 rivales + TT mapper)
RECENT-CLOSED 2026-05-25: PLAN-2026-05-22-recovery.md (F3.0-F3.3 cerradas · 5/5 G-criteria verdes · batch único 670 OK 0 fails 30min)
PREVIOUS-CLOSED 2026-05-20: PLAN-2026-05-20-post-ingest-hugo.md (cerrado de facto por sesiones intermedias)
PREVIOUS-CLOSED 2026-05-20: PLAN-2026-05-19-deuda-tests-y-fixes.md (CERRADO · PR #55 mergeado cd3e408e75 · 14/14 audit-full tasks · 3 falsos positivos verificados · hotfix Gemini regex · workflow CI smoke fix · sidebar Fans y Perfiles restaurado D-FANS-PERFILES-SIDEBAR-INVARIANTE)
NEXT: TBD post-Saymi/Pepe ingest cierre (depende discrepancias NLP residuales · si <10% siguen ok producto, si >10% sprint dedicado NLP)
PREV: PLAN-2026-05-19-content-hub.md v2 (post-piloto · 4 fases F0-F3 · F4 backlog · F4 Content Hub absorbido por PR #54)
RECENT-CLOSED 2026-05-19: PLAN-2026-05-17-fans-dashboard.md · 6/6 sprints cerrados (Sprints A/B/C/E pre-apagón 2026-05-17 commits f449262/7e34fdf/923c034/2a1b13b/3a412eb + Sprints D/F post-apagón 2026-05-19 commits 0c75a85/0b0e4b1/ae20ef0/177f768 + nuevo regen_plan_dirigente.py)
PARALLEL-CLOSED: PLAN-2026-05-16-sprint-implement-sesion.md (Q-1..Q-5 · 5 blockers cerrados · 42 tests verdes · cross-audit Gemini integrado)
PREV-CLOSED: PLAN-2026-05-15-sprints-dedicados.md (6/7 sprints CERRADOS · S1 diferido honestamente · Gemini cross-audit integrado)
PREV-CLOSED: PLAN-2026-05-15-audit-multi.md (4 fases audit + hotfix RBAC 7 endpoints + bugs encuestas)
PREV-CLOSED: PLAN-2026-05-14-war-room-personal.md (W0-W8 + scraper light Apify FB · Saymi enriquecida)
PARALLEL-CLOSED: Sprint C de PLAN-2026-05-14-fix-fantasmas-observados.md (commenter_handle cacheado · endpoint enriquecido)
ABSORBED: PLAN-2026-05-14-watchlist-saymi.md (Fase 1+2 → BLOQUE 8)
ABSORBED: PLAN-2026-05-14-tier2-ux-followers-ig.md (Sprint A → BLOQUE 4 S-4.2 · Sprint B → BLOQUE 5 S-5.1 · Sprint C → BLOQUE 5 S-5.4)

NOTAS ACTIVE 2026-05-20:
- Sprint autónomo: Linda ejecuta sin pedir confirmación entre fases. PARO obligatorio en gate fallido.
- Cross-audit Gemini DEBE pasar antes de arrancar Fase 0.
- Hugo (peer s2ryygne) entrega dump RADAR. Coordinación vía claude-peers.
- Saymi prioridad #1 (dirigente_id=3), Pepe Monroy #2 (dirigente_id=57).
- Misael Fan #1 con 40/12 (D-MISAEL-VIP-40) verificación en F5.
- Backup BD pre-ingest obligatorio (postmortem S-8.1 lesson).
