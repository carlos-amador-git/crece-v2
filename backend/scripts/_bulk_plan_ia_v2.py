"""Bulk generator de Plan IA CONSOLIDACION v2 (2026-05-12).

Para cada dirigente, lee el FODA del DIAGNOSTICO más reciente (no lo reemplaza),
deriva tareas estratégicas + integra 8 efemerides próximas 60 días + bloqueos
analíticos conocidos. INSERT nuevo CONSOLIDACION sin destruir versiones previas.

Cubre: 1 (Piña), 2 (Solano), 3 (Pineda), 4 (Nolasco), 5 (Jiménez), 6 (Cravioto),
8 (Ballesteros). Pepe (57) ya fue procesado por separado.

Idempotente: agrega un nuevo CONSOLIDACION con timestamp actual. La FODA endpoint
lee MAX(created_at) → el nuevo plan será el visible.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from sqlalchemy import text

from app.core.database import async_session_factory
from app.api.v1.endpoints.diagnostico import _parse_foda


def parse_foda_simple(contenido: str) -> dict[str, list[str]]:
    """Wrap parser oficial. Limita a 5 items por cuadrante."""
    full = _parse_foda(contenido or "")
    return {k: (v or [])[:5] for k, v in full.items()}


async def fetch_dirigente_context(session, did: int) -> dict:
    row = (await session.execute(
        text("""
            SELECT id, full_name, cargo, partido, estado, rol_politico
            FROM dirigentes WHERE id = :id
        """),
        {"id": did},
    )).first()
    if not row:
        return {}
    d = dict(row._mapping)

    profiles = (await session.execute(
        text("""
            SELECT platform::text as platform, handle, followers_count, posts_count
            FROM social_profiles WHERE dirigente_id = :id
            ORDER BY followers_count DESC
        """),
        {"id": did},
    )).all()
    d["profiles"] = [dict(p._mapping) for p in profiles]
    d["followers_total"] = sum((p._mapping["followers_count"] or 0) for p in profiles)

    posts_row = (await session.execute(
        text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE sp.sentiment_label='POSITIVE') AS positive,
                COUNT(*) FILTER (WHERE sp.sentiment_label='NEGATIVE') AS negative,
                COUNT(*) FILTER (WHERE sp.sentiment_label='NEUTRAL') AS neutral
            FROM social_posts sp
            JOIN social_profiles spr ON spr.id=sp.profile_id
            WHERE spr.dirigente_id=:id
              AND sp.scraped_at >= NOW() - INTERVAL '90 days'
        """),
        {"id": did},
    )).first()
    d["posts_90d"] = dict(posts_row._mapping) if posts_row else {"total": 0}

    comments_row = (await session.execute(
        text("""
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT sc.author_hash) AS unique_authors,
                COUNT(*) FILTER (WHERE sc.nlp_polaridad = 1) AS approve,
                COUNT(*) FILTER (WHERE sc.nlp_polaridad = -1) AS reject
            FROM social_comments sc
            JOIN social_posts sp ON sp.id=sc.parent_post_id
            JOIN social_profiles spr ON spr.id=sp.profile_id
            WHERE spr.dirigente_id=:id
              AND sc.nlp_model_version='comment-framework-v2'
        """),
        {"id": did},
    )).first()
    d["comments"] = dict(comments_row._mapping) if comments_row else {"total": 0}

    diag_row = (await session.execute(
        text("""
            SELECT id, contenido, modelo_ia, created_at
            FROM planes_ia WHERE dirigente_id=:id AND tipo='DIAGNOSTICO'
            ORDER BY created_at DESC LIMIT 1
        """),
        {"id": did},
    )).first()
    if diag_row:
        d["diagnostico_id"] = diag_row.id
        d["foda"] = parse_foda_simple(diag_row.contenido or "")
        d["diag_modelo"] = diag_row.modelo_ia
    else:
        d["diagnostico_id"] = None
        d["foda"] = {"fortalezas": [], "oportunidades": [], "debilidades": [], "amenazas": []}
        d["diag_modelo"] = "—"

    return d


async def fetch_efemerides_60d(session) -> list[dict]:
    """8 efemerides próximas 60 días, ordenadas por viralidad y fecha."""
    rows = (await session.execute(
        text("""
            WITH base AS (
              SELECT mes, dia, titulo, viralidad,
                MAKE_DATE(2026, mes, dia) AS fecha
              FROM efemerides
              WHERE (mes=5 AND dia >= 12) OR (mes=6) OR (mes=7 AND dia <= 12)
            )
            SELECT fecha, titulo, viralidad
            FROM base
            ORDER BY
              CASE viralidad WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END,
              fecha
            LIMIT 8
        """)
    )).all()
    return [{"fecha": r.fecha.isoformat(), "titulo": r.titulo, "viralidad": r.viralidad} for r in rows]


def build_tareas_desde_foda(foda: dict[str, list[str]]) -> list[dict]:
    """Deriva 5-7 tareas accionables del FODA parseado."""
    tareas = []

    # 1 tarea por debilidad (hasta 2) — START
    for d in foda["debilidades"][:2]:
        tareas.append({
            "tipo": "START",
            "objetivo": "Mitigar debilidad detectada",
            "accion": d,
        })

    # 1 tarea por oportunidad (hasta 3) — START
    for o in foda["oportunidades"][:3]:
        tareas.append({
            "tipo": "START",
            "objetivo": "Apalancar oportunidad",
            "accion": o,
        })

    # 1 tarea por fortaleza (hasta 1) — CONTINUE
    for f in foda["fortalezas"][:1]:
        tareas.append({
            "tipo": "CONTINUE",
            "objetivo": "Escalar fortaleza",
            "accion": f,
        })

    # 1 tarea por amenaza — MITIGAR
    for a in foda["amenazas"][:1]:
        tareas.append({
            "tipo": "MITIGAR",
            "objetivo": "Mitigar amenaza",
            "accion": a,
        })

    return tareas


def build_markdown(d: dict, tareas: list[dict], efemerides: list[dict]) -> str:
    profile_lines = [
        f"- **{p['platform']}** @{p['handle']} · {p['followers_count']:,} followers"
        for p in d["profiles"]
    ]
    posts = d["posts_90d"]
    comments = d["comments"]

    md = f"""# Plan Estratégico — {d['full_name']}

**Cargo:** {d['cargo'] or '—'}
**Partido:** {d['partido'] or '—'} · **Rol:** {d.get('rol_politico') or '—'}
**Audiencia total:** ~{d['followers_total']:,} seguidores
**Posts últimos 90d:** {posts.get('total', 0)} ({posts.get('positive', 0)} positivos / {posts.get('neutral', 0)} neutros / {posts.get('negative', 0)} negativos)
**Comments analizados (matriz v2):** {comments.get('total', 0)} de {comments.get('unique_authors', 0)} autores únicos · aprob {comments.get('approve', 0)} · rech {comments.get('reject', 0)}
**Modelo:** claude-code-2026-05-12 · derivado del DIAGNOSTICO `{d['diag_modelo']}` (id={d['diagnostico_id']})

---

## Perfiles activos

{chr(10).join(profile_lines) if profile_lines else '_(sin perfiles registrados)_'}

---

## Tareas estratégicas derivadas del FODA

"""

    for i, t in enumerate(tareas, 1):
        md += f"### {i}. {t['tipo']} — {t['objetivo']}\n{t['accion']}\n\n"

    md += "---\n\n## Calendario editorial — efemérides próximas 60 días\n\n"
    md += "Cada efeméride se trabaja con post en las redes activas. Plantilla disponible "
    md += "en `/dashboard/calendario` (botón \"Sugerir post\").\n\n"
    md += "| Fecha | Efeméride | Viralidad |\n|-------|-----------|----------|\n"
    for e in efemerides:
        md += f"| {e['fecha']} | {e['titulo']} | {e['viralidad']} |\n"

    md += "\n---\n\n## Notas\n\n"
    md += f"- El FODA detallado vive en el DIAGNOSTICO `{d['diag_modelo']}` (id={d['diagnostico_id']}). "
    md += "Este Plan deriva las tareas operativas; la lectura completa del análisis sigue allí.\n"
    md += "- Próxima revisión sugerida: " + (datetime.now(UTC).replace(month=((datetime.now(UTC).month % 12) + 1)).date().isoformat()) + " (30 días).\n\n"
    md += "*Plan generado por Claude Code — 2026-05-12 · grounded en FODA real sin invención.*\n"

    return md


async def main():
    DIRIGENTES = [1, 2, 3, 4, 5, 6, 8]
    async with async_session_factory() as session:
        admin_uid = (await session.execute(
            text("SELECT id FROM users WHERE role='ADMIN' LIMIT 1")
        )).scalar_one()

        efemerides = await fetch_efemerides_60d(session)
        print(f"Efemerides cargadas: {len(efemerides)}")

        for did in DIRIGENTES:
            d = await fetch_dirigente_context(session, did)
            if not d:
                print(f"  ⚠️  dirigente {did} no encontrado")
                continue

            tareas = build_tareas_desde_foda(d["foda"])
            md = build_markdown(d, tareas, efemerides)

            estructura = {
                "version": "claude-code-bulk-v2-2026-05-12",
                "generado_por": "claude-code-2026-05-12",
                "dirigente_id": did,
                "tareas_count": len(tareas),
                "diagnostico_id_base": d["diagnostico_id"],
                "diagnostico_modelo": d["diag_modelo"],
                "efemerides_count": len(efemerides),
                "foda_items": {k: len(v) for k, v in d["foda"].items()},
                "baseline": {
                    "posts_90d": d["posts_90d"].get("total", 0),
                    "comments_v2": d["comments"].get("total", 0),
                    "comentaristas_unicos": d["comments"].get("unique_authors", 0),
                    "followers_total": d["followers_total"],
                },
            }

            # NO DELETE — agregamos como nueva versión. El endpoint FODA lee MAX(created_at).
            await session.execute(
                text("""
                    INSERT INTO planes_ia
                        (dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                         generado_por_id, aprobado, estructura_json, created_at)
                    VALUES (:did, 'CONSOLIDACION', :contenido, 'claude-code-2026-05-12',
                            'scripts/_bulk_plan_ia_v2.py', :uid, false,
                            CAST(:struct AS JSONB), NOW())
                """),
                {
                    "did": did,
                    "contenido": md,
                    "uid": admin_uid,
                    "struct": json.dumps(estructura),
                },
            )
            print(f"  ✅ {d['full_name']} (id={did}) · {len(tareas)} tareas · {len(md)} chars")

        await session.commit()
        print(f"\n🎯 {len(DIRIGENTES)} CONSOLIDACIONes creadas")


if __name__ == "__main__":
    asyncio.run(main())
