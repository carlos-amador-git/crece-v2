"""Seed FODA rico (CC inline) para 7 dirigentes · 2026-05-27.

Reemplaza los DIAGNOSTICO escuetos de gemini-pro-inline con FODA rico razonado
por CC, grounded en data real (followers/ER/sentiment por red, mix de tono,
recepción de comments, identidad). estructura_json dual-shape:
  - top-level {fortalezas,oportunidades,debilidades,amenazas} = [{titulo,evidencia}]  (endpoint /foda)
  - foda.{F,O,D,A} = strings  (generate_planes_v3)
  - baseline.profiles  (contexto)

HOST + venv: cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_foda_cc_2026_05_27.py
Idempotente: DELETE WHERE modelo_ia IN (gemini-pro-inline, cc-claude-inline) + INSERT.
"""
from __future__ import annotations

import json
import os

import psycopg2

DB = os.environ.get("DATABASE_URL_RAW", "postgresql://crece:crece_dev@localhost:5438/crece")
MODEL = "cc-claude-inline-2026-05-27"

# (titulo, evidencia) por cuadrante + baseline profiles
FODAS: dict[int, dict] = {
    1: {  # Alejandro Piña Medina · MC oposición · Coord. Comisión Operativa Estatal
        "F": [
            ("Engagement sólido en redes visuales", "Instagram 4.13% y TikTok 4.52% de ER sobre ~4K seguidores cada una, muy por encima del ~0.2% promedio político; tiene una base que sí interactúa."),
            ("Discurso propositivo fuerte", "119 posts propositivos (2º tono más usado tras crítico); construye agenda, no solo reacciona, lo que diferencia a un coordinador estatal."),
            ("Cobertura multicanal balanceada", "Presencia activa en las 5 redes con volumen real (117-169 posts por red), sin depender de una sola plataforma."),
        ],
        "O": [
            ("YouTube sin explotar", "Solo 30 subs y 18 videos pero el sentiment más positivo (+0.36); espacio para columna-video y contenido largo donde la recepción ya es favorable."),
            ("Empaquetar lo propositivo como sello de marca", "El mix editorial ya inclina a propuesta; convertirlo en narrativa diferenciadora frente a una oposición percibida como solo reactiva."),
            ("Activar a la audiencia de Twitter", "3,675 followers pero ER bajo (1.25%); optimizar formato (hilos, postura) para mover a una base que sigue pero no reacciona."),
        ],
        "D": [
            ("Sentiment negativo en sus canales políticos", "TikTok -0.18 y Twitter -0.30: justo las redes de mayor reach político generan reacción adversa, hay fricción con el mensaje."),
            ("Tono crítico domina el discurso", "157 posts críticos (el #1) vs 119 propositivos; para un cargo de coordinación, el exceso de crítica puede leerse como confrontativo."),
            ("La audiencia responde a la persona, no al mensaje", "459 comentarios 'personal' superan por mucho a los propositivos (46); baja conversión de seguidores a apoyo de agenda."),
        ],
        "A": [
            ("Hostilidad en comentarios", "46 comentarios de ataque; presencia de oposición que puede escalar en momentos de tensión."),
            ("Cede el terreno de contenido largo", "YouTube casi inexistente (30 subs) deja el espacio explicativo a competidores."),
            ("Riesgo reputacional en X", "El sentiment -0.30 sostenido en Twitter puede consolidar una narrativa de oposición percibida como solo-crítica."),
        ],
    },
    2: {  # Rafael Solano Pérez · MC oposición · Comisión Estatal / Analista La Razón
        "F": [
            ("Twitter es un activo excepcional", "7,932 followers con ER de 18.39%, altísimo; su rol de analista en La Razón le da autoridad que se traduce en interacción muy por encima de lo normal."),
            ("Voz de analista creíble", "El tono neutral-informativo domina (188 neutral + 24 informativo), coherente con una marca de credibilidad y análisis más que de activismo."),
            ("Sentiment positivo en redes visuales", "Instagram +0.19 y TikTok +0.16; donde publica imagen/video la recepción es favorable."),
        ],
        "O": [
            ("Capitalizar la autoridad de X en otras redes", "El ER 18% prueba que su análisis engancha; replicar ese contenido en IG/TT (hoy con 627/159 followers) para crecer base."),
            ("TikTok de análisis corto", "ER 4.11% con poca producción (66 posts); el formato de análisis en video corto es un hueco claro de crecimiento."),
            ("Pasar de comentar a liderar agenda", "Solo 20 posts propositivos; su credibilidad de analista le permitiría encabezar temas, no solo reaccionar a ellos."),
        ],
        "D": [
            ("Dependencia total de Twitter", "Instagram (627) y TikTok (159) son audiencias marginales; si X falla, no hay red de respaldo."),
            ("Facebook inexistente", "0 followers y 2 posts: ausencia total en la red de mayor alcance masivo en México."),
            ("Discurso sin postura clara", "188 posts neutrales dominan; poca toma de posición limita la construcción de una identidad política más allá del analista."),
        ],
        "A": [
            ("Volatilidad de un solo canal", "Toda su influencia depende del algoritmo y la salud de Twitter/X."),
            ("Alcance sin comunidad", "Bajo volumen de comentarios (~70) indica reach que no genera comunidad activa."),
            ("Percepción de comentarista vs actor político", "El perfil neutral-analista puede dificultar el salto a liderazgo si busca un cargo."),
        ],
    },
    3: {  # Saymi Pineda · MORENA oficialismo · Secretaria de Turismo Oaxaca
        "F": [
            ("Audiencia masiva en Facebook", "114,000 seguidores, la base más grande del grupo; plataforma de alcance institucional consolidada."),
            ("Sentiment uniformemente positivo", "+0.56 a +0.65 en todas las redes; el contenido de turismo genera recepción favorable (1,365 comentarios celebratorios)."),
            ("TikTok de alto volumen y tracción", "1,189 posts con ER 3.32% sobre 20K followers; una máquina de contenido turístico que funciona."),
            ("Discurso institucional bien calibrado", "Celebratorio (787) + informativo (716) coherente con cargo de gobierno; proyecta gestión positiva."),
        ],
        "O": [
            ("Activar Instagram y Twitter", "Audiencias decentes (12K/8.8K) pero ER muy bajo (0.60%/0.38%); el contenido visual de turismo es ideal para IG, hay crecimiento dormido."),
            ("Convertir alcance de FB en interacción", "114K followers pero ER 0.15%; trabajar video nativo y lives para despertar a la audiencia masiva."),
            ("Liderar la narrativa turística nacional", "Sentiment +0.6 y volumen le permiten ser referente del tema más allá de Oaxaca."),
        ],
        "D": [
            ("Engagement bajo pese a audiencia enorme", "Facebook 0.15% y Twitter 0.38% de ER; el reach no se traduce en interacción, audiencia pasiva."),
            ("Poco contenido propositivo", "150 propositivos vs 787 celebratorios; mucha celebración de gestión, poca propuesta o agenda futura."),
            ("Riesgo de percepción autopromocional", "La concentración en celebración institucional puede leerse como autopromoción si no se balancea con valor ciudadano."),
        ],
        "A": [
            ("Crítica activa pese al tono positivo", "227 comentarios críticos + 27 ataques; oposición que monitorea la gestión."),
            ("Exposición por cargo público", "Como Secretaria, su contenido está sujeto a escrutinio de gasto y veda; vulnerabilidad regulatoria."),
            ("Concentración en Facebook", "Si la base masiva vive en una sola red, los cambios de algoritmo golpean su alcance principal."),
        ],
    },
    5: {  # Gabriela Jiménez Godoy · MORENA oficialismo · Diputada Federal Vicecoordinadora
        "F": [
            ("TikTok excepcional", "44,900 followers y ER 9.06%, el más alto del grupo, en 1,099 posts; es viral y consolidado, su mayor activo digital."),
            ("Audiencia grande y multicanal", "30K-94K seguidores en las 4 redes; alcance de figura nacional acorde a diputada y vicecoordinadora."),
            ("Sentiment positivo general", "+0.29 a +0.50; recepción favorable en todas las redes."),
            ("Comunidad fiel", "1,086 comentarios 'personal' + 211 celebratorios; conexión emocional fuerte con su audiencia."),
        ],
        "O": [
            ("Despertar Facebook e Instagram", "94K y 75K followers con ER bajísimo (0.11%/0.74%); audiencia enorme dormida, replicar la fórmula de TikTok en video nativo."),
            ("Escalar el modelo TikTok", "El 9% de ER prueba un formato ganador; sistematizar esa producción para el resto de redes."),
            ("Dar voz a la agenda legislativa", "Su discurso es casi todo neutral; su rol de vicecoordinadora le permite liderar temas con contenido propositivo."),
        ],
        "D": [
            ("Discurso abrumadoramente neutral", "1,195 de ~1,600 posts son neutrales; mensaje sin postura clara que desaprovecha su posición de liderazgo."),
            ("Facebook con ER casi nulo", "0.11% sobre 94K followers; la red de mayor base es la de peor desempeño."),
            ("Baja conversión a propuesta", "Solo 17 posts propositivos; mucho volumen, poca construcción de agenda."),
        ],
        "A": [
            ("Capital político personalista", "La recepción domina en 'personal' (1,086); riesgo de un capital ligado a la persona, no transferible a agenda."),
            ("Crítica y ataques presentes", "37 críticos + 21 ataques; oposición activa monitoreando."),
            ("Exposición por cargo federal", "Escrutinio alto, sujeta a veda y rendición de cuentas."),
        ],
    },
    8: {  # Laura Ballesteros · MC oposición · Diputada Federal Plurinominal
        "F": [
            ("Audiencia grande y políticamente activa", "55,966 followers en Twitter (la mayor base de X del grupo MC) y 22K-33K en otras redes; figura nacional con alcance real."),
            ("TikTok de alto engagement", "ER 5.88% sobre 22,200 followers; su contenido de video conecta fuerte."),
            ("Perfil de propuesta y debate", "52 posts propositivos y un discurso crítico estructurado; voz de oposición con agenda propia (movilidad)."),
        ],
        "O": [
            ("Canalizar el debate que genera a propuesta", "La alta interacción crítica significa que mueve la conversación; reconducirla a propuesta para liderar la agenda opositora."),
            ("YouTube sin explotar", "2,330 subs, 24 videos y ER 0.18%; espacio para contenido explicativo de su especialidad legislativa."),
            ("Profundizar el vínculo en Twitter", "55K followers con ER 2.40%; formato de hilos y postura puede convertir reach en comunidad."),
        ],
        "D": [
            ("Sentiment negativo en TODAS las redes", "De -0.22 a -0.57; su contenido genera reacción adversa consistente, el ambiente es de fricción."),
            ("Alta hostilidad en la recepción", "370 comentarios críticos + 226 ataques (el mayor volumen de ataques del grupo); blanco de oposición organizada."),
            ("Carga negativa en su propio discurso", "45 posts de ataque + 41 negativos; tono confrontativo que alimenta la polarización."),
        ],
        "A": [
            ("Hostilidad organizada", "226 ataques en comentarios; riesgo real de campañas de desprestigio coordinadas."),
            ("Narrativa adversa difícil de revertir", "El sentiment -0.35 promedio puede consolidar una percepción negativa estructural."),
            ("Su mejor red tiene el peor clima", "TikTok concentra el mayor ER (5.88%) pero el peor sentiment (-0.57); el engagement alto puede ser de rechazo, no de apoyo."),
        ],
    },
    57: {  # Pepe Monroy · PAZ · Líder Nacional de Partidos Políticos Locales
        "F": [
            ("Instagram de alto engagement", "16,569 followers y ER 5.77%; su red principal conecta muy bien, con recepción celebratoria (459 comentarios)."),
            ("Sentiment positivo", "Instagram +0.51 y Facebook +0.40; clima favorable, audiencia que apoya."),
            ("Discurso propositivo presente", "80 posts propositivos; construye agenda, coherente con su rol de líder partidista."),
        ],
        "O": [
            ("Activar Facebook", "388 posts pero ER 0.19% sobre 10,970 followers; gran volumen de contenido sin interacción, claro margen de optimización de formato."),
            ("Diversificar redes", "Solo presente en IG y FB; entrar a TikTok y Twitter para ampliar base en los canales de mayor crecimiento."),
            ("Escalar la fórmula de Instagram", "El ER 5.77% prueba contenido que funciona; replicarlo en otras plataformas."),
        ],
        "D": [
            ("Presencia limitada a dos redes", "Sin TikTok, Twitter ni YouTube; ausente de los canales de mayor alcance y audiencia joven."),
            ("Facebook desaprovechado", "388 posts con casi nula interacción (0.19%); esfuerzo de producción sin retorno."),
            ("Audiencia modesta para un rol nacional", "16K/11K followers es chico para un 'Líder Nacional'; brecha entre el cargo y el alcance digital."),
        ],
        "A": [
            ("Crítica y ataques presentes", "39 comentarios críticos + 34 ataques; oposición monitoreando pese al clima positivo."),
            ("Vulnerabilidad por concentración", "Depender de Instagram lo deja expuesto a cambios de algoritmo."),
            ("Alcance que no respalda el cargo", "El volumen de conversación digital no sostiene la dimensión nacional del puesto."),
        ],
    },
    60: {  # Felipe de Jesús Martínez Gómez · MORENA oficialismo · Síndico
        "F": [
            ("TikTok es el único motor real de tracción", "2,380 followers y ER 2.91% en 98 posts; supera por mucho a Facebook (4,714 followers pero ER 0.16% plano) y a Instagram (6 followers, irrelevante). Es donde concentrar la producción de video corto."),
            ("Sentiment positivo donde publica", "TikTok +0.08, Facebook +0.34, Instagram +0.55; pese a ser figura local, su contenido no genera rechazo neto."),
            ("Mix editorial apropiado para cargo local", "Personal (36) + celebratorio (36) + informativo (22) proyecta cercanía y gestión, lo adecuado para un Síndico."),
        ],
        "O": [
            ("Construir desde cero sin pasivos", "La audiencia chica es un lienzo limpio: posicionar una imagen disruptiva sin historial negativo que arrastrar."),
            ("Profesionalizar TikTok", "Ya hay tracción (2.91% de ER); con producción consistente puede ser el canal de despegue."),
            ("Decidir Instagram: arrancar en serio o cerrar", "6 followers es alcance nulo; o se invierte en activarlo, o se concentra el esfuerzo en TikTok y Facebook."),
        ],
        "D": [
            ("Audiencia insignificante en redes ancla", "Instagram con 6 followers y Facebook con ER 0.16% sobre 4,714; alcance digital prácticamente inexistente para construir base."),
            ("Recepción crítica mayoritaria", "56 comentarios críticos vs 37 celebratorios + 11 ataques; pese a la baja interacción, el clima inicial es adverso."),
            ("Volumen de contenido bajo", "25 posts en Facebook y 12 en Instagram; producción insuficiente para crecer audiencia."),
        ],
        "A": [
            ("Hostilidad temprana", "Los críticos superan a los celebratorios (56 vs 37) en una cuenta chica; señal de oposición local activa desde el inicio."),
            ("Riesgo de irrelevancia digital", "El alcance casi nulo lo deja fuera de la conversación pública."),
            ("Dependencia de un canal incipiente", "Todo depende de que TikTok despegue; sin red de respaldo."),
        ],
    },
}


def build_estructura(did: int, foda: dict, baseline_rows: list[dict]) -> dict:
    def items(key):
        return [{"titulo": t, "evidencia": e} for (t, e) in foda[key]]

    return {
        "version": MODEL,
        "fortalezas": items("F"),
        "oportunidades": items("O"),
        "debilidades": items("D"),
        "amenazas": items("A"),
        "foda": {
            "F": [t for (t, _e) in foda["F"]],
            "O": [t for (t, _e) in foda["O"]],
            "D": [t for (t, _e) in foda["D"]],
            "A": [t for (t, _e) in foda["A"]],
        },
        "baseline": {"profiles": baseline_rows},
    }


def main() -> None:
    conn = psycopg2.connect(DB)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role='ADMIN' LIMIT 1")
    admin_uid = cur.fetchone()[0]

    for did, foda in FODAS.items():
        cur.execute(
            """SELECT platform, followers_count, posts_count
                 FROM social_profiles WHERE dirigente_id=%s ORDER BY followers_count DESC""",
            (did,),
        )
        baseline_rows = [
            {"platform": p, "followers": f, "posts": n} for (p, f, n) in cur.fetchall()
        ]
        estructura = build_estructura(did, foda, baseline_rows)

        cur.execute(
            "DELETE FROM planes_ia WHERE tipo='DIAGNOSTICO' AND modelo_ia IN (%s,%s) AND dirigente_id=%s",
            ("gemini-pro-inline-2026-05-27", MODEL, did),
        )
        cur.execute(
            """INSERT INTO planes_ia (dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                                      generado_por_id, aprobado, estructura_json, created_at)
               VALUES (%s, 'DIAGNOSTICO', %s, %s, 'seed_foda_cc_2026_05_27.py', %s, false, %s::jsonb, NOW())""",
            (
                did,
                f"FODA estratégico (CC inline) grounded en data real 2026-05-27 · {len(foda['F'])}F/{len(foda['O'])}O/{len(foda['D'])}D/{len(foda['A'])}A",
                MODEL,
                admin_uid,
                json.dumps(estructura, ensure_ascii=False),
            ),
        )
        print(f"dir {did}: {len(foda['F'])}F {len(foda['O'])}O {len(foda['D'])}D {len(foda['A'])}A · {len(baseline_rows)} perfiles")

    conn.commit()
    cur.close()
    conn.close()
    print("OK commit")


if __name__ == "__main__":
    main()
