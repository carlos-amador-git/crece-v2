"""Seed matriz v2 — 20 reglas nuevas para comments de terceros.

Aplica post-migration ds04. Idempotente via ON CONFLICT DO NOTHING sobre
unique key (version, rol, tono, target, contexto).

Bucket B — 6 overrides comment-specific:
    Casos donde la misma tupla (rol, tono, target) tiene polaridad distinta
    cuando quien emite es un follower vs el dirigente.

Bucket C — 14 reglas nuevas target=dirigente:
    Comments dirigidos al autor del post. Simétrico rol (oposición y oficialismo
    tienen los mismos 7 tonos con los mismos scores — la relación follower→dirigente
    es independiente de ideología en el score base).

Referencia completa en Obsidian:
    research/memory/2026-04-14-matriz-polaridad-v2-comments.md
"""
from __future__ import annotations

import os
import sys

import psycopg2

DB_DSN = os.environ.get(
    "DB_DSN",
    "host=localhost port=5438 dbname=crece user=crece password=crece_dev",
)

# (version, rol, tono, target, score, descripcion, contexto)
BUCKET_B_OVERRIDES = [
    ("v1", "oposicion", "celebratorio", "autopromocion", 0,
     "Follower se autopromueve: irrelevante para dirigente", "comment_tercero"),
    ("v1", "oposicion", "critico", "medios", 0,
     "Follower critica medios: no arrastra al dirigente", "comment_tercero"),
    ("v1", "oposicion", "propositivo", "gobierno", 1,
     "Follower civil propone al gobierno: eleva tono del timeline", "comment_tercero"),
    ("v1", "oficialismo", "celebratorio", "autopromocion", 0,
     "Follower se autopromueve: irrelevante", "comment_tercero"),
    ("v1", "oficialismo", "critico", "medios", 0,
     "Follower critica medios: no arrastra al dirigente", "comment_tercero"),
    ("v1", "independiente", "celebratorio", "autopromocion", 0,
     "Follower se autopromueve: irrelevante", "comment_tercero"),
]

BUCKET_C_DIRIGENTE = []
_TONO_DIRIGENTE = [
    ("ataque", -1, "Troll/detractor directo al dirigente"),
    ("critico", -1, "Decepción de base / crítica a la gestión"),
    ("celebratorio", 1, "Apoyo entusiasta al dirigente"),
    ("solidario", 1, "Apoyo emocional al dirigente"),
    ("propositivo", 0, "Sugerencia al dirigente: ambigua"),
    ("informativo", 0, "Dato sobre el dirigente: neutro"),
    ("personal", 0, "Comment personal-íntimo dirigido: neutro"),
]
for rol in ("oposicion", "oficialismo"):
    for tono, score, desc in _TONO_DIRIGENTE:
        BUCKET_C_DIRIGENTE.append(
            ("v1", rol, tono, "dirigente", score, desc, "comment_tercero")
        )

ALL_RULES = BUCKET_B_OVERRIDES + BUCKET_C_DIRIGENTE  # 6 + 14 = 20


def main():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    for v, rol, tono, target, score, desc, ctx in ALL_RULES:
        cur.execute(
            """
            INSERT INTO framework_matrix_defaults
                (version, rol, tono, target, score_politico, descripcion, contexto)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (version, rol, tono, target, contexto) DO NOTHING
            """,
            (v, rol, tono, target, score, desc, ctx),
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1
    cur.execute(
        "SELECT contexto, COUNT(*) FROM framework_matrix_defaults GROUP BY contexto ORDER BY contexto"
    )
    breakdown = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM framework_matrix_defaults")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(f"inserted: {inserted}")
    print(f"skipped (already present): {skipped}")
    print(f"breakdown by contexto: {breakdown}")
    print(f"total rules: {total}")
    if total < 52:
        sys.exit(f"Expected ≥52 rules, got {total}")


if __name__ == "__main__":
    main()
