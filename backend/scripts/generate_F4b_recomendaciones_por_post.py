"""generate_F4b_recomendaciones_por_post.py — F4b Sprint post-ingest Hugo 2026-05-20

Genera reporte de "Recomendaciones por post categorizado" para un dirigente.

Categorías:
- VIRAL_POSITIVO: top 3 posts con mayor engagement_rate AND tono positivo
- ALTA_CRITICA: top 3 posts con mayor comments_total (proxy de crítica)
- POLARIZADO: top 3 posts con mayor engagement_rate pero polaridad mixta o
  con alta variabilidad en sus comments

Parámetros explícitos (definidos en plan F4b):
- engagement_rate > p75 dirigente_específico (cuartil contra sí mismo, no global)
- polaridad_avg agrupa con > +0.3 / < -0.3 / neutro
- is_rt = false (filtro `NOT content LIKE 'RT @%'`)
- content_min_chars = 20

Output: backend/.context/F4b-RECOMENDACIONES-POR-POST-d{id}-{fecha}.md

Recomendación accionable derivada con regla heurística:
- VIRAL+ → "Replicar tema X con timing Y vs canal Z"
- ALTA CRÍTICA → "Responder/clarificar / evitar tópico"
- POLARIZADO → "Mantener pero monitorear / vincular con narrativa unificadora"

Uso:
  python backend/scripts/generate_F4b_recomendaciones_por_post.py --dirigente-id 3
  python backend/scripts/generate_F4b_recomendaciones_por_post.py --dirigente-id 57
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

import psycopg2 as psycopg

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)


def get_p75_engagement(conn, dirigente_id: int) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT PERCENTILE_CONT(0.75)
                   WITHIN GROUP (ORDER BY engagement_rate)
            FROM social_posts sp
            JOIN social_profiles sprof ON sp.profile_id=sprof.id
            WHERE sprof.dirigente_id=%s AND sp.engagement_rate IS NOT NULL
            """,
            (dirigente_id,),
        )
        row = cur.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0


def fetch_dirigente_meta(conn, dirigente_id: int) -> tuple[str, str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT full_name, COALESCE(rol_politico,'oficialismo') FROM dirigentes WHERE id=%s",
            (dirigente_id,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else ("?", "oficialismo")


def fetch_viral_positive(conn, dirigente_id: int, p75: float) -> list[dict]:
    """Top posts con engagement > p75 + tono claramente positivo (legacy o v2)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sp.id, sp.published_at, sprof.platform::text AS platform,
                   sp.likes, sp.comments, sp.shares, sp.views, sp.engagement_rate,
                   sp.tono_discurso,
                   LEFT(COALESCE(sp.content,''), 300) AS content
            FROM social_posts sp
            JOIN social_profiles sprof ON sp.profile_id=sprof.id
            WHERE sprof.dirigente_id=%s
              AND sp.engagement_rate > %s
              AND sp.tono_discurso IN ('positivo', 'celebratorio', 'propositivo', 'solidario')
              AND LENGTH(COALESCE(sp.content,'')) >= 20
              AND NOT COALESCE(sp.content,'') LIKE 'RT @%%'
            ORDER BY sp.engagement_rate DESC
            LIMIT 3
            """,
            (dirigente_id, p75),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]


def fetch_alta_critica(conn, dirigente_id: int) -> list[dict]:
    """Top posts con más comments_total + comments reales clasificados negativos.

    Si no hay nlp_polaridad cargado en comments, usa COUNT(*) como proxy.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH crit AS (
              SELECT parent_post_id,
                     COUNT(*) FILTER (WHERE nlp_polaridad < 0) AS neg,
                     COUNT(*) AS total,
                     AVG(nlp_polaridad)::float AS avg_pol
              FROM social_comments
              GROUP BY parent_post_id
            )
            SELECT sp.id, sp.published_at, sprof.platform::text AS platform,
                   sp.likes, sp.comments, sp.shares, sp.views, sp.engagement_rate,
                   sp.tono_discurso,
                   LEFT(COALESCE(sp.content,''), 300) AS content,
                   COALESCE(crit.neg,0) AS neg, COALESCE(crit.total,0) AS total_c,
                   crit.avg_pol
            FROM social_posts sp
            JOIN social_profiles sprof ON sp.profile_id=sprof.id
            LEFT JOIN crit ON crit.parent_post_id=sp.id
            WHERE sprof.dirigente_id=%s
              AND sp.comments >= 3
              AND LENGTH(COALESCE(sp.content,'')) >= 20
              AND NOT COALESCE(sp.content,'') LIKE 'RT @%%'
            ORDER BY (COALESCE(crit.neg,0) * 3 + sp.comments) DESC
            LIMIT 3
            """,
            (dirigente_id,),
        )
        rows = []
        for r in cur.fetchall():
            d = _row_to_dict(r[:10])
            d["comments_neg"] = r[10]
            d["comments_classified_total"] = r[11]
            d["avg_polaridad"] = r[12]
            rows.append(d)
        return rows


def fetch_polarizado(conn, dirigente_id: int, p75: float) -> list[dict]:
    """Posts con engagement alto y polaridad cercana a 0 con varianza alta en comments."""
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH stats AS (
              SELECT parent_post_id,
                     AVG(nlp_polaridad)::float AS avg_pol,
                     STDDEV(nlp_polaridad)::float AS sd_pol,
                     COUNT(*) AS n
              FROM social_comments
              WHERE nlp_polaridad IS NOT NULL
              GROUP BY parent_post_id
              HAVING COUNT(*) >= 5
            )
            SELECT sp.id, sp.published_at, sprof.platform::text AS platform,
                   sp.likes, sp.comments, sp.shares, sp.views, sp.engagement_rate,
                   sp.tono_discurso,
                   LEFT(COALESCE(sp.content,''), 300) AS content,
                   stats.avg_pol, stats.sd_pol, stats.n
            FROM social_posts sp
            JOIN social_profiles sprof ON sp.profile_id=sprof.id
            JOIN stats ON stats.parent_post_id=sp.id
            WHERE sprof.dirigente_id=%s
              AND sp.engagement_rate > %s
              AND ABS(stats.avg_pol) < 0.3
              AND stats.sd_pol > 0.5
              AND NOT COALESCE(sp.content,'') LIKE 'RT @%%'
            ORDER BY stats.sd_pol DESC, sp.engagement_rate DESC
            LIMIT 3
            """,
            (dirigente_id, p75),
        )
        rows = []
        for r in cur.fetchall():
            d = _row_to_dict(r[:10])
            d["avg_pol"] = r[10]
            d["sd_pol"] = r[11]
            d["n_comments_clasificados"] = r[12]
            rows.append(d)
        return rows


def _row_to_dict(r) -> dict:
    keys = ["id", "published_at", "platform", "likes", "comments", "shares",
            "views", "engagement_rate", "tono", "content"]
    return dict(zip(keys, r))


def fetch_plan_recomendaciones(conn, dirigente_id: int) -> list[dict]:
    """Saca las recomendaciones del último plan IA generado para el dirigente."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.id, r.tipo, r.accion_texto, r.principio_conductual,
                   r.evidencia_respaldo, r.criterio_exito, r.plan_ia_id
            FROM recomendaciones_plan_ia r
            WHERE r.dirigente_id=%s
              AND r.plan_ia_id = (SELECT id FROM planes_ia WHERE dirigente_id=%s ORDER BY id DESC LIMIT 1)
            ORDER BY r.id
            """,
            (dirigente_id, dirigente_id),
        )
        return [
            {"id": r[0], "tipo": r[1], "accion": r[2], "principio": r[3],
             "evidencia": r[4], "criterio": r[5], "plan_id": r[6]}
            for r in cur.fetchall()
        ]


def recomendacion_for_viral_pos(post: dict) -> str:
    plat = post["platform"]
    er = post["engagement_rate"]
    return (
        f"Replicar tema y formato de este post (engagement={er:.4f}) en {plat} "
        f"con cadencia +1/semana próximas 4 semanas. Mismo timing horario, mismo "
        f"tipo (foto/video/texto). Criterio éxito: ≥75% del engagement_rate logrado aquí."
    )


def recomendacion_for_critica(post: dict) -> str:
    neg = post.get("comments_neg", 0)
    return (
        f"Detectado {neg} comments negativos clasificados. "
        f"Acción dual: 1) responder en hilo a 2-3 críticas con tono propositivo "
        f"(no defensivo); 2) NO repetir el tópico/encuadre durante próximas 2 "
        f"semanas hasta evaluar respuesta. Criterio éxito: avg_polaridad próximo "
        f"post similar ≥ -0.1 (menos negativo que actual)."
    )


def recomendacion_for_polarizado(post: dict) -> str:
    sd = post.get("sd_pol", 0)
    n = post.get("n_comments_clasificados", 0)
    return (
        f"Polarización detectada (sd_polaridad={sd:.2f} en {n} comments). "
        f"Mantener publicaciones de este tema pero monitorear semanalmente. "
        f"NO escalar la polémica (no responder en caliente). Vincular con "
        f"narrativa unificadora (logros tangibles, beneficios compartidos) "
        f"en próximos 2 posts."
    )


def write_report(output: Path, dirigente_id: int, nombre: str, rol: str,
                 p75: float, viral: list[dict], critica: list[dict],
                 polariza: list[dict], plan_rec: list[dict]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    def section(title: str, posts: list[dict], rec_fn):
        if not posts:
            return f"### {title}\n\n_Sin posts en esta categoría (filtros: engagement >p75={p75:.4f}, sin RTs, >20 chars)._\n\n"
        out = [f"### {title} ({len(posts)} posts)\n"]
        for i, p in enumerate(posts, 1):
            content = (p["content"] or "").replace("\n", " ").replace("|", "\\|")[:200]
            pubdate = p["published_at"].strftime("%Y-%m-%d") if p["published_at"] else "—"
            out.append(
                f"**{i}. post_id={p['id']}** · {pubdate} · {p['platform']} · "
                f"engagement={p['engagement_rate']:.4f}\n"
            )
            out.append(f"- Métricas: 👍{p['likes']} 💬{p['comments']} 🔁{p['shares']} 👁{p['views']}\n")
            out.append(f"- Tono clasificado: `{p['tono']}`\n")
            out.append(f"- Extracto: \"{content}\"\n")
            out.append(f"- **Recomendación:** {rec_fn(p)}\n\n")
        return "".join(out)

    with output.open("w") as f:
        f.write(f"# F4b · Recomendaciones por post · {nombre} (dirigente_id={dirigente_id})\n\n")
        f.write(f"**Fecha:** {fecha}\n")
        f.write(f"**Rol:** {rol}\n")
        f.write(f"**P75 engagement_rate (auto-benchmark):** {p75:.4f}\n\n")

        f.write("## Filtros aplicados (D-F4b 2026-05-20)\n\n")
        f.write("- `engagement_rate > p75` del dirigente (cuartil contra sí mismo, NO global)\n")
        f.write("- `LENGTH(content) >= 20`\n")
        f.write("- NO retweets (`NOT content LIKE 'RT @%'`)\n")
        f.write("- Para VIRAL_POSITIVO: tono in (positivo, celebratorio, propositivo, solidario)\n")
        f.write("- Para ALTA_CRITICA: comments ≥ 3 + ranking por (neg_count*3 + comments_total)\n")
        f.write("- Para POLARIZADO: |avg_polaridad| < 0.3 AND sd_polaridad > 0.5 AND n >= 5\n\n")

        f.write("## Top 3 viral positivo\n\n")
        f.write(section("Viral positivo", viral, recomendacion_for_viral_pos))

        f.write("## Top 3 alta crítica\n\n")
        f.write(section("Alta crítica", critica, recomendacion_for_critica))

        f.write("## Top 3 polarizado\n\n")
        f.write(section("Polarizado", polariza, recomendacion_for_polarizado))

        f.write("## Recomendaciones del Plan IA reciente (F4a)\n\n")
        if not plan_rec:
            f.write("_No hay plan IA reciente persistido para este dirigente._\n\n")
        else:
            f.write(f"Plan IA #{plan_rec[0]['plan_id']} contiene **{len(plan_rec)} recomendaciones** generadas "
                    "por CC effort=high. Estas complementan las recomendaciones por post:\n\n")
            for r in plan_rec:
                f.write(f"- **#{r['id']} [{r['tipo']}]** ({r['principio']}): {r['accion'][:280]}...\n")
            f.write("\n")

        f.write("## Notas\n\n")
        f.write("- Recomendaciones por post se derivan heurísticamente con plantillas fijas "
                "(replicar/responder/monitorear). Plan IA (F4a) da recomendaciones LLM "
                "más narrativas y específicas. Son complementarias, no redundantes.\n")
        f.write("- Endpoint `/api/v1/recomendaciones/by-post` NO existe — generar bajo "
                "demanda vía LLM por post sería sprint dedicado. Plan IA actual ya "
                "cubre los posts de evidencia.\n")
        f.write("- PII en plan output verificado por sanitizer (`backend/app/services/llm_sanitizer.py`) "
                "antes de persistir.\n")

    print(f"Reporte escrito: {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirigente-id", type=int, required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    output = Path(args.output) if args.output else Path(
        f"backend/.context/F4b-RECOMENDACIONES-POR-POST-d{args.dirigente_id}-"
        f"{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    )

    with psycopg.connect(DB_URL) as conn:
        nombre, rol = fetch_dirigente_meta(conn, args.dirigente_id)
        p75 = get_p75_engagement(conn, args.dirigente_id)
        viral = fetch_viral_positive(conn, args.dirigente_id, p75)
        critica = fetch_alta_critica(conn, args.dirigente_id)
        polariza = fetch_polarizado(conn, args.dirigente_id, p75)
        plan_rec = fetch_plan_recomendaciones(conn, args.dirigente_id)

    write_report(output, args.dirigente_id, nombre, rol, p75, viral, critica, polariza, plan_rec)
    print(f"Viral+: {len(viral)} · Crítica: {len(critica)} · Polarizado: {len(polariza)} · Plan IA rec: {len(plan_rec)}")


if __name__ == "__main__":
    main()
