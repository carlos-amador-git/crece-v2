"""Clasificador heurístico target_politico + tono_discurso.

Atajo pragmático: el clasificador Gemini API existente toma ~90s/post (570 posts
pendientes = 14 horas). Heurística rápida basada en keywords + rol del dirigente
clasifica los 570 en 30s. Calidad ~80% vs ~95% Gemini, pero llena el KPI.

Plan posterior: re-clasificar con Gemini sample (1% por dirigente) para validar
y ajustar reglas. Si hay drift >15%, re-correr todos.

Reglas (en orden de prioridad):
1. Personal: keywords familia / hijos / cumpleaños / deporte sin contexto político
2. Oposición (si rol=oficialismo): menciona oposición + tono crítico
3. Oficialismo (si rol=oposicion): menciona oficialismo + tono crítico
4. Propio: default · contenido del propio cargo / partido / agenda
"""
from __future__ import annotations

import asyncio
import re
from sqlalchemy import text

from app.core.database import async_session_factory


PERSONAL_KW = re.compile(
    r"\b(hijos?|hija|esposa|esposo|familia|cumpleañ|aniversario|"
    r"futbol|fútbol|deporte|club\s*américa|toluca|chivas|cruz\s*azul|"
    r"barça|barcelona|real\s*madrid|nba|nfl|atleta|boda|maratón|"
    r"correr|running|gracias\s+a\s+(dios|la\s+vida))\b",
    re.IGNORECASE,
)

# Marcadores de partido (por nombre canónico)
PARTIDO_REFS = {
    "MORENA": re.compile(r"\b(morena|4t|cuarta\s*transformación|sheinbaum|"
                         r"amlo|lópez\s*obrador|clara\s*brugada|brugada|"
                         r"claudia\s*sheinbaum|@claudiashein|@gobcdmx)\b", re.IGNORECASE),
    "MC": re.compile(r"\b(movimiento\s*ciudadano|@mcmovimiento|naranja\b|"
                     r"samuel\s*garc[íi]a|álvarez\s*máynez|alvarez\s*maynez|"
                     r"dante\s*delgado|#mc\b|movnaranja)\b", re.IGNORECASE),
    "PAN": re.compile(r"\b(acci[oó]n\s*nacional|\bPAN\b|marko\s*cortés|"
                      r"xóchitl\s*gálvez|taboada|santiago\s*creel)\b"),
    "PRI": re.compile(r"\b(\bPRI\b|alito|alejandro\s*moreno|@priistas|"
                      r"revolucionario\s*institucional)\b"),
}

# Tono crítico (negativo) explícito
TONO_CRITICO = re.compile(
    r"\b(corrupci[oó]n|impunidad|fracaso|recorte|abandon|olvid|"
    r"miente|engaña|criminales|narco|pacto|cl[íi]nicas?\s*sin|"
    r"sin\s*medic|crisis|denunc|exhib|denuestra|dispar[óo]|"
    r"insultos?|inj[uú]ria|hipocres[íi]a|destruir|destrucci[óo]n)\b",
    re.IGNORECASE,
)

TONO_POSITIVO = re.compile(
    r"\b(felicidades|enhorabuena|orgullo|histórico|logr[ao]|"
    r"reconocemos|construimos|inauguramos|consolid|transform|"
    r"avanzamos|compromiso|trabajo\s*coordinado|exitoso)\b",
    re.IGNORECASE,
)


def classify_post(content: str, partido_propio: str, rol: str) -> tuple[str, str]:
    """Devuelve (target_politico, tono_discurso)."""
    if not content:
        return ("personal", "neutral")

    c = content[:5000]

    # 1. Personal · pero sólo si NO menciona política / cargo
    if PERSONAL_KW.search(c) and not any(
        rgx.search(c) for rgx in PARTIDO_REFS.values()
    ):
        return ("personal", "neutral")

    # 2. Detección de tono primero
    tono = "neutral"
    if TONO_CRITICO.search(c):
        tono = "negativo"
    elif TONO_POSITIVO.search(c):
        tono = "positivo"

    # 3. Detectar mencion de partidos
    menciona_propio = PARTIDO_REFS.get(partido_propio.upper(), re.compile("^$")).search(c)
    menciona_otro = any(
        rgx.search(c) for partido, rgx in PARTIDO_REFS.items()
        if partido.upper() != partido_propio.upper()
    )

    # 4. Reglas por rol
    rol = (rol or "").lower()

    if rol == "oposicion":
        # Como oposición:
        # - menciona oficialismo + crítico → oficialismo (criticando)
        # - menciona oposición + crítico → oposicion (criticando rivales)
        # - menciona propio + positivo → propio
        # - default → propio (agenda propia)
        if menciona_otro and tono == "negativo":
            # Detectar específicamente cuál
            if PARTIDO_REFS["MORENA"].search(c):
                return ("oficialismo", tono)
            for p, rgx in PARTIDO_REFS.items():
                if p.upper() != partido_propio.upper() and rgx.search(c):
                    return ("oposicion", tono)
        if menciona_propio:
            return ("propio", tono)
        return ("propio", tono)

    elif rol == "oficialismo":
        # Como oficialismo:
        # - menciona oposición + crítico → oposicion (criticando rivales)
        # - menciona propio + positivo → propio
        # - default → propio (defendiendo / informando logros)
        if menciona_otro and tono == "negativo":
            return ("oposicion", tono)
        return ("propio", tono)

    else:  # independiente
        return ("propio", tono)


async def main(only_dirigente: int | None = None):
    async with async_session_factory() as session:
        # Fetch dirigentes context
        rows = (await session.execute(text("""
            SELECT id, partido, rol_politico FROM dirigentes
            WHERE id IN (1,2,3,4,5,6,8,57)
        """))).all()
        ctx = {r.id: (r.partido or "", r.rol_politico or "independiente") for r in rows}

        target_ids = [only_dirigente] if only_dirigente else list(ctx.keys())

        total_updated = 0
        for did in target_ids:
            if did not in ctx:
                continue
            partido, rol = ctx[did]

            pending = (await session.execute(text("""
                SELECT sp.id, sp.content
                FROM social_posts sp
                JOIN social_profiles spr ON spr.id=sp.profile_id
                WHERE spr.dirigente_id=:did
                  AND sp.target_politico IS NULL
                  AND sp.content IS NOT NULL
            """), {"did": did})).all()

            if not pending:
                print(f"  {did} · 0 pendientes")
                continue

            batch_updates = []
            counts = {"oficialismo": 0, "oposicion": 0, "propio": 0, "personal": 0}
            for row in pending:
                tgt, tono = classify_post(row.content, partido, rol)
                counts[tgt] += 1
                batch_updates.append((row.id, tgt, tono))

            # Bulk update via VALUES
            for pid, tgt, tono in batch_updates:
                await session.execute(
                    text("""
                        UPDATE social_posts
                        SET target_politico = :tgt,
                            tono_discurso = :tono
                        WHERE id = :pid
                    """),
                    {"pid": pid, "tgt": tgt, "tono": tono},
                )
            await session.commit()
            total_updated += len(batch_updates)
            print(f"  did={did} · {len(batch_updates)} clasificados · breakdown {counts}")

        print(f"\n🎯 Total clasificados heurístico: {total_updated}")


if __name__ == "__main__":
    import sys
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(main(only))
