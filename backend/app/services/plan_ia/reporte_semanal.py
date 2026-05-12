"""Plan IA · T11 — Reporte semanal PDF.

Genera un PDF de 1 página por dirigente con:
- Número de recomendaciones completadas en la semana + tasa éxito
- Top 3 recomendaciones exitosas (con link al post ejecutor)
- Próximas a vencer ventana (next 7 days)
- Principio conductual más usado + dominante en éxitos

Usa reportlab (pure Python, sin system deps). Retorna bytes del PDF o los escribe a disco.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.models.dirigente import Dirigente
from app.models.recomendacion_plan_ia import RecomendacionPlanIA
from app.models.social import SocialPost

logger = logging.getLogger(__name__)

BRAND_PRIMARY = colors.HexColor("#FF6600")  # MC CDMX orange
BRAND_DARK = colors.HexColor("#1A1A1A")
BRAND_GRAY = colors.HexColor("#595959")
BRAND_SOFT = colors.HexColor("#F2F2F2")


def _iso_week_bounds(year: int, week: int) -> tuple[datetime, datetime]:
    """ISO week number to (start_monday, end_sunday) in UTC."""
    jan4 = datetime(year, 1, 4, tzinfo=UTC)
    start_of_week1 = jan4 - timedelta(days=jan4.isoweekday() - 1)
    week_start = start_of_week1 + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=7)
    return week_start, week_end


def _post_link(post: SocialPost | None) -> str:
    if post is None:
        return "-"
    raw = getattr(post, "raw_data", None) or {}
    link = raw.get("link") or raw.get("url") or ""
    if link:
        return link
    return f"post#{post.id}"


def generar_pdf_dirigente(
    session: Session,
    dirigente_id: int,
    year: int | None = None,
    week: int | None = None,
    output_path: str | Path | None = None,
) -> bytes:
    """Genera el PDF semanal para un dirigente. Retorna bytes.

    Si `output_path` se proporciona, también escribe el PDF a disco.
    """
    if year is None or week is None:
        now = datetime.now(UTC)
        iso = now.isocalendar()
        year = iso.year
        week = iso.week

    week_start, week_end = _iso_week_bounds(year, week)
    next_week_end = week_end + timedelta(days=7)

    dirigente = session.get(Dirigente, dirigente_id)
    dirigente_name = getattr(dirigente, "full_name", f"Dirigente #{dirigente_id}")

    # 1. Recomendaciones completadas en la semana
    completadas = (
        session.query(RecomendacionPlanIA)
        .filter(
            RecomendacionPlanIA.dirigente_id == dirigente_id,
            RecomendacionPlanIA.estado.in_(("completada", "fallida")),
            RecomendacionPlanIA.updated_at >= week_start,
            RecomendacionPlanIA.updated_at < week_end,
        )
        .all()
    )
    total_comp = len(completadas)
    exitosas = [r for r in completadas if r.veredicto == "exitosa"]
    parciales = [r for r in completadas if r.veredicto == "parcial"]
    fallidas = [r for r in completadas if r.veredicto == "fallida"]

    if total_comp:
        tasa_exito = round(
            (len(exitosas) + 0.5 * len(parciales)) / total_comp, 4
        )
    else:
        tasa_exito = 0.0

    # 2. Top 3 exitosas
    top_exitosas = exitosas[:3]

    # 3. Próximas a vencer (próximos 7 días en ejecutada)
    proximas = (
        session.query(RecomendacionPlanIA)
        .filter(
            RecomendacionPlanIA.dirigente_id == dirigente_id,
            RecomendacionPlanIA.estado == "ejecutada",
            RecomendacionPlanIA.ventana_fin.isnot(None),
            RecomendacionPlanIA.ventana_fin >= week_end,
            RecomendacionPlanIA.ventana_fin < next_week_end,
        )
        .order_by(RecomendacionPlanIA.ventana_fin)
        .limit(5)
        .all()
    )

    # 4. Principio conductual más usado + dominante en éxitos
    principios_total = Counter(
        r.principio_conductual or "sin_principio" for r in completadas
    )
    principios_exitos = Counter(
        r.principio_conductual or "sin_principio" for r in exitosas
    )
    principio_mas_usado = principios_total.most_common(1)[0] if principios_total else None
    principio_dominante_exito = (
        principios_exitos.most_common(1)[0] if principios_exitos else None
    )

    # Build PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Reporte semanal Plan IA · {dirigente_name} · W{week}/{year}",
    )
    story: list[Any] = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        textColor=BRAND_DARK,
        fontSize=18,
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "subtitle",
        parent=styles["Normal"],
        textColor=BRAND_GRAY,
        fontSize=10,
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        textColor=BRAND_PRIMARY,
        fontSize=13,
        spaceAfter=6,
    )
    body = styles["Normal"]

    story.append(Paragraph(f"Reporte Plan IA · {dirigente_name}", title_style))
    story.append(
        Paragraph(
            f"Semana ISO {week}/{year} · {week_start.date().isoformat()} → "
            f"{(week_end - timedelta(days=1)).date().isoformat()}",
            subtitle_style,
        )
    )

    # KPI cards
    kpi_data = [
        ["Completadas", "Tasa éxito", "Exitosas", "Parciales", "Fallidas"],
        [
            str(total_comp),
            f"{tasa_exito * 100:.1f}%",
            str(len(exitosas)),
            str(len(parciales)),
            str(len(fallidas)),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[3.2 * cm] * 5)
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), BRAND_SOFT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                ("TOPPADDING", (0, 1), (-1, 1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 0.5 * cm))

    # Top 3 exitosas
    story.append(Paragraph("Top 3 recomendaciones exitosas", h2_style))
    if top_exitosas:
        rows = [["#", "Tipo", "Acción", "Post ejecutor"]]
        for i, rec in enumerate(top_exitosas, 1):
            post = session.get(SocialPost, rec.post_ejecutor_id) if rec.post_ejecutor_id else None
            rows.append(
                [
                    str(i),
                    rec.tipo or "-",
                    Paragraph((rec.accion_texto or "")[:200], body),
                    _post_link(post)[:60],
                ]
            )
        t = Table(rows, colWidths=[0.8 * cm, 2 * cm, 9 * cm, 5 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, BRAND_GRAY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_SOFT]),
                ]
            )
        )
        story.append(t)
    else:
        story.append(Paragraph("Sin recomendaciones exitosas esta semana.", body))
    story.append(Spacer(1, 0.4 * cm))

    # Próximas a vencer
    story.append(Paragraph("Próximas a vencer (siguientes 7 días)", h2_style))
    if proximas:
        rows = [["Vence", "Tipo", "Acción", "Criterio"]]
        for rec in proximas:
            criterio = rec.criterio_exito or {}
            criterio_str = (
                f"{criterio.get('metrica', '-')}: {criterio.get('objetivo', '-')}"
                if isinstance(criterio, dict)
                else "-"
            )
            rows.append(
                [
                    rec.ventana_fin.date().isoformat() if rec.ventana_fin else "-",
                    rec.tipo or "-",
                    Paragraph((rec.accion_texto or "")[:200], body),
                    criterio_str,
                ]
            )
        t = Table(rows, colWidths=[2.5 * cm, 2 * cm, 8 * cm, 4.3 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, BRAND_GRAY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_SOFT]),
                ]
            )
        )
        story.append(t)
    else:
        story.append(Paragraph("Sin recomendaciones próximas a vencer.", body))
    story.append(Spacer(1, 0.4 * cm))

    # Principios
    story.append(Paragraph("Principios conductuales", h2_style))
    if principio_mas_usado:
        story.append(
            Paragraph(
                f"<b>Más usado esta semana:</b> {principio_mas_usado[0]} "
                f"({principio_mas_usado[1]} recomendaciones)",
                body,
            )
        )
    else:
        story.append(Paragraph("Sin principios registrados en la semana.", body))

    if principio_dominante_exito:
        story.append(
            Paragraph(
                f"<b>Dominante en éxitos:</b> {principio_dominante_exito[0]} "
                f"({principio_dominante_exito[1]} exitosas)",
                body,
            )
        )

    story.append(Spacer(1, 0.6 * cm))
    story.append(
        Paragraph(
            f"<font color='#999999' size='8'>Generado automáticamente · "
            f"{datetime.now(UTC).isoformat(timespec='seconds')} · MD Consultoría TI</font>",
            body,
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdf_bytes)
        logger.info("reporte_semanal: PDF escrito en %s (%d bytes)", path, len(pdf_bytes))

    return pdf_bytes


def generar_reportes_todos_dirigentes(
    session: Session,
    output_dir: str | Path | None = None,
    year: int | None = None,
    week: int | None = None,
) -> dict[str, Any]:
    """Genera reportes semanales para todos los dirigentes con actividad reciente."""
    if year is None or week is None:
        now = datetime.now(UTC)
        iso = now.isocalendar()
        year = iso.year
        week = iso.week

    dirigentes_activos = (
        session.query(RecomendacionPlanIA.dirigente_id)
        .distinct()
        .all()
    )
    dirigente_ids = [d[0] for d in dirigentes_activos]

    generados = []
    errores: list[dict[str, Any]] = []
    for did in dirigente_ids:
        try:
            out_path = None
            if output_dir is not None:
                out_path = Path(output_dir) / f"reporte_plan_ia_{did}_W{week}_{year}.pdf"
            pdf_bytes = generar_pdf_dirigente(
                session, did, year=year, week=week, output_path=out_path
            )
            generados.append(
                {
                    "dirigente_id": did,
                    "bytes": len(pdf_bytes),
                    "path": str(out_path) if out_path else None,
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("reporte_semanal: error dirigente %d: %s", did, exc)
            errores.append({"dirigente_id": did, "error": str(exc)})

    return {
        "year": year,
        "week": week,
        "generados": len(generados),
        "errores": len(errores),
        "detalles": generados,
        "errores_detalle": errores,
    }
