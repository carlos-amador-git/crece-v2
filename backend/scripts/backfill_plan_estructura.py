"""
Backfill estructura_json on existing PlanIA rows that have markdown contenido
but null estructura_json.

Parses the markdown to extract titulo, tesis_central, and tareas.
Run with: python -m scripts.backfill_plan_estructura
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _parse_markdown_to_estructura(contenido: str) -> dict:
    """Parse markdown plan content into PlanEstructurado-compatible JSON.

    Extracts:
    - titulo_campana: from first H1 or H2
    - tesis_central: from first paragraph or diagnostic section
    - problematicas_direccionadas: from bullet points in early sections
    - tareas: from H3 sections or numbered items
    """
    lines = contenido.strip().split("\n")

    # --- Extract titulo ---
    titulo = "Plan sin titulo"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            titulo = stripped.lstrip("# ").strip()
            break
        if stripped.startswith("## "):
            titulo = stripped.lstrip("## ").strip()
            break

    # Trim to 200 chars
    titulo = titulo[:200]
    if len(titulo) < 5:
        titulo = "Plan generado automaticamente"

    # --- Extract tesis_central ---
    # Look for first substantial paragraph (non-header, non-bullet, >50 chars)
    tesis = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("-") or stripped.startswith("*"):
            continue
        if stripped.startswith("|"):
            continue
        if len(stripped) > 50:
            tesis = stripped
            break

    # If no paragraph found, concatenate early bullet points
    if len(tesis) < 50:
        bullets = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                bullets.append(stripped.lstrip("-* ").strip())
                if len(". ".join(bullets)) > 50:
                    break
        tesis = ". ".join(bullets) if bullets else contenido[:200]

    # Enforce min 50 chars
    if len(tesis) < 50:
        tesis = tesis + " " + contenido[:200]
    tesis = tesis[:1000]

    # --- Extract problematicas ---
    problematicas = []
    in_diagnostico = False
    for line in lines:
        stripped = line.strip()
        if "diagnos" in stripped.lower() or "problem" in stripped.lower():
            in_diagnostico = True
            continue
        if in_diagnostico and stripped.startswith("###"):
            in_diagnostico = False
            continue
        if in_diagnostico and (stripped.startswith("- ") or stripped.startswith("* ")):
            item = stripped.lstrip("-* ").strip()
            if item:
                problematicas.append(item[:200])
        if len(problematicas) >= 10:
            break

    if not problematicas:
        problematicas = ["Presencia digital insuficiente"]

    # --- Extract tareas from ### sections or numbered items ---
    tareas = []
    current_section = None

    for line in lines:
        stripped = line.strip()

        # H3 headers become section context
        if stripped.startswith("### "):
            current_section = stripped.lstrip("### ").strip()
            continue

        # Numbered items (1. **Title**: description or 1. text)
        match = re.match(r"^\d+\.\s+\*\*(.+?)\*\*[:\s]*(.*)", stripped)
        if match:
            t_titulo = match.group(1).strip()
            t_desc = match.group(2).strip()
            if len(t_titulo) < 5:
                t_titulo = f"{current_section or 'Tarea'}: {t_titulo}"
            if len(t_desc) < 20:
                t_desc = f"{t_titulo} - {t_desc}" if t_desc else t_titulo
                if current_section:
                    t_desc = f"{current_section}: {t_desc}"
            # Pad description if still short
            while len(t_desc) < 20:
                t_desc += " (pendiente de detallar)"
            tareas.append({
                "titulo": t_titulo[:200],
                "descripcion": t_desc[:2000],
                "orden": len(tareas),
            })
            continue

        # Plain numbered items: 1. Some text here
        match2 = re.match(r"^\d+\.\s+(.{5,})", stripped)
        if match2 and current_section:
            t_text = match2.group(1).strip()
            t_titulo = t_text[:200]
            t_desc = f"{current_section}: {t_text}"
            while len(t_desc) < 20:
                t_desc += " (pendiente de detallar)"
            tareas.append({
                "titulo": t_titulo[:200],
                "descripcion": t_desc[:2000],
                "orden": len(tareas),
            })

    # If we got fewer than 5, create generic tareas from H3 sections
    if len(tareas) < 5:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("### "):
                section_title = stripped.lstrip("### ").strip()
                # Skip if already captured
                if any(t["titulo"] == section_title for t in tareas):
                    continue
                desc = f"Ejecutar actividades de: {section_title}"
                while len(desc) < 20:
                    desc += " (pendiente de detallar)"
                if len(section_title) >= 5:
                    tareas.append({
                        "titulo": section_title[:200],
                        "descripcion": desc[:2000],
                        "orden": len(tareas),
                    })

    # Still fewer than 5? Add padding tareas
    while len(tareas) < 5:
        idx = len(tareas) + 1
        tareas.append({
            "titulo": f"Tarea pendiente de definir #{idx}",
            "descripcion": f"Tarea extraida del plan original pendiente de detalle. Revisar contenido markdown para completar.",
            "orden": len(tareas),
        })

    # Cap at 20
    tareas = tareas[:20]

    return {
        "titulo_campana": titulo,
        "tesis_central": tesis,
        "problematicas_direccionadas": problematicas,
        "tareas": tareas,
    }


async def backfill():
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find plans with null estructura_json
        result = await session.execute(
            text(
                "SELECT id, contenido FROM planes_ia "
                "WHERE estructura_json IS NULL AND contenido IS NOT NULL"
            )
        )
        rows = result.fetchall()

        if not rows:
            print("No plans found with null estructura_json. Nothing to backfill.")
            await engine.dispose()
            return

        print(f"Found {len(rows)} plan(s) to backfill.\n")

        updated = 0
        for row in rows:
            plan_id, contenido = row
            try:
                estructura = _parse_markdown_to_estructura(contenido)
                await session.execute(
                    text(
                        "UPDATE planes_ia SET estructura_json = :json WHERE id = :id"
                    ),
                    {"json": json.dumps(estructura, ensure_ascii=False), "id": plan_id},
                )
                updated += 1
                print(f"  [OK] Plan {plan_id}: '{estructura['titulo_campana'][:60]}' -> {len(estructura['tareas'])} tareas")
            except Exception as e:
                print(f"  [ERR] Plan {plan_id}: {e}")

        await session.commit()
        print(f"\nBackfill complete: {updated}/{len(rows)} plans updated.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(backfill())
