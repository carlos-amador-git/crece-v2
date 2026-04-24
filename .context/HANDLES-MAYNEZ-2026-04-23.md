# Handles oficiales Jorge Álvarez Máynez (id=7) — verificación 2026-04-23

**Propósito:** Máynez no tiene ningún row en `social_profiles`. Sweep de handles vía 2 fuentes oficiales independientes per criterio CEO, para habilitar insertion cuando F1.1 corra y el batch Gemma3 pueda cubrirlo.

**Dirigente:** Jorge Álvarez Máynez · Coordinador Nacional de Movimiento Ciudadano (desde 2024-12-05) · Ex-candidato presidencial MC 2024

---

## Tabla de verificación

| Plataforma | Handle propuesto | Fuente 1 | Fuente 2 | Decisión |
|---|---|---|---|---|
| X (Twitter) | `@AlvarezMaynez` | [movimientociudadano.mx/integrantes/jorge-alvarez-maynez](https://movimientociudadano.mx/integrantes/jorge-alvarez-maynez) (sitio oficial del partido, linkea a `twitter.com/AlvarezMaynez`) | [x.com/alvarezmaynez](https://x.com/alvarezmaynez?lang=es) (perfil directo activo, múltiples notas Infobae/CNN/Milenio confirman uso) | ✅ 2/2 — **confirmado** |
| Instagram | `alvarezmaynez` | movimientociudadano.mx/integrantes/... → `instagram.com/alvarezmaynez` | [instagram.com/alvarezmaynez/reels/](https://www.instagram.com/alvarezmaynez/reels/) (perfil directo activo) | ✅ 2/2 — **confirmado** |
| Facebook | `AlvarezMaynez` | movimientociudadano.mx/integrantes/... → `facebook.com/AlvarezMaynez` | [facebook.com/AlvarezMaynez/?locale=es_LA](https://www.facebook.com/AlvarezMaynez/?locale=es_LA) (perfil directo · 1.5M likes · Milenio confirma) | ✅ 2/2 — **confirmado** |
| TikTok | `@alvarezmaynez` | [tiktok.com/@alvarezmaynez](https://www.tiktok.com/@alvarezmaynez?lang=es) (perfil directo · 76.6M likes · bio linktr.ee/jorgemaynez) | Milenio "el candidato del TikTok" + Radio Fórmula + Bamba Política (múltiples notas de prensa) | ✅ 2/2 — **confirmado** |
| YouTube | `JorgeAlvarezMaynez` (legacy) | movimientociudadano.mx/integrantes/... → `youtube.com/user/JorgeAlvarezMaynez` | — (sin 2ª fuente independiente hallada en sweep) | ⚠️ 1/2 — **pendiente validación manual** |

---

## URLs canónicas para `social_profiles` insertion (post-F1.1)

```
Twitter/X:  https://x.com/AlvarezMaynez              handle: alvarezmaynez
Instagram:  https://instagram.com/alvarezmaynez      handle: alvarezmaynez
Facebook:   https://facebook.com/AlvarezMaynez       handle: alvarezmaynez
TikTok:     https://tiktok.com/@alvarezmaynez        handle: @alvarezmaynez
YouTube:    https://youtube.com/user/JorgeAlvarezMaynez  handle: jorgealvarezmaynez  (⚠️ verificar)
```

---

## Reglas al insertar

1. Ejecutar INSERT en `social_profiles` SOLO después de F1.1 aplicada (por si la migración de restauración modifica estructura).
2. `social_profiles.verified = true` para los 4 con 2/2; `false` para YouTube hasta segunda confirmación.
3. YouTube: intentar `youtube.com/@AlvarezMaynez` como alternativa moderna antes de aceptar `/user/JorgeAlvarezMaynez` legacy. Si responde 200 y muestra contenido político coherente, usar ese.
4. Scraping inicial debe correr antes del batch Layer 2 Gemma3 para que Máynez tenga datos.

---

## Fuentes consultadas

- [Sitio oficial Movimiento Ciudadano — perfil integrante](https://movimientociudadano.mx/integrantes/jorge-alvarez-maynez) — fuente partido, linkea los 4 handles
- [x.com/alvarezmaynez](https://x.com/alvarezmaynez?lang=es) — perfil directo
- [instagram.com/alvarezmaynez](https://www.instagram.com/alvarezmaynez/reels/) — perfil directo
- [facebook.com/AlvarezMaynez](https://www.facebook.com/AlvarezMaynez/?locale=es_LA) — perfil directo
- [tiktok.com/@alvarezmaynez](https://www.tiktok.com/@alvarezmaynez?lang=es) — perfil directo
- [INE — Candidaturas 2024 Máynez](https://candidaturas.ine.mx/detalleCandidato/1736/1) — contexto oficial
- [Wikipedia ES](https://es.wikipedia.org/wiki/Jorge_%C3%81lvarez_M%C3%A1ynez) — contexto biográfico
- [Infobae · nombramiento dirigente 2024-12-05](https://www.infobae.com/mexico/2024/12/05/nombran-a-alvarez-maynez-como-el-nuevo-dirigente-nacional-de-movimiento-ciudadano/)
- [Milenio · "candidato del TikTok"](https://www.milenio.com/politica/elecciones/jorge-alvarez-maynez-el-candidato-del-tiktok)

---

**Registrado por:** Claude Code sesión 2026-04-23 · post-meta-fix CLAUDE.md + PLAN-current.md redirect a `PLAN-recuperacion-post-incidente-2026-04-21.md`.
