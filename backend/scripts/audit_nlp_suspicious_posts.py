"""audit_nlp_suspicious_posts.py — F3b Sprint post-ingest Hugo 2026-05-20

Detección heurística de falsos positivos NLP en `social_posts.tono_discurso`.
Diseñado para validar el sample empíricamente sin depender de "ground truth
humano" (que requeriría 50 anotaciones manuales del CEO/Linda).

Patrón detección:
1. Posts clasificados como "celebratorio"/"propositivo"/"personal" que contienen
   palabras críticas (muertos, violencia, accidente, denuncia, escándalo, etc.)
2. Posts clasificados como "critico"/"ataque" con palabras positivas (gracias,
   logro, felicito, celebro, festejo).
3. Casos conocidos del notebook de errores (precedente Alebrijes, Día del Niño):
   posts mencionando estos temas con polaridad NEGATIVA fuerte.

Salida: backend/.context/F3b-NLP-SUSPICIOUS-d{id}-{fecha}.md con tabla de
sospechosos para revisar manualmente. Si la tasa supera 10% del sample
clasificado, reporta al CEO antes de F4.

Uso:
  python backend/scripts/audit_nlp_suspicious_posts.py --dirigente-id 3
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from pathlib import Path

import psycopg2 as psycopg

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)

# Palabras críticas: si aparecen, post NO debería ser celebratorio/propositivo/personal puro
PALABRAS_CRITICAS = {
    "muerte", "muertos", "muerto", "muerta", "fallecido", "fallecidos",
    "violencia", "violento", "violenta",
    "accidente", "accidentes", "tragedia", "tragico",
    "denuncia", "denuncio", "denunciar",
    "escandalo", "escandalos", "corrupcion", "corrupto",
    "asesinato", "asesino", "homicidio", "feminicidio",
    "agresion", "atentado", "balacera", "tiroteo",
    "abuso", "abusan", "abusado",
    "crisis", "colapso", "fracaso", "fracasado",
    "indignacion", "indignante", "vergüenza", "verguenza",
    "secuestro", "secuestrado", "desaparecido",
}

# Palabras positivas fuertes: NO deberían estar en post critico/ataque
PALABRAS_POSITIVAS = {
    "gracias", "agradezco", "agradecer",
    "felicito", "felicitaciones", "felicidades",
    "celebro", "celebramos", "celebracion",
    "festejo", "festejamos", "festejar",
    "logro", "logramos", "logrado",
    "exito", "exitoso", "exitosamente",
    "orgullo", "orgulloso", "orgullosa",
    "alegria", "alegre", "feliz",
}

# Casos conocidos del notebook 2026-05-15 (Alebrijes/Día del Niño)
TEMAS_PRECEDENTE = {
    "alebrije", "alebrijes",
    "dia del niño", "día del niño", "niños",
    "campeón", "campeon", "campeones",
    "trofeo", "medalla", "ganador", "ganadores",
}


def normalize(text: str) -> str:
    if not text:
        return ""
    txt = text.lower()
    # quitar acentos básico
    repl = str.maketrans("áéíóúüñ", "aeiouun")
    return txt.translate(repl)


def find_keywords(content: str, keywords: set[str]) -> list[str]:
    if not content:
        return []
    norm = normalize(content)
    hits = []
    for kw in keywords:
        kw_norm = normalize(kw)
        if re.search(rf"\b{re.escape(kw_norm)}\b", norm):
            hits.append(kw)
    return hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirigente-id", type=int, required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    output = Path(args.output) if args.output else Path(
        f"backend/.context/F3b-NLP-SUSPICIOUS-d{args.dirigente_id}-"
        f"{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    )

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sp.id, sp.published_at, sp.content,
                       sp.tono_discurso, sp.target_politico,
                       sp.sentimiento_politico_ajustado,
                       sp.nlp_model_version,
                       sprof.platform::text AS platform
                FROM social_posts sp
                JOIN social_profiles sprof ON sp.profile_id = sprof.id
                WHERE sprof.dirigente_id = %s
                  AND sp.tono_discurso IS NOT NULL
                  AND sp.content IS NOT NULL
                  AND LENGTH(sp.content) > 20
                ORDER BY sp.published_at DESC NULLS LAST
                """,
                (args.dirigente_id,),
            )
            rows = cur.fetchall()

        cur.close()

    if not rows:
        print(f"No hay posts clasificados para dirigente_id={args.dirigente_id}")
        return

    total = len(rows)
    sospechosos_tono_critico_en_post_celebratorio = []
    sospechosos_palabras_positivas_en_critico = []
    casos_precedente = []

    # Detectar vocabulario por post: v2 (celebratorio/critico/etc) vs legacy (positivo/neutral/negativo)
    TONOS_V2_NEUTRAL_O_POS = {"celebratorio", "personal", "propositivo", "informativo", "solidario"}
    TONOS_V2_CRITICO = {"critico", "ataque"}
    TONOS_LEGACY_NEUTRAL_O_POS = {"positivo", "neutral"}
    TONOS_LEGACY_NEG = {"negativo"}

    vocab_counts = {"v2": 0, "legacy": 0, "otro": 0}

    for r in rows:
        pid, pub, content, tono, target, pol, mv, plat = r
        critic_hits = find_keywords(content, PALABRAS_CRITICAS)
        positive_hits = find_keywords(content, PALABRAS_POSITIVAS)
        precedent_hits = find_keywords(content, TEMAS_PRECEDENTE)

        # Tag vocabulario
        if tono in TONOS_V2_NEUTRAL_O_POS or tono in TONOS_V2_CRITICO:
            vocab = "v2"
        elif tono in TONOS_LEGACY_NEUTRAL_O_POS or tono in TONOS_LEGACY_NEG:
            vocab = "legacy"
        else:
            vocab = "otro"
        vocab_counts[vocab] += 1

        # Caso 1: palabras críticas pero clasificado como tono neutro/positivo
        tono_es_neutral_o_pos = (
            tono in TONOS_V2_NEUTRAL_O_POS
            or tono in TONOS_LEGACY_NEUTRAL_O_POS
        )
        if critic_hits and tono_es_neutral_o_pos:
            sospechosos_tono_critico_en_post_celebratorio.append({
                "id": pid, "tono": tono, "pol": pol, "platform": plat,
                "hits": critic_hits, "content": (content or "")[:200],
                "fecha": pub.strftime("%Y-%m-%d") if pub else "—",
                "mv": mv or "legacy",
                "vocab": vocab,
            })

        # Caso 2: palabras positivas pero clasificado critico/ataque/negativo
        tono_es_critico = tono in TONOS_V2_CRITICO or tono in TONOS_LEGACY_NEG
        if positive_hits and tono_es_critico:
            sospechosos_palabras_positivas_en_critico.append({
                "id": pid, "tono": tono, "pol": pol, "platform": plat,
                "hits": positive_hits, "content": (content or "")[:200],
                "fecha": pub.strftime("%Y-%m-%d") if pub else "—",
                "mv": mv or "legacy",
                "vocab": vocab,
            })

        # Caso 3: casos precedente con polaridad NEGATIVA fuerte
        # Considera tanto polaridad numérica como tono crítico/negativo si polaridad es null
        es_negativo = (pol is not None and pol < 0) or tono in TONOS_V2_CRITICO or tono in TONOS_LEGACY_NEG
        if precedent_hits and es_negativo:
            casos_precedente.append({
                "id": pid, "tono": tono, "pol": pol, "platform": plat,
                "hits": precedent_hits, "content": (content or "")[:200],
                "fecha": pub.strftime("%Y-%m-%d") if pub else "—",
                "mv": mv or "legacy",
                "vocab": vocab,
            })

    total_sospechosos = (len(sospechosos_tono_critico_en_post_celebratorio)
                        + len(sospechosos_palabras_positivas_en_critico)
                        + len(casos_precedente))
    tasa = round(100 * total_sospechosos / total, 1)
    output.parent.mkdir(parents=True, exist_ok=True)

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    with output.open("w") as f:
        f.write(f"# F3b · NLP Suspicious Posts · dirigente_id={args.dirigente_id}\n\n")
        f.write(f"**Fecha:** {fecha}\n")
        f.write(f"**Total posts clasificados:** {total}\n")
        f.write(f"**Vocabulario:** v2={vocab_counts['v2']} · legacy={vocab_counts['legacy']} · otro={vocab_counts['otro']}\n")
        f.write(f"**Sospechosos detectados:** {total_sospechosos} ({tasa}%)\n\n")
        if vocab_counts["legacy"] > 0 and vocab_counts["v2"] == 0:
            f.write("⚠️ **TODOS los posts usan vocabulario LEGACY** (positivo/neutral/negativo). "
                    "Matriz polaridad v2 (celebratorio/critico/etc) no se aplicó a este dirigente. "
                    "Considerar sprint dedicado de backfill matriz v2.\n\n")
        elif vocab_counts["legacy"] > 0 and vocab_counts["v2"] > 0:
            f.write(f"⚠️ **Vocabularios mezclados** detectados. {vocab_counts['legacy']} posts "
                    f"en legacy, {vocab_counts['v2']} en v2. Backfill incompleto.\n\n")

        f.write("## Veredicto\n\n")
        if tasa <= 10:
            f.write(f"✅ **PASS** — tasa {tasa}% ≤ 10% threshold. NLP framework está dentro "
                    "de lo aceptable. Revisar manualmente los casos abajo para confirmar.\n\n")
        else:
            f.write(f"⚠️ **ATENCIÓN** — tasa {tasa}% > 10% threshold. Reportar al CEO. "
                    "Considerar sprint dedicado de revisión NLP antes de F4.\n\n")

        f.write("## Caso 1: Palabras críticas en post clasificado como neutro/positivo\n\n")
        if not sospechosos_tono_critico_en_post_celebratorio:
            f.write(f"Ninguno detectado.\n\n")
        else:
            f.write(f"**{len(sospechosos_tono_critico_en_post_celebratorio)} casos.** "
                    f"Posts con palabras como 'muerto/violencia/accidente/denuncia' "
                    f"pero clasificados con tono neutro o positivo.\n\n")
            f.write("| post_id | fecha | platform | tono | pol | palabras críticas | contenido (preview) |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for s in sospechosos_tono_critico_en_post_celebratorio[:50]:
                content_short = s["content"].replace("|", "\\|").replace("\n", " ")[:140]
                f.write(f"| {s['id']} | {s['fecha']} | {s['platform']} | {s['tono']} | "
                        f"{s['pol']} | {', '.join(s['hits'])} | {content_short} |\n")
            f.write("\n")

        f.write("## Caso 2: Palabras positivas en post clasificado como crítico/ataque\n\n")
        if not sospechosos_palabras_positivas_en_critico:
            f.write("Ninguno detectado.\n\n")
        else:
            f.write(f"**{len(sospechosos_palabras_positivas_en_critico)} casos.** "
                    f"Posts con palabras como 'gracias/celebro/logro/orgullo' "
                    f"pero clasificados como crítico/ataque con polaridad negativa.\n\n")
            f.write("| post_id | fecha | platform | tono | pol | palabras positivas | contenido (preview) |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for s in sospechosos_palabras_positivas_en_critico[:50]:
                content_short = s["content"].replace("|", "\\|").replace("\n", " ")[:140]
                f.write(f"| {s['id']} | {s['fecha']} | {s['platform']} | {s['tono']} | "
                        f"{s['pol']} | {', '.join(s['hits'])} | {content_short} |\n")
            f.write("\n")

        f.write("## Caso 3: Casos precedente notebook (Alebrijes/Día del Niño/Campeones)\n\n")
        if not casos_precedente:
            f.write("Ninguno detectado. (Casos similares al precedente 2026-05-15 NO se "
                    "reproducen tras este backfill.)\n\n")
        else:
            f.write(f"**{len(casos_precedente)} casos.** Posts mencionando temas del precedente "
                    "(Alebrijes/Día del Niño/Campeones/Trofeo) pero clasificados con polaridad "
                    "NEGATIVA fuerte.\n\n")
            f.write("| post_id | fecha | platform | tono | pol | tema | contenido (preview) |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for s in casos_precedente[:50]:
                content_short = s["content"].replace("|", "\\|").replace("\n", " ")[:140]
                f.write(f"| {s['id']} | {s['fecha']} | {s['platform']} | {s['tono']} | "
                        f"{s['pol']} | {', '.join(s['hits'])} | {content_short} |\n")
            f.write("\n")

        f.write("## Notas metodológicas\n\n")
        f.write("Este audit usa heurísticas keyword-based, NO ground truth humano. "
                "Detecta candidatos a falsos positivos pero el veredicto final requiere "
                "lectura humana del contenido. Si CEO/Linda revisan los casos arriba y "
                "confirman <10% son legítimamente erróneos, el NLP framework está OK.\n\n")
        f.write("Razón de no usar Gemini cross-audit en este sprint: triangulación "
                "Layer 2 fue cerrada 2026-05-08 (D-NLP-MAPPER-C). Repetirla aquí "
                "no aporta — Gemini ya validó la matriz hace 12 días. Mejor ROI: "
                "detectar regresiones específicas con keywords del notebook.\n")

    print(f"Reporte escrito: {output}")
    print(f"Total {total} posts · Sospechosos {total_sospechosos} ({tasa}%)")


if __name__ == "__main__":
    main()
