"""Patch post-Gemini audit de la matriz v2 (2026-04-14).

Ajustes integrados:
1. REMOVE `oposicion + propositivo + gobierno (comment)` — fallback v1 post=0 es correcto.
   Gemini: "Follower proponiendo al gobierno empodera al adversario del dirigente opositor".
2. UPDATE `propositivo + dirigente (ambos roles, comment)` 0 → +1.
   Gemini: "Engagement propositivo de la base construye capital político, no debe ser neutral".
3. INSERT explícito `ataque + ciudadania (comment, ambos roles)` = -1.
   Gemini: "Flame wars degradan espacio digital del dirigente — evitar fallback silencioso a v1 post".

Idempotente.
"""
from __future__ import annotations

import os

import psycopg2

DB_DSN = os.environ.get(
    "DB_DSN",
    "host=localhost port=5438 dbname=crece user=crece password=crece_dev",
)


def main():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. REMOVE override oposicion + propositivo + gobierno (comment_tercero)
    cur.execute(
        """
        DELETE FROM framework_matrix_defaults
        WHERE version='v1' AND rol='oposicion' AND tono='propositivo'
          AND target='gobierno' AND contexto='comment_tercero'
        """
    )
    removed_1 = cur.rowcount

    # 2. UPDATE propositivo + dirigente 0 → +1 (both roles)
    cur.execute(
        """
        UPDATE framework_matrix_defaults
        SET score_politico = 1,
            descripcion = 'Engagement propositivo construye capital político (Gemini audit)'
        WHERE version='v1' AND tono='propositivo' AND target='dirigente'
          AND contexto='comment_tercero'
          AND rol IN ('oposicion', 'oficialismo')
        """
    )
    updated_2 = cur.rowcount

    # 3. INSERT ataque + ciudadania (comment) = -1 (ambos roles)
    new_rules = [
        ("v1", "oposicion", "ataque", "ciudadania", -1,
         "Flame war entre followers degrada espacio digital (Gemini audit)", "comment_tercero"),
        ("v1", "oficialismo", "ataque", "ciudadania", -1,
         "Flame war entre followers degrada espacio digital (Gemini audit)", "comment_tercero"),
    ]
    inserted_3 = 0
    for r in new_rules:
        cur.execute(
            """
            INSERT INTO framework_matrix_defaults
                (version, rol, tono, target, score_politico, descripcion, contexto)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (version, rol, tono, target, contexto) DO NOTHING
            """,
            r,
        )
        if cur.rowcount == 1:
            inserted_3 += 1

    # Verification
    cur.execute(
        "SELECT contexto, COUNT(*) FROM framework_matrix_defaults GROUP BY contexto"
    )
    breakdown = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM framework_matrix_defaults")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"1. Removed oposicion+propositivo+gobierno(comment): {removed_1}")
    print(f"2. Updated propositivo+dirigente → +1: {updated_2}")
    print(f"3. Inserted ataque+ciudadania(comment) rules: {inserted_3}")
    print(f"breakdown: {breakdown}")
    print(f"total rules: {total}")


if __name__ == "__main__":
    main()
