#!/usr/bin/env python3
"""
Seed the political framework:
1. contexto_politico — who governs what scope (federal/CDMX/Oaxaca)
2. framework_matrix_defaults v1 — published defaults (suave +1/-1/0)
3. dirigentes.rol_politico — derive from partido vs contexto
"""
import os

import psycopg2

DB_URL = os.environ.get("DATABASE_URL_SYNC", "postgresql://crece:crece_dev@localhost:5438/crece")


CONTEXTO_POLITICO = [
    # (ambito, entidad, partido_gobernante, vigente_desde)
    ("federal", None, "MORENA", "2024-10-01"),
    ("estatal", "CDMX", "MORENA", "2024-10-05"),
    ("estatal", "OAXACA", "MORENA", "2022-12-01"),
    ("estatal", "NUEVO_LEON", "MC", "2021-10-04"),
    ("estatal", "JALISCO", "MC", "2024-12-06"),
]


# Matrix v1 — defaults published. Scale +1/-1/0 (suave, recommendation of Gemini)
# Format: (rol, tono, target, score, descripcion)
MATRIX_V1 = [
    # ── Oposición ─────────────────────────────────────────────────────
    ("oposicion", "critico",     "gobierno",       +1, "Fiscalización efectiva del gobierno en turno"),
    ("oposicion", "critico",     "ciudadania",     -1, "Criticar ciudadanía daña imagen"),
    ("oposicion", "critico",     "oposicion",      -1, "Disidencia interna opositora"),
    ("oposicion", "critico",     "medios",         -1, "Atacar medios es riesgoso"),
    ("oposicion", "propositivo", "gobierno",        0, "Propuesta al gobierno: neutral"),
    ("oposicion", "propositivo", "ciudadania",     +1, "Proponer a la ciudadanía construye marca"),
    ("oposicion", "celebratorio","autopromocion",  +1, "Construcción de marca personal"),
    ("oposicion", "celebratorio","ciudadania",      0, "Celebrar ciudadanía es neutral"),
    ("oposicion", "informativo", "tema_especifico", 0, "Información neutral sobre temas"),
    ("oposicion", "solidario",   "ciudadania",     +1, "Solidaridad con ciudadanía suma"),
    ("oposicion", "ataque",      "gobierno",       +1, "Ataque directo al gobierno: efectivo para base"),
    ("oposicion", "ataque",      "oposicion",      -1, "Ataque a aliados opositores: divisivo"),
    ("oposicion", "personal",    "autopromocion",   0, "Contenido personal: sin impacto político"),
    # ── Oficialismo ──────────────────────────────────────────────────
    ("oficialismo","critico",    "oposicion",      +1, "Crítica a oposición desde el poder"),
    ("oficialismo","critico",    "gobierno",       -1, "Disidencia interna oficialista"),
    ("oficialismo","critico",    "ciudadania",     -1, "Criticar ciudadanía daña imagen"),
    ("oficialismo","propositivo","gobierno",        0, "Alineación con agenda oficial: esperable"),
    ("oficialismo","propositivo","ciudadania",     +1, "Propuesta a ciudadanía: suma"),
    ("oficialismo","celebratorio","gobierno",       0, "Celebrar al gobierno propio: esperable"),
    ("oficialismo","celebratorio","ciudadania",    +1, "Celebración compartida con ciudadanía"),
    ("oficialismo","celebratorio","autopromocion", +1, "Construcción de marca desde el poder"),
    ("oficialismo","informativo","tema_especifico", 0, "Información neutral"),
    ("oficialismo","solidario",  "ciudadania",     +1, "Solidaridad oficialista: suma"),
    ("oficialismo","ataque",     "oposicion",      +1, "Ataque efectivo a oposición"),
    ("oficialismo","ataque",     "gobierno",       -1, "Atacar al gobierno propio: muy mal"),
    ("oficialismo","personal",   "autopromocion",   0, "Personal: neutro"),
    # ── Independiente ────────────────────────────────────────────────
    ("independiente","critico",  "gobierno",        0, "Crítica sin alineación clara: neutral"),
    ("independiente","critico",  "oposicion",       0, "Crítica a oposición: neutral"),
    ("independiente","propositivo","ciudadania",   +1, "Propuesta construye marca"),
    ("independiente","celebratorio","autopromocion",+1,"Construcción de marca personal"),
    ("independiente","solidario","ciudadania",     +1, "Solidaridad construye imagen"),
    ("independiente","personal", "autopromocion",   0, "Personal: neutro"),
]


DIRIGENTES_ROL = {
    # dirigente_id: rol
    # Resolved manually — could be derived automatically from partido vs contexto
    1: "oposicion",    # Piña MC vs MORENA CDMX
    2: "oposicion",    # Solano MC vs MORENA CDMX
    3: "oficialismo",  # Pineda Secretaria Turismo Oaxaca MORENA (gobierno OAX MORENA)
    4: "oficialismo",  # Nolasco Gobierno Oaxaca MORENA
    5: "oficialismo",  # Jiménez Godoy Diputada MORENA federal
    6: "oficialismo",  # Cravioto diputado MORENA CDMX
}


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 1. Seed contexto_politico
    cur.execute("SELECT COUNT(*) FROM contexto_politico;")
    if cur.fetchone()[0] == 0:
        for ambito, entidad, partido, fecha in CONTEXTO_POLITICO:
            cur.execute(
                "INSERT INTO contexto_politico (ambito, entidad, partido_gobernante, vigente_desde) VALUES (%s, %s, %s, %s);",
                (ambito, entidad, partido, fecha),
            )
        print(f"Inserted {len(CONTEXTO_POLITICO)} contexto_politico rows")

    # 2. Seed framework_matrix_defaults v1
    cur.execute("SELECT COUNT(*) FROM framework_matrix_defaults WHERE version = 'v1';")
    if cur.fetchone()[0] == 0:
        for rol, tono, target, score, desc in MATRIX_V1:
            cur.execute(
                """INSERT INTO framework_matrix_defaults (version, rol, tono, target, score_politico, descripcion)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                ("v1", rol, tono, target, score, desc),
            )
        print(f"Inserted {len(MATRIX_V1)} framework_matrix_defaults v1 rows")

    # 3. Set rol_politico on dirigentes
    for dirigente_id, rol in DIRIGENTES_ROL.items():
        cur.execute(
            "UPDATE dirigentes SET rol_politico = %s WHERE id = %s;",
            (rol, dirigente_id),
        )
    print(f"Updated rol_politico for {len(DIRIGENTES_ROL)} dirigentes")

    conn.commit()

    # 4. Verify
    cur.execute("SELECT rol_politico, COUNT(*) FROM dirigentes GROUP BY rol_politico;")
    print("\nrol_politico distribution:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cur.execute("SELECT rol, COUNT(*), AVG(score_politico)::numeric(3,1) FROM framework_matrix_defaults WHERE version='v1' GROUP BY rol ORDER BY rol;")
    print("\nMatrix defaults by rol:")
    print(f"  {'rol':<15} {'rules':>7} {'avg_score':>10}")
    for row in cur.fetchall():
        print(f"  {row[0]:<15} {row[1]:>7} {float(row[2]):>10.1f}")

    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
