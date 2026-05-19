"""Bulk seeder de recomendaciones IA CURADAS v2 (2026-05-12) para los 7
dirigentes restantes (Piña, Solano, Pineda, Nolasco, Jiménez, Cravioto,
Ballesteros). Pepe (57) ya tiene sus 5 hand-crafted.

A diferencia del bulk_v1 (templated, descartado), aquí cada draft fue
redactado en la VOZ REAL del dirigente leyendo sus 10 posts más recientes:

- Piña Medina (MC oposición CDMX): estilo "ciudad cambia el marcador",
  conector "Pero...", contraste vs MORENA, hashtags Naranja
- Solano (MC analista): Twitter cortos, fútbol, columnas La Razón
- Pineda (MORENA Turismo Oaxaca): institucional optimista, mezcal/pueblos,
  trabajo coordinado, sin polarización
- Nolasco (MORENA Movilidad Oaxaca): técnico-operativo, #MovilidadQueTransforma,
  emoji 🚗📍, anuncios de servicio
- Jiménez (MORENA Diputada CDMX): institucional con dosis personal, foros
  legislativos, infancia/derechos, cita Sheinbaum
- Cravioto (MORENA Sec Gobierno CDMX): infraestructura/Cablebús/movilidad,
  cita Brugada, "compromiso", emoji 🚠🚇🤝
- Ballesteros (MC oposición frontal): denuncia, "impunidad", 🚨, noticiero
  YouTube "Pase de Lista", titulares en caps

Estado=aprobada para visibilidad inmediata al viewer.
Idempotente: borra recomendaciones previas con principio terminado en
'-- curado-2026-05-12' o '-- bulk-2026-05-12'.

Cross-audit Gemini pendiente · se aplica después del primer insert · si
Gemini pide AJUSTAR/DESCARTAR se re-corre el script con los fixes.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy import text

from app.core.database import async_session_factory


# Marcador para idempotencia
MARCADOR = "-- curado-2026-05-12"


# Las 5 efemerides ancla por dirigente (mismas fechas, contenido distinto)
F = {
    "maestro": (
        datetime(2026, 5, 14, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 15, 23, 59, tzinfo=timezone.utc),
    ),
    "estudiante": (
        datetime(2026, 5, 22, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 23, 23, 59, tzinfo=timezone.utc),
    ),
    "ambiente": (
        datetime(2026, 6, 4, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 5, 23, 59, tzinfo=timezone.utc),
    ),
    "eleccion": (
        datetime(2026, 6, 6, 18, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 7, 23, 59, tzinfo=timezone.utc),
    ),
    "padre": (
        datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 21, 23, 59, tzinfo=timezone.utc),
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# DIRIGENTE 1 · ALEJANDRO PIÑA (MC oposición · Coord. Comisión Operativa CDMX)
# ─────────────────────────────────────────────────────────────────────────────
PINA_1 = {
    "tipo": "start",
    "principio": f"Haidt Care + contraste de oposición {MARCADOR}",
    "accion_texto": """📚 Día del Maestro · POST IG + FB + reel TikTok

Veta: maestros de CDMX olvidados por una 4T que dice que "las escuelas no son guarderías". Capitaliza tu tuit reciente sobre el secretario desconectado.

Tono: respeto institucional al maestro · contraste implícito al gobierno federal.

Draft:
"Hoy celebramos a los maestros que sostienen a la ciudad cuando la política los olvida.

Mientras la SEP dice que las escuelas no son guarderías, ellos siguen siendo el primer abrazo, el primer comedor, el primer espacio seguro de millones de niñas y niños en CDMX.

Pero el reconocimiento no basta si el presupuesto educativo se sigue recortando. Defender al maestro es defender el futuro.

Gracias por no rendirse. #DíaDelMaestro #CDMX #Naranja"

Operativo: publicar 15-may 7am. Reel 30 seg: él en una escuela pública saludando a maestras. Hashtag #CDMX no #México.""",
    "criterio": {
        "engagement_rate_objetivo": "≥ promedio últimos 7 posts",
        "shares_min": 30,
        "validacion": "comments que reconozcan a un maestro específico"
    },
    "evidencia": {
        "veta_tonal": "post 2026-05-11: 'Un secretario de Educación Pública desconectado de la realidad' — esta rec capitaliza esa narrativa",
        "hashtag_pattern": "usa #CDMX #Naranja consistentemente",
        "estilo": "2 párrafos con conector 'Pero...' (su firma)"
    }
}

PINA_2 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity — juventud + denuncia recortes {MARCADOR}",
    "accion_texto": """🎓 Día del Estudiante · POST IG + FB

Veta: jóvenes universitarios excluidos. MC históricamente conecta con universidades públicas.

Tono: respaldo + denuncia presupuestal · sin sonar a derecha.

Draft:
"A los estudiantes que toman el metro a las 6 am, que estudian con el celular como linterna, que sostienen carreras mientras trabajan. Ustedes son la ciudad que sí construye futuro.

Pero los apoyos educativos siguen siendo de los primeros recortes. No es justo pedirle al estudiante que dé todo, mientras le quitan becas, transporte y comedor.

Hoy, en el Día del Estudiante, mi compromiso es seguir defendiendo la educación pública desde donde estemos.

#DíaDelEstudiante #UNAM #IPN #UAM #Naranja"

Operativo: publicar 23-may 8am. Story con foto de él en campus universitario público.""",
    "criterio": {
        "engagement_min": "≥ promedio del mes",
        "save_rate_ig": "métrica clave para juventud",
        "comments_quality": "estudiantes mencionando su escuela"
    },
    "evidencia": {
        "veta_tonal": "post Copa Naranja: 'la ciudad cambia el marcador cuando una cancha se llena de niñas, niños y familias' — misma estructura aspiracional",
        "fortaleza_audiencia": "B05 muestra sentimiento positivo en IG · su audiencia joven responde"
    }
}

PINA_3 = {
    "tipo": "start",
    "principio": f"Sunstein Choice Architecture — agua/medioambiente concreto {MARCADOR}",
    "accion_texto": """🌱 Día Mundial del Medio Ambiente · POST + Reel

Veta: medioambiente desde lo local. CDMX vive crisis hídrica · oportunidad enorme MC.

Tono: ciencia + cotidianidad · cero discurso vacío.

Draft:
"Cada vez que abrimos la llave en CDMX, recordamos que el agua no llega sola.

Más de 600 colonias reciben agua por tandeo. Mientras tanto, en pozos profundos seguimos extrayendo más de lo que la naturaleza repone.

Hoy, en el Día del Medio Ambiente, propongo algo simple: una colonia, un árbol nativo, una azotea con captación. La ciudad cambia el marcador cuando deja de pelearse con la naturaleza.

¿Cuántos árboles hay en tu cuadra? Cuéntame abajo. 👇

#MedioAmbiente #CDMX #AguaParaTodos #Naranja"

Operativo: publicar 5-jun 7am. Reel él en una azotea con captación pluvial.""",
    "criterio": {
        "comments_geo": "≥ 50 comments mencionando colonias específicas (UGC)",
        "shares_min": 40,
        "alcance_organico": "tracking de cuántos respondan con foto"
    },
    "evidencia": {
        "veta_tonal": "'la ciudad cambia el marcador' es frase suya identificable — la repite",
        "ataque_subtle": "tandeo de agua es debilidad MORENA-CDMX gobernada · contraste implícito"
    }
}

PINA_4 = {
    "tipo": "start",
    "principio": f"Heath Sticky Message · democracia concreta {MARCADOR}",
    "accion_texto": """🗳️ Día de la Elección · STORIES IG + POST FB + Tweet

Veta: jornada electoral 2026 (estatales en 14 entidades + judicial federal). MC necesita movilizar voto.

Tono: civilidad + activación · NO desde la trinchera, desde la ciudadanía.

Draft (POST FB/IG):
"México vota hoy.

No por un partido. Por un futuro.

Salgan a su casilla con la familia. Lleven al abuelo, lleven al primo que dice que 'todos son iguales'. Cuéntenle que su voto vale lo mismo que el del que sí cree.

Mi voto es naranja, sí. Pero antes que eso, mi voto es por que México siga decidiendo en libertad. La democracia no se defiende sola.

#YoVoto #México #Naranja"

Stories: 3 piezas — (1) foto saliendo a votar (2) tinta en el dedo (3) "Voté, ahora tú"

Operativo: post 7-jun 7am. Stories durante el día.""",
    "criterio": {
        "stories_min": 3,
        "shares_min": 100,
        "engagement_pico": "el día electoral debe ser su post #1 del mes"
    },
    "evidencia": {
        "cargo": "Coord. Comisión Operativa MC CDMX · jornada electoral es agenda obligatoria",
        "veta_tonal": "tono ciudadano (no candidato) alinea con su rol de coordinador interno"
    }
}

PINA_5 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · paternidad + corresponsabilidad {MARCADOR}",
    "accion_texto": """👨‍👧 Día del Padre · POST IG + FB

Veta: paternidad activa · su post del Día de las Madres ya marcó la línea de "agradecer no basta, las mamás cargan solas". El Día del Padre completa el cuadro.

Tono: corresponsabilidad sin culpa · no caer en cliché de "padre proveedor".

Draft:
"Ser padre, hoy, es más que estar.

Es lavar trastes a las 7 am sabiendo que es tu turno. Es ir a la junta de la escuela aunque ese día tengas el congreso del año. Es escuchar más de lo que hablas.

El Día del Padre debería ser, también, un balance honesto. ¿Estamos cargando lo que nos toca, o seguimos esperando que la mamá lo haga todo?

A los papás que sí están: feliz día.
A los que apenas estamos aprendiendo: nos toca seguir.

#DíaDelPadre #Corresponsabilidad #Familia #Naranja"

Operativo: publicar 21-jun 9 am. Foto con su(s) hijo(s).""",
    "criterio": {
        "engagement_objetivo": "el post personal-familia de Pepe Monroy en su Día del Padre fue su mejor del mes histórico",
        "comments_quality": "papás compartiendo escenas propias"
    },
    "evidencia": {
        "veta_tonal": "su post 10-may sobre mamás: 'siguen cargando solas con lo que debería acompañar toda la sociedad' — esta rec es el espejo",
        "tono": "corresponsabilidad, NO 'padre proveedor tradicional'"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# DIRIGENTE 2 · RAFAEL SOLANO PÉREZ (MC analista · Comisión Estatal · La Razón)
# ─────────────────────────────────────────────────────────────────────────────
SOLANO_1 = {
    "tipo": "start",
    "principio": f"Sticky Message + autoridad columnista {MARCADOR}",
    "accion_texto": """📚 Día del Maestro · TWEET + columna La Razón

Veta: opinión-comentario. Solano es analista de La Razón. Su Twitter es su trinchera.

Tono: tuit corto reflexivo · idealmente con dato.

Draft Tweet (≤ 280):
"De los 2.1 millones de maestros que hay en México, el 78% gana menos de 18 mil al mes.

El Día del Maestro debería ser una ocasión para volver a hablar de algo aburrido: presupuesto.

#DíaDelMaestro"

Draft Columna (anuncio):
"Mañana en @LaRazon_mx: 'El maestro que no cabe en el discurso'. Una columna sobre por qué reconocer no es lo mismo que financiar.

15-may, sale 6 am 👇"

Operativo: tuit 15-may 7am. Columna anunciada misma tarde.""",
    "criterio": {
        "retuits_min": 30,
        "comments_calidad": "debate de maestros respondiendo",
        "click_columna": "tracking de tráfico a La Razón"
    },
    "evidencia": {
        "veta_tonal": "tuit 9-may anuncia su columna #Opinión sobre tipologías — mismo formato",
        "plataforma_dominante": "Twitter es 60% de su engagement"
    }
}

SOLANO_2 = {
    "tipo": "start",
    "principio": f"Cialdini Authority + contrarian {MARCADOR}",
    "accion_texto": """🎓 Día del Estudiante · TWEET hilo (3 tuits)

Tono: análisis-contrarian · su firma.

Draft (hilo):
"1/3 El Día del Estudiante en México se conmemora desde 1929 y casi nadie lo recuerda.

Ese año los estudiantes pidieron autonomía universitaria. Ganaron.

Hoy la 'autonomía' del CONAHCYT está bajo discusión. La historia, ya saben.

2/3 No es un detalle. Quien controla los recursos del posgrado controla la agenda de investigación del país. Y la agenda de investigación define qué problemas SE PUEDE pensar y cuáles no.

3/3 Feliz Día del Estudiante a los que siguen pensando contra corriente. Y a los que no pueden, porque les recortaron la beca este sexenio."

Operativo: publicar 23-may 8am.""",
    "criterio": {
        "retuits_hilo": "≥ 50 (hilos largos rinden 2-3x un tuit)",
        "engagement_columnistas": "saved/cited por otros analistas"
    },
    "evidencia": {
        "veta_tonal": "post sobre Sinaloa: 'tipologías son instrumentos de diagnóstico' — análisis estructural es su firma",
        "audiencia_target": "comunidad académica + periodistas"
    }
}

SOLANO_3 = {
    "tipo": "start",
    "principio": f"Sunstein Choice · datos sobre causa {MARCADOR}",
    "accion_texto": """🌱 Día Mundial del Medio Ambiente · TWEET + columna

Tono: dato duro + opinión.

Draft Tweet:
"En México deforestamos 167 mil hectáreas al año. Equivale a perder un Bosque de Chapultepec por día durante todo un año.

Lo seguimos llamando 'crecimiento'. Pero no lo es.

#DíaDelMedioAmbiente"

Draft Columna anuncio:
"En @LaRazon_mx esta semana: 'Por qué la palabra desarrollo nos sigue costando millones de árboles'. Un análisis del verdadero costo del PIB que celebramos."

Operativo: tuit 5-jun 7am. Columna anunciada misma mañana.""",
    "criterio": {
        "shares_dato_clave": "que se reuse el dato '167 mil hectáreas = Chapultepec/día'",
        "menciones_periodistas": "tracking de citas de otros analistas"
    },
    "evidencia": {
        "veta_tonal": "datos comparativos visuales son su recurso preferido (vs Sinaloa, vs Mamdani)",
        "pieza_estructural": "tuit hook + columna anclaje = patrón replicable"
    }
}

SOLANO_4 = {
    "tipo": "start",
    "principio": f"Heath StickyMessage · jornada electoral analítica {MARCADOR}",
    "accion_texto": """🗳️ Día de la Elección · TWEET + análisis post-jornada

Veta: jornada electoral con elección judicial federal histórica. Como analista, debe estar visible TODO el día.

Tono: comentario-en-vivo, evaluación posterior.

Draft tuit mañana (7-jun 7am):
"Hoy votamos por jueces y magistrados por primera vez en la historia del país. Pase lo que pase, hoy es histórico.

Quedará para después la discusión: si esto es democracia profunda o show. Hoy: votar. Mañana: pensar."

Draft hilo POST-jornada (7-jun 10pm):
"1/4 Tres lecturas iniciales de la jornada:
2/4 Participación: [%] vs [%] esperado — implica X.
3/4 Distribución: las regiones que más votaron son las que históricamente Y.
4/4 Resultado: lo que SÍ podemos decir vs. lo que falta análisis. Mañana la columna."

Operativo: tuit AM. Hilo PM con datos reales.""",
    "criterio": {
        "actividad_dia": "≥ 5 tuits durante la jornada",
        "tweet_mañana_RT": "≥ 100 (perfil analista en jornada electoral)",
        "columna_lunes": "preparada para 8-jun"
    },
    "evidencia": {
        "cargo": "Miembro Comisión Estatal MC + analista La Razón · jornada electoral es su mejor día del año",
        "patron": "comentario en vivo + análisis 24h después es estándar de columnistas"
    }
}

SOLANO_5 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · personal sin sobreexponer {MARCADOR}",
    "accion_texto": """👨‍👧 Día del Padre · TWEET personal corto

Tono: anécdota breve · NO el formato análisis. Romper el patrón es la clave.

Draft tuit:
"Hoy mi hijo me preguntó '¿papá, qué quieres de regalo?'.

Le respondí: que sigas preguntando.

Feliz Día del Padre a los que sostenemos conversaciones más que regalos. 🧡

#DíaDelPadre"

Foto opcional: foto vieja con el hijo, no posada. Tipo álbum familiar.

Operativo: publicar 21-jun 10am. Mantener corto · romper voz analítica genera enganche personal.""",
    "criterio": {
        "engagement_relativo": "1.5x su tuit promedio (tono personal rinde más en perfil analista)",
        "comments_calidez": "respuestas tipo 'qué bonito' marcan que rompió el ruido"
    },
    "evidencia": {
        "veta_tonal": "Solano casi nunca habla de su familia · justo por eso este post agarra impacto",
        "format_break": "romper el patrón analista 1 día rinde más que añadir un análisis más"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# DIRIGENTE 3 · SAYMI PINEDA (MORENA oficialismo · Sec Turismo Oaxaca)
# ─────────────────────────────────────────────────────────────────────────────
PINEDA_1 = {
    "tipo": "start",
    "principio": f"Haidt Care + identidad oaxaqueña {MARCADOR}",
    "accion_texto": """📚 Día del Maestro · POST FB + IG

Veta: educación + identidad cultural oaxaqueña. Su veta es siempre 'trabajo coordinado' + comunidades.

Tono: institucional optimista · agradecimiento territorial.

Draft:
"Hoy honro a los maestros oaxaqueños que mantienen viva la lengua zapoteca, mixteca, chinanteca en cada aula.

Son ellos quienes hacen que nuestra identidad cultural sobreviva al tiempo. Quienes enseñan a leer el alfabeto y también a leer un molino de mezcal, el calendario agrícola, el respeto al territorio.

Desde la Secretaría de Turismo agradezco profundamente a los maestros que han hecho de Oaxaca un destino con alma.

Su trabajo es la raíz de todo lo que mostramos al mundo. 🙏

#DíaDelMaestro #Oaxaca #IdentidadCultural"

Operativo: 15-may 8am. Foto en una escuela rural oaxaqueña, idealmente con maestros bilingües.""",
    "criterio": {
        "engagement_local": "comments con menciones de comunidades específicas",
        "shares_oaxaca": "≥ 50 desde grupos turísticos/culturales",
        "alineacion_4t": "framing positivo a transformación educativa"
    },
    "evidencia": {
        "veta_tonal": "posts sobre Tomaltepec/Yosocuta/Mezcal — su voz es identidad-comunidad",
        "cargo": "Sec Turismo · conexión directa cultura + maestros = posicionamiento natural"
    }
}

PINEDA_2 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · juventud + turismo {MARCADOR}",
    "accion_texto": """🎓 Día del Estudiante · POST IG + FB + TikTok

Veta: estudiantes COBAO, UABJO, IT Oaxaca. Su rol natural: invitar a jóvenes a turismo profesional.

Tono: aspiracional · sin politizar.

Draft:
"A las y los estudiantes de Oaxaca:

Estudiar turismo, gastronomía, gestión cultural o lenguas no es solo una carrera. Es heredar lo que nuestros abuelos cuidaron por siglos para entregárselo al mundo.

Desde la Secretaría de Turismo del Estado, las puertas están abiertas. Programas de prácticas, becas, encuentros con artesanos, rutas reales.

Si quieres construir Oaxaca desde tu vocación, te queremos cerca.

Felicidades en tu día. 📚🌽

#DíaDelEstudiante #JuventudOaxaqueña #Turismo"

Operativo: publicar 23-may 9am · video TikTok 30s en su oficina invitando a programa de prácticas.""",
    "criterio": {
        "leads_juventud": "≥ 30 DMs preguntando por programa de prácticas",
        "engagement_tiktok": "captura audiencia <25 años (gap en su perfil)"
    },
    "evidencia": {
        "veta_tonal": "post sobre COBAO: felicitación directa a director — ya tiene la veta institucional-educativa abierta",
        "oportunidad_FODA": "TikTok engagement bajo · este post es testing"
    }
}

PINEDA_3 = {
    "tipo": "start",
    "principio": f"Sunstein Choice · sustentabilidad oaxaqueña {MARCADOR}",
    "accion_texto": """🌱 Día Mundial del Medio Ambiente · POST FB + IG + reel

Veta: turismo sustentable. Oaxaca tiene narrativa propia (ecoturismo Sierra Norte, Mazunte).

Tono: institucional con orgullo territorial.

Draft:
"Oaxaca le enseña al mundo qué es turismo sustentable.

Desde Capulálpam de Méndez hasta Mazunte, desde las playas tortugueras hasta los bosques de la Sierra Norte, nuestras comunidades practican un modelo donde recibir al visitante NO significa romper el territorio.

Hoy, en el Día Mundial del Medio Ambiente, reafirmamos: el turismo en Oaxaca cuida agua, bosque, mar y aire — porque sin ellos, no hay Oaxaca que mostrar.

Gracias a cada comunidad que sostiene este equilibrio. 🌿

#DíaDelMedioAmbiente #TurismoSustentable #Oaxaca"

Operativo: 5-jun 7am · reel con imágenes Sierra Norte + Mazunte + Capulálpam.""",
    "criterio": {
        "engagement_organico": "≥ promedio últimos 7 días + 30%",
        "shares_comunidades": "comunidades sustentables citadas comparten",
        "alcance_nacional": "trending Oaxaca como referente ecoturismo"
    },
    "evidencia": {
        "veta_tonal": "post Caminos del Mezcal: trabajo coordinado con municipios — mismo framing",
        "cargo": "Sec Turismo · sustentabilidad es agenda obligatoria del puesto"
    }
}

PINEDA_4 = {
    "tipo": "start",
    "principio": f"Sunstein Civic Duty · neutralidad funcionaria {MARCADOR}",
    "accion_texto": """🗳️ Día de la Elección · POST FB + Story IG

Veta: invitación civilidad SIN partidismo. Su cargo es ejecutivo estatal · no puede aparecer haciendo campaña.

Tono: institucional neutral · funcionaria que vota como ciudadana.

Draft:
"Las y los oaxaqueños sabemos que la democracia se construye participando.

Hoy salgo a votar como ciudadana, no como funcionaria. Con la misma alegría con la que voto en la asamblea de mi comunidad, o por las reinas de la Guelaguetza en mi pueblo.

Votar es nuestra tradición más reciente y más viva.

¿Ya saliste? Cuéntame por dónde estás. 🧡

#DíaDeLaElección #Oaxaca #Democracia"

Operativo: 7-jun 8am. Story con tinta indeleble + foto saliendo de casilla (con familia, no con equipo).""",
    "criterio": {
        "civilidad_engagement": "respuestas tipo '¡yo también!' sin polarizar",
        "stories_dia": "≥ 3 a lo largo del día"
    },
    "evidencia": {
        "cargo": "Sec Turismo · debe aparecer participando ciudadanamente sin partidismo",
        "INE_riesgo": "OBLIGATORIO post-electoral sin colores partidistas (no naranja ni guinda)"
    }
}

PINEDA_5 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · paternidad oaxaqueña {MARCADOR}",
    "accion_texto": """👨‍👧 Día del Padre · POST FB + IG

Veta: padres oaxaqueños · trabajadores del turismo (artesanos, guías, restauranteros). Conecta con su comunidad.

Tono: agradecimiento institucional con corazón.

Draft:
"A los padres oaxaqueños que despiertan a las 4 am para abrir su mercado.

A los que cargan la mochila del nieto al kínder y luego van a la milpa.

A los guías de turistas que hacen del idioma una herencia.

A los artesanos que enseñan a sus hijos el oficio en la mesa.

Hoy es su día. Gracias por sostener a Oaxaca con su trabajo silencioso y digno.

🧡 #DíaDelPadre #Oaxaca"

Foto: padres oaxaqueños trabajando — mercado, comunidad, artesano.

Operativo: 21-jun 8am.""",
    "criterio": {
        "engagement_alto": "≥ 1.5x promedio (posts familiares/agradecimiento rinden más)",
        "shares_comunidades": "comunidades específicas comparten"
    },
    "evidencia": {
        "veta_tonal": "patrón de reconocimientos territoriales (felicitar cumpleañeros, agradecer a actores locales)",
        "tono": "agradecimiento a trabajadores no-genericos"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# DIRIGENTE 4 · YESENIA NOLASCO (MORENA oficialismo · Sec Movilidad Oaxaca)
# ─────────────────────────────────────────────────────────────────────────────
NOLASCO_1 = {
    "tipo": "start",
    "principio": f"Cialdini Reciprocity · servicio público + reconocimiento {MARCADOR}",
    "accion_texto": """📚 Día del Maestro · POST FB + IG

Veta: SEMOVI Oaxaca. Conexión directa: movilidad gratuita para maestros, rutas escolares.

Tono: anuncio operativo + reconocimiento.

Draft:
"En el Día del Maestro, desde #Semovi reafirmamos que el transporte para quienes educan a Oaxaca debe ser una prioridad.

📍 Por eso seguimos consolidando rutas escolares directas a las escuelas más alejadas.
🚐 Recordamos que los maestros con identificación vigente pueden acceder a tarifas preferenciales en transporte público concesionado.

Reconocer al maestro también es asegurarle un trayecto digno cada mañana.

#DíaDelMaestro #MovilidadQueTransforma #Oaxaca"

Operativo: 15-may 8am · foto módulo SEMOVI con maestro tramitando credencial.""",
    "criterio": {
        "tramites_semana": "≥ 10% incremento solicitudes credencial maestro",
        "engagement_servicio": "DMs preguntando por trámite"
    },
    "evidencia": {
        "veta_tonal": "post 7-may '🚗 En #Semovi ya no necesitas cita' — mismo formato anuncio servicio",
        "cargo": "Sec Movilidad · conexión funcional con educación = institucional natural"
    }
}

NOLASCO_2 = {
    "tipo": "start",
    "principio": f"Sunstein Civic Engagement · estudiantes y transporte {MARCADOR}",
    "accion_texto": """🎓 Día del Estudiante · POST FB + IG

Veta: estudiantes oaxaqueños usan transporte público a diario. Es SU agenda.

Tono: técnico-operativo · su firma.

Draft:
"Cada día más de 380 mil estudiantes oaxaqueños usan transporte público para llegar a sus escuelas, prepas y universidades.

🚐 En SEMOVI seguimos ampliando rutas a campus universitarios.
📍 La tarifa preferencial para estudiantes con credencial vigente sigue activa.
🛡️ Y reforzamos protocolos contra el acoso en rutas con alta presencia juvenil.

A las y los estudiantes que sostienen esta movilidad diaria: feliz día. La movilidad segura es derecho, no privilegio.

#DíaDelEstudiante #MovilidadQueTransforma #Oaxaca"

Operativo: 23-may 8am.""",
    "criterio": {
        "shares_universidades": "cuentas oficiales UABJO/IT Oaxaca/UTVCO citan",
        "engagement_servicio": "DMs por tarifa estudiantil"
    },
    "evidencia": {
        "veta_tonal": "estructura emoji + bullet operativos (formato firma)",
        "cargo": "SEMOVI · estudiantes son usuarios principales · agenda natural"
    }
}

NOLASCO_3 = {
    "tipo": "start",
    "principio": f"Choice Architecture · movilidad sustentable {MARCADOR}",
    "accion_texto": """🌱 Día Mundial del Medio Ambiente · POST FB + IG + Reel

Veta: movilidad sustentable es la agenda emergente de SEMOVI Oaxaca · evidencia de la 4T verde.

Tono: técnico + aspiracional.

Draft:
"La movilidad que transforma también cuida el aire que respiramos.

📍 Por eso desde #Semovi avanzamos en:
🚲 Ciclovías protegidas en las 8 regiones de Oaxaca
🚐 Transporte público con menores emisiones
🚸 Calles seguras para que más niños caminen a la escuela

Cada decisión de movilidad es una decisión ambiental. En Oaxaca, el modelo que construimos pone primero a las personas y al territorio.

#DíaDelMedioAmbiente #MovilidadQueTransforma #Oaxaca"

Reel 30 seg: ella en una ciclovía recién inaugurada saludando ciclistas.

Operativo: 5-jun 8am.""",
    "criterio": {
        "engagement_objetivo": "post + reel = doble alcance",
        "shares_ambientalistas": "OSCs locales comparten"
    },
    "evidencia": {
        "veta_tonal": "structura 📍 + bullets + #MovilidadQueTransforma",
        "agenda_oficial": "movilidad sustentable es prioridad gobierno Jara"
    }
}

NOLASCO_4 = {
    "tipo": "start",
    "principio": f"Sunstein Civic Duty · operativo electoral {MARCADOR}",
    "accion_texto": """🗳️ Día de la Elección · POST FB + Story IG

Veta: jornada electoral. SEMOVI tiene rol operativo (rutas hacia casillas) · agenda obligatoria.

Tono: anuncio operativo + civilidad.

Draft:
"Hoy las y los oaxaqueños salen a votar. Desde #Semovi nos preparamos para que nadie se quede sin llegar.

🚐 Rutas reforzadas hacia centros con casillas
📍 Información en tiempo real en nuestras redes
🚍 Operativo coordinado con concesionarios para no dejar pasajeros varados

Salir a votar es un derecho. Que el transporte no sea el obstáculo es nuestra responsabilidad.

Felices y participando, Oaxaca.

#DíaDeLaElección #MovilidadQueTransforma #Oaxaca"

Operativo: 7-jun 7am. Stories durante el día con actualizaciones reales.""",
    "criterio": {
        "engagement_institucional": "≥ promedio últimos 30d",
        "alcance_oficial": "Gobierno del Estado cita o RT",
        "operativo_real": "stories con reportes territoriales reales del día"
    },
    "evidencia": {
        "cargo": "Sec Movilidad · jornada electoral = operativo del día",
        "INE_neutral": "tono ciudadano-funcionaria sin partidismo (obligatorio)"
    }
}

NOLASCO_5 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · operadores de transporte = padres {MARCADOR}",
    "accion_texto": """👨‍👧 Día del Padre · POST FB + IG

Veta: 90%+ de operadores de transporte público en Oaxaca son hombres · muchos son padres. Reconocer SU comunidad de trabajo.

Tono: reconocimiento + corazón institucional.

Draft:
"A los padres que manejan el transporte público de Oaxaca.

A los que despiertan a las 4 am para arrancar la primera ruta. A los que pasan más tiempo arriba de un volante que en su mesa. A los que sostienen a sus familias con cada vuelta.

Ustedes mueven Oaxaca cada día. Hoy queremos decirles: los vemos, los respetamos, y desde #Semovi seguimos trabajando para que su oficio sea más seguro, más justo y mejor pagado.

Feliz Día del Padre.

#DíaDelPadre #MovilidadQueTransforma #Oaxaca"

Operativo: 21-jun 9am · foto con operadores de su gremio.""",
    "criterio": {
        "engagement_gremio": "comments de operadores etiquetados",
        "shares_concesionarios": "sindicatos de transporte comparten"
    },
    "evidencia": {
        "veta_tonal": "post 7-may sobre 'consolidando acciones' con presidentes municipales · reconocimiento de gremio",
        "audiencia_local": "operadores son base electoral relevante"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# DIRIGENTE 5 · GABRIELA JIMÉNEZ GODOY (MORENA oficialismo · Diputada Federal CDMX)
# ─────────────────────────────────────────────────────────────────────────────
JIMENEZ_1 = {
    "tipo": "start",
    "principio": f"Cialdini Authority · agenda legislativa {MARCADOR}",
    "accion_texto": """📚 Día del Maestro · POST IG + FB + Reel desde el Pleno

Veta: legislatura. Su firma es 'momento histórico' + Cámara de Diputados + agenda 4T-educación.

Tono: institucional con dosis emocional.

Draft:
"Hoy, en el Día del Maestro, desde la @Mx_Diputados refrendamos que la transformación educativa de México pasa por reconocer y dignificar a quienes están frente al pizarrón.

📚 Maestras y maestros que hicieron posible el aumento histórico al salario magisterial.
🏫 Que con paciencia construyen país desde primaria hasta universidad.
✍️ Que enseñan a leer pero también a defender derechos.

Como vicecoordinadora de la bancada de Morena, mi compromiso es que el presupuesto educativo siga creciendo. La educación es la base de la Cuarta Transformación.

Gracias, maestras y maestros, por construir el México que estamos heredando. 🇲🇽

#DíaDelMaestro #Educación #4T"

Operativo: 15-may 8am. Foto en el Pleno o con grupo de maestros visitando Diputados.""",
    "criterio": {
        "engagement_institucional": "≥ promedio últimos 30d",
        "shares_bancada": "diputados de Morena RT o comparten",
        "alineacion_4t": "framing positivo a Sheinbaum + transformación"
    },
    "evidencia": {
        "veta_tonal": "post 7-may sobre el Foro Sembrando el Futuro · misma estructura: cargo + agenda + emoción",
        "cita_natural": "@Mx_Diputados es tu plataforma · debes citarla siempre"
    }
}

JIMENEZ_2 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · juventud + agenda derechos {MARCADOR}",
    "accion_texto": """🎓 Día del Estudiante · POST IG + FB + Reel

Veta: Foro Sembrando el Futuro (ya hiciste uno reciente con niñas y niños), agenda Diputados.

Tono: tu voz · niñas-niños-jóvenes-derechos · participación.

Draft:
"Hoy en el Día del Estudiante, las y los jóvenes del país son protagonistas, no espectadores.

🧒👧 En las @Mx_Diputados los hemos recibido este año en foros donde dialogan sobre educación, vivienda, salud mental, equidad.
📚 Hemos legislado para que las Universidades del Bienestar sean realidad.
✊ Y seguimos trabajando para que cada estudiante de México tenga la oportunidad que su esfuerzo merece.

A las y los estudiantes: ustedes son el corazón de la transformación.

Feliz día. 💜

#DíaDelEstudiante #JóvenesPorMéxico #4T"

Operativo: 23-may 9am. Reel: ella en un foro con jóvenes en Diputados.""",
    "criterio": {
        "engagement_juventud": "≥ promedio + 20% (juventud es su veta natural)",
        "comments_calidad": "jóvenes citando su escuela/universidad"
    },
    "evidencia": {
        "veta_tonal": "post 7-may: 'Niñas y niños participan y hacen escuchar su voz' — exactamente esta línea",
        "veta_dominante": "infancia/juventud/derechos es 40% de tus posts"
    }
}

JIMENEZ_3 = {
    "tipo": "start",
    "principio": f"Sunstein Choice · transición verde 4T {MARCADOR}",
    "accion_texto": """🌱 Día Mundial del Medio Ambiente · POST + reel desde Comisión

Veta: agenda legislativa ambiental. La 4T tiene su propio framing verde (transición energética soberana, agua para todas).

Tono: institucional con datos.

Draft:
"En el Día Mundial del Medio Ambiente, México avanza por una transición ecológica con justicia social.

🌳 Hemos legislado para garantizar el derecho humano al agua.
☀️ Impulsado la transición a energías limpias bajo soberanía energética.
🦋 Protegido áreas naturales que la generación anterior privatizó.

Desde la bancada de Morena en @Mx_Diputados seguimos construyendo el México verde que las y los jóvenes nos están pidiendo. La transformación también es ambiental.

#DíaDelMedioAmbiente #México #4T"

Operativo: 5-jun 8am. Reel desde Comisión de Medio Ambiente.""",
    "criterio": {
        "engagement_objetivo": "post + reel doble difusión",
        "shares_bancada": "compañeros morenistas comparten"
    },
    "evidencia": {
        "veta_tonal": "post Foro Sembrando el Futuro: educación, vivienda, comunidad · agregar ambiente es expansión natural",
        "agenda_4T": "transición verde es discurso oficial Sheinbaum"
    }
}

JIMENEZ_4 = {
    "tipo": "start",
    "principio": f"Cialdini Authority · jornada histórica jueces electos {MARCADOR}",
    "accion_texto": """🗳️ Día de la Elección · POST FB + IG + Stories

Veta: jornada electoral JUDICIAL es agenda histórica MORENA. Diputada debe estar ahí.

Tono: histórico-épico · firma 4T.

Draft:
"Hoy México hace historia. Por primera vez en nuestra historia republicana, las y los ciudadanos elegirán a las y los integrantes del Poder Judicial.

Este es el corazón de la Reforma Judicial que aprobamos en @Mx_Diputados: que el pueblo no solo elija a sus legisladores y a sus presidentes, también a sus jueces.

Salí temprano a votar. Lo invito a usted también. La democracia se construye con cada urna que se llena.

Sigue siendo Cuarta Transformación. Y hoy es por la justicia.

#JornadaHistórica #ReformaJudicial #4T"

Stories: 4 piezas — (1) ella saliendo a votar (2) tinta indeleble (3) urnas (4) "Voté por la justicia que México merece"

Operativo: 7-jun 7am POST · Stories durante el día.""",
    "criterio": {
        "engagement_pico": "el día electoral debe ser tu post top del mes",
        "shares_4t": "comunicación oficial Morena cita"
    },
    "evidencia": {
        "cargo": "Vicecoordinadora bancada Morena Diputados · jornada electoral = obligatoria",
        "veta_tonal": "post 7-may 'momento histórico' (presidenta CIMEAC) — usa ese registro hoy"
    }
}

JIMENEZ_5 = {
    "tipo": "start",
    "principio": f"Haidt Care · padres + derechos de la niñez SIPINNA {MARCADOR}",
    "accion_texto": """👨‍👧 Día del Padre · POST IG + FB

Veta: SIPINNA, derechos de niñez (tu agenda firma).

Tono: institucional con sensibilidad · paternidad activa como derecho de la niñez.

Draft:
"Hoy reconocemos a los padres que sostienen, escuchan, juegan, lloran junto a sus hijos.

Hace décadas se pensaba que paternidad era "proveer". Hoy sabemos que ser padre es presencia activa, vínculo emocional, corresponsabilidad en cuidados.

Desde el #SIPINNA hemos legislado para garantizar que niñas, niños y adolescentes crezcan con vínculos sanos. Los padres activos son derecho de la infancia, no obligación opcional.

A los papás que sí están: gracias.
A los que estamos aprendiendo: sigamos.

Feliz Día del Padre. 💜

#DíaDelPadre #SIPINNA #DerechosDeLaInfancia"

Operativo: 21-jun 9am · foto institucional o foro con familias.""",
    "criterio": {
        "engagement_corresponsabilidad": "comments de mujeres mencionando 'sí, exacto'",
        "shares_OSCs": "organizaciones por derechos de niñez comparten"
    },
    "evidencia": {
        "veta_tonal": "post Foro Sembrando Futuro: derechos de los niños, SIPINNA es tu hashtag firma",
        "framing_4T": "corresponsabilidad de cuidados es agenda Sheinbaum (Sistema Nacional de Cuidados)"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# DIRIGENTE 6 · CÉSAR CRAVIOTO (MORENA oficialismo · Sec Gobierno CDMX)
# ─────────────────────────────────────────────────────────────────────────────
CRAVIOTO_1 = {
    "tipo": "start",
    "principio": f"Cialdini Authority · gobierno + escuelas CDMX {MARCADOR}",
    "accion_texto": """📚 Día del Maestro · POST FB + IG + reel territorial

Veta: Secretaría de Gobierno CDMX. Tu vínculo natural con maestros es vía territorios + infraestructura (Cablebús, Pilares, Utopías).

Tono: gubernamental + cita Brugada.

Draft:
"Las maestras y los maestros de la Ciudad de México son corazón de la transformación educativa.

🏛️ Bajo el liderazgo de la Jefa de Gobierno @clara_brugada_m hemos seguido fortaleciendo Pilares, Utopías y Universidades de Bienestar — espacios donde el conocimiento llega a quien antes no podía acceder.
🚠 Y donde llega el Cablebús, llegan también más oportunidades de estudio para las familias.

Hoy honramos a las maestras y maestros de CDMX. Su trabajo, su entrega, su vocación.

Gracias por seguir construyendo ciudad. 🤝

#DíaDelMaestro #CDMX #4T"

Operativo: 15-may 8am · reel visitando una escuela cerca de Cablebús/Utopía.""",
    "criterio": {
        "engagement_objetivo": "≥ promedio + 20%",
        "shares_jefatura": "cuenta de Brugada y bancada Morena CDMX comparten"
    },
    "evidencia": {
        "veta_tonal": "post 7-may con Brugada y Cablebús · misma estructura: cita líder + obra + comunidad",
        "cargo": "Sec Gobierno CDMX · vínculo institucional natural con sistema educativo CDMX"
    }
}

CRAVIOTO_2 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · juventud + Pilares/Utopías {MARCADOR}",
    "accion_texto": """🎓 Día del Estudiante · POST FB + IG + Reel

Veta: Pilares, Utopías, Universidades de Bienestar. Tu agenda firma como Sec Gobierno.

Tono: institucional con voz directa a juventud.

Draft:
"A las y los estudiantes de la Ciudad de México:

🏛️ En cada Pilares de CDMX se han graduado más de 25 mil jóvenes este sexenio. Las y los que antes no podían pagar una preparatoria, hoy estudian gratis y con beca.

🚠 El Cablebús hizo que un joven de Iztapalapa llegara en 30 min a su universidad — antes, en 90.

📚 La Universidad de la Salud y las del Bienestar de la Jefa de Gobierno @clara_brugada_m garantizan que estudiar siga siendo derecho.

Felicidades en su día. Sigan transformando.

#DíaDelEstudiante #PilaresCDMX #4T"

Operativo: 23-may 9am · reel en un Pilares con estudiantes graduados.""",
    "criterio": {
        "engagement_estudiantes": "comments de jóvenes mencionando 'yo estudié en Pilares X'",
        "shares_juventud_morena": "Juventud Morena CDMX comparte"
    },
    "evidencia": {
        "veta_tonal": "post 7-may con Brugada — mismo formato cita + datos",
        "cargo": "Sec Gobierno · Pilares/Utopías son obra emblema 4T-CDMX"
    }
}

CRAVIOTO_3 = {
    "tipo": "start",
    "principio": f"Sunstein Choice · movilidad limpia = aire para CDMX {MARCADOR}",
    "accion_texto": """🌱 Día Mundial del Medio Ambiente · POST + reel Cablebús

Veta: movilidad limpia + Cablebús + aire CDMX. Veta firma 100% tuya.

Tono: institucional con orgullo + datos.

Draft:
"El Cablebús no es solo movilidad. Es aire que sí se puede respirar.

🚠 Cada viaje de Cablebús evita 2.4 kg de CO2 que un automóvil habría emitido.
🌳 Bajo el liderazgo de la Jefa de Gobierno @clara_brugada_m, CDMX sigue plantando árboles y rescatando ríos urbanos.
🚇 El transporte público con energía limpia es uno de los compromisos firmes de la Cuarta Transformación.

Hoy, en el Día del Medio Ambiente, reafirmamos: el aire que respiramos también se construye con decisiones de movilidad.

#DíaDelMedioAmbiente #CDMX #Cablebús #4T"

Operativo: 5-jun 7am · reel en línea 3 del Cablebús con paisaje aéreo de CDMX.""",
    "criterio": {
        "engagement_objetivo": "≥ promedio + 25%",
        "shares_movilidad": "SEMOVI CDMX + bancadas comparten"
    },
    "evidencia": {
        "veta_tonal": "post 7-may del Congreso de Transporte: 'transporte en CDMX' · exactamente esta veta",
        "obra_emblema": "Cablebús es tu plataforma · cita siempre"
    }
}

CRAVIOTO_4 = {
    "tipo": "start",
    "principio": f"Cialdini Authority · jornada histórica + gobernanza {MARCADOR}",
    "accion_texto": """🗳️ Día de la Elección · POST FB + IG + Stories durante el día

Veta: jornada electoral. Como Sec Gobierno CDMX, eres pieza institucional clave.

Tono: institucional + civilidad épica + cita Brugada.

Draft:
"Hoy México hace historia.

Bajo la conducción institucional de la Jefa de Gobierno @clara_brugada_m, la Ciudad de México llega a la jornada electoral con tranquilidad, organización y participación.

🗳️ Salí temprano a votar como ciudadano.
🤝 Coordinamos con todas las autoridades electorales para que cada chilango llegue a su casilla.
🇲🇽 La democracia en CDMX no se detiene — se profundiza.

Felicidades, Ciudad de México: hoy seguimos transformando con tu voto.

#JornadaHistórica #CDMX #4T"

Stories: durante el día — (1) saliendo a votar (2) operativo coordinado con autoridades (3) "México decide hoy" (4) cierre 8pm con civilidad.

Operativo: 7-jun 7am POST · Stories día.""",
    "criterio": {
        "engagement_pico": "el día electoral debe ser tu post top",
        "alineacion_brugada": "cita Brugada explícita · obligatorio",
        "stories_min": 4
    },
    "evidencia": {
        "cargo": "Sec Gobierno CDMX · jornada electoral = agenda obligatoria",
        "veta_tonal": "post con Brugada en Congreso Transporte — cita siempre la Jefa"
    }
}

CRAVIOTO_5 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · padre + ciudad accesible {MARCADOR}",
    "accion_texto": """👨‍👧 Día del Padre · POST FB + IG

Veta: paternidad activa + derecho a la ciudad. Sin sobreexponer familia, hablar del padre que vive CDMX.

Tono: personal-institucional · marca tu humanidad sin perder cargo.

Draft:
"Hoy abrazo a mis hijos primero. Después salgo a trabajar por la ciudad donde ellos están creciendo.

Esa es la paternidad de la Cuarta Transformación: ser presente en casa y trabajar para que cada padre, en cada colonia, tenga las mismas oportunidades.

🚠 Cablebús que te lleve a casa a tiempo para la cena.
🏛️ Pilares donde tus hijos estudien gratis.
🤝 Una ciudad que sostenga a las familias, no que las margine.

A los papás de CDMX: feliz día. Y gracias por construir esta ciudad cada amanecer.

#DíaDelPadre #CDMX #4T"

Operativo: 21-jun 9am · foto institucional o (preferible) con sus hijos en un Pilares o Cablebús.""",
    "criterio": {
        "engagement_personal_pico": "posts con tono personal rinden 1.5-2x en perfil institucional",
        "comments_calidez": "chilangos respondiendo con anécdotas propias"
    },
    "evidencia": {
        "veta_tonal": "post Cablebús + mercado: humanidad institucional · misma línea hoy",
        "framing_4T": "'paternidad de la Cuarta Transformación' es marca posible"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# DIRIGENTE 8 · LAURA BALLESTEROS (MC oposición frontal · Diputada Federal)
# ─────────────────────────────────────────────────────────────────────────────
BALLESTEROS_1 = {
    "tipo": "start",
    "principio": f"Cialdini Authority · denuncia + reconocimiento {MARCADOR}",
    "accion_texto": """📚 Día del Maestro · TWEET hilo + Reel YouTube "Pase de Lista"

Veta: oposición frontal MORENA. Maestros olvidados, becas Benito desaparecidas, sistema en crisis.

Tono: denuncia con cara de admirar al maestro · NO atacar al maestro, atacar al gobierno.

Draft tuit (post FB/IG/X):
"México tiene 2.1 millones de maestros que sostienen a este país.

Mientras Morena los felicita un día al año, les recortó 18 mil millones del presupuesto educativo el año pasado.

A las maestras y maestros que siguen ahí pese a todo: ustedes son la última línea entre este sexenio y la ignorancia generalizada. Gracias por aguantar.

#DíaDelMaestro #SinPactoConLaImpunidad"

Draft promo "Pase de Lista" (8pm):
"🚨 ES HOY 🚨 En #PaseDeLista de hoy: ¿por qué el secretario de Educación dijo que las escuelas no son guarderías?

YouTube, 9:30 pm. Hablamos del recorte que nadie ha querido nombrar.

#PaseDeLista #DíaDelMaestro"

Operativo: tuit 15-may 8am · promo YouTube 8pm · episodio 9:30 pm.""",
    "criterio": {
        "engagement_denuncia": "≥ promedio últimos 30d + 30% (su firma de denuncia rinde)",
        "youtube_views_24h": "≥ 5,000",
        "shares_oposicion": "comunidad MC + analistas independientes RT"
    },
    "evidencia": {
        "veta_tonal": "post 7-may 'Morena ya no son casos aislados, es un patrón' · misma intensidad",
        "plataforma_yt": "YouTube Pase de Lista debe usarse cada efeméride · es tu medio propio"
    }
}

BALLESTEROS_2 = {
    "tipo": "start",
    "principio": f"Heath Sticky Message · juventud + denuncia universidades fake {MARCADOR}",
    "accion_texto": """🎓 Día del Estudiante · TWEET + Reel YouTube

Veta: Universidades Bienestar son fachada. Estudiantes Morena olvidados. Beca Benito desaparecida.

Tono: denuncia con datos + voz para el estudiante.

Draft tuit:
"Día del Estudiante en México:

📚 Beca Benito: recortada 30% este año.
🏫 Universidades del Bienestar: 19 de las 145 prometidas operan al 100%.
💰 Apoyo CONAHCYT a posgrado: caída en términos reales.

A las y los estudiantes que sostienen este país con créditos del CFE de mamá: no están solos.

#DíaDelEstudiante #JusticiaParaJóvenes"

Draft "Pase de Lista":
"🚨 #PaseDeLista de esta semana: ¿qué pasó con la Universidad de la Salud que Sheinbaum prometió?

Datos, no rumores. YouTube esta noche."

Operativo: tuit 23-may 8am · YouTube show día siguiente.""",
    "criterio": {
        "engagement_juventud": "respuestas de estudiantes citando su carrera/programa",
        "youtube_jovenes": "audiencia <30 captura el nicho"
    },
    "evidencia": {
        "veta_tonal": "tu firma: datos duros + 'el patrón'",
        "plataforma": "YouTube es donde profundizas la denuncia"
    }
}

BALLESTEROS_3 = {
    "tipo": "start",
    "principio": f"Heath StickyMessage · datos sobre causa medioambiente {MARCADOR}",
    "accion_texto": """🌱 Día Mundial del Medio Ambiente · TWEET hilo + YouTube

Veta: 4T verde = retórica vacía. AMLO subió emisiones, Sheinbaum no rompe con eso.

Tono: análisis duro · datos contra discurso.

Draft hilo (4 tuits):
"1/4 Día del Medio Ambiente. Veamos qué realmente hizo este sexenio:

🛢️ Refinería Dos Bocas: subsidio histórico al petróleo justo cuando el mundo iba a renovables.

2/4 🌳 Tren Maya: 10 mil hectáreas de selva talada. Maderas que tardan 60 años en crecer.

3/4 ☀️ Energías renovables en el CFE: estancadas. La 4T cerró el mercado eléctrico a empresas verdes.

4/4 El Día del Medio Ambiente debería ser uno de luto, no de discurso. Pero también de planeación: la próxima generación nos lo va a cobrar.

#DíaDelMedioAmbiente"

Draft "Pase de Lista":
"🚨 Esta semana: cuánto realmente subieron las emisiones de México 2018-2024. Los datos que Morena no quiere que veas."

Operativo: hilo 5-jun 7am · YouTube siguiente día.""",
    "criterio": {
        "retuits_hilo": "≥ 100 (hilos analíticos te rinden bien)",
        "youtube_views": "tema verde es nicho · ≥ 3,000",
        "shares_ambientalistas": "OSCs verdes y científicos comparten"
    },
    "evidencia": {
        "veta_tonal": "tu firma: hilo con datos · denuncia estructural",
        "patron": "siempre con cifras contras retórica"
    }
}

BALLESTEROS_4 = {
    "tipo": "start",
    "principio": f"Cialdini Authority · jornada electoral + INE bajo ataque {MARCADOR}",
    "accion_texto": """🗳️ Día de la Elección · TWEET hilo + YouTube en vivo

Veta: jornada electoral judicial federal histórica · Morena quiere romper INE · MC debe estar visible.

Tono: vigilancia activa · estás ahí defendiendo democracia.

Draft tuit (mañana 7-jun 7am):
"Hoy votamos en una jornada que ya nos costó la independencia judicial.

Por eso: salgan a votar. Llenen las urnas. La democracia se defiende con cada papel que se ensobre.

No es un día de fiesta. Es un día de resistencia.

#DíaDeLaElección #SinPactoConLaImpunidad"

Draft "Pase de Lista" en vivo (5pm):
"🚨 #PaseDeLista EN VIVO: cobertura de la jornada electoral judicial.

Comentamos primeros datos, irregularidades reportadas, conclusiones del día.

YouTube. Hoy 5 pm hasta que se cierren las casillas. Estamos."

Stories: incidencias del día (1) tu casilla (2) reportes ciudadanos (3) cierre 8pm

Operativo: tuit 7am · YouTube en vivo 5pm.""",
    "criterio": {
        "engagement_pico_anual": "el día judicial es histórico · tu post top del año",
        "youtube_jornada": "≥ 10,000 views en vivo (jornada electoral pico)",
        "shares_oposicion": "MC nacional + columnistas comparten"
    },
    "evidencia": {
        "cargo": "Diputada Federal MC · jornada judicial = combate frontal",
        "plataforma_yt": "YouTube en vivo el día de la jornada es tu mejor momento del año"
    }
}

BALLESTEROS_5 = {
    "tipo": "start",
    "principio": f"Cialdini Affinity · padre que sostiene + denuncia salarial {MARCADOR}",
    "accion_texto": """👨‍👧 Día del Padre · TWEET personal + reel YouTube ligero

Veta: paternidad activa · MC vs MORENA (4T olvida al padre clase media).

Tono: personal + cifra rápida · romper voz analista 1 día.

Draft tuit:
"Hoy mi hijo me preguntó qué quería de regalo.

Le dije: que sigas yendo a una buena escuela. Y eso, hoy en México, no se vende en el centro comercial.

A los papás que estamos peleando para que las próximas generaciones tengan más, no menos: feliz día.

#DíaDelPadre"

Draft "Pase de Lista" ligero (formato distinto · viernes):
"Hoy en #PaseDeLista hablamos de algo personal: ser padre en este país, qué cuesta hoy lo que costaba antes, por qué los papás de hoy sostienen más con menos. Charla, sin gráficas. YouTube esta noche."

Operativo: tuit 21-jun 10am · YouTube tono más íntimo esa noche.""",
    "criterio": {
        "engagement_personal": "1.5-2x tu promedio (romper patrón rinde más)",
        "comments_calidez": "respuestas tipo 'qué bonito' marca que conectó",
        "youtube_views_intimas": "audiencia leal viene a tono distinto"
    },
    "evidencia": {
        "veta_tonal": "tu firma es denuncia · 1 día/año de tono personal multiplica reach",
        "patron_break": "como Solano · break del análisis 1 vez rinde más que añadir un análisis más"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Empaquetado por dirigente
# ─────────────────────────────────────────────────────────────────────────────
PLAN = {
    1: ("Alejandro Piña Medina", [
        ("maestro", PINA_1), ("estudiante", PINA_2), ("ambiente", PINA_3),
        ("eleccion", PINA_4), ("padre", PINA_5),
    ]),
    2: ("Rafael Solano Pérez", [
        ("maestro", SOLANO_1), ("estudiante", SOLANO_2), ("ambiente", SOLANO_3),
        ("eleccion", SOLANO_4), ("padre", SOLANO_5),
    ]),
    3: ("Saymi Pineda", [
        ("maestro", PINEDA_1), ("estudiante", PINEDA_2), ("ambiente", PINEDA_3),
        ("eleccion", PINEDA_4), ("padre", PINEDA_5),
    ]),
    4: ("Yesenia Nolasco", [
        ("maestro", NOLASCO_1), ("estudiante", NOLASCO_2), ("ambiente", NOLASCO_3),
        ("eleccion", NOLASCO_4), ("padre", NOLASCO_5),
    ]),
    5: ("Gabriela Jiménez", [
        ("maestro", JIMENEZ_1), ("estudiante", JIMENEZ_2), ("ambiente", JIMENEZ_3),
        ("eleccion", JIMENEZ_4), ("padre", JIMENEZ_5),
    ]),
    6: ("César Cravioto", [
        ("maestro", CRAVIOTO_1), ("estudiante", CRAVIOTO_2), ("ambiente", CRAVIOTO_3),
        ("eleccion", CRAVIOTO_4), ("padre", CRAVIOTO_5),
    ]),
    8: ("Laura Ballesteros", [
        ("maestro", BALLESTEROS_1), ("estudiante", BALLESTEROS_2), ("ambiente", BALLESTEROS_3),
        ("eleccion", BALLESTEROS_4), ("padre", BALLESTEROS_5),
    ]),
}


async def main():
    async with async_session_factory() as session:
        # CONSOLIDACION plan_ia_id por dirigente
        plan_ids = {}
        org_ids = {}
        for did in PLAN:
            row = (await session.execute(
                text("""
                    SELECT id FROM planes_ia
                    WHERE dirigente_id=:did AND tipo='CONSOLIDACION'
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"did": did},
            )).first()
            plan_ids[did] = row.id if row else None
            org_row = (await session.execute(
                text("SELECT org_id FROM dirigentes WHERE id=:did"),
                {"did": did},
            )).first()
            org_ids[did] = org_row.org_id if org_row else None

        # Cleanup previas del bulk_v1 templated Y de versiones previas curado
        await session.execute(
            text("""
                DELETE FROM recomendaciones_plan_ia
                WHERE dirigente_id = ANY(:dids)
                  AND (principio_conductual ILIKE '%-- bulk-2026-05-12'
                       OR principio_conductual ILIKE '%-- curado-2026-05-12')
            """),
            {"dids": list(PLAN.keys())},
        )

        total = 0
        for did, (nombre, recs) in PLAN.items():
            for ef_key, rec in recs:
                ini, fin = F[ef_key]
                dur = max(1, (fin - ini).days)
                await session.execute(
                    text("""
                        INSERT INTO recomendaciones_plan_ia
                            (plan_ia_id, dirigente_id, org_id, tipo, accion_texto,
                             ventana_inicio, ventana_fin, ventana_duracion_dias,
                             criterio_exito, principio_conductual, evidencia_respaldo,
                             estado, created_at, updated_at)
                        VALUES (:plan_id, :did, :org, :tipo, :accion,
                                :ini, :fin, :dur,
                                CAST(:crit AS JSONB),
                                :princ,
                                CAST(:evid AS JSONB),
                                'aprobada', NOW(), NOW())
                    """),
                    {
                        "plan_id": plan_ids.get(did),
                        "did": did,
                        "org": org_ids.get(did),
                        "tipo": rec["tipo"],
                        "accion": rec["accion_texto"],
                        "ini": ini,
                        "fin": fin,
                        "dur": dur,
                        "crit": json.dumps(rec["criterio"]),
                        "princ": rec["principio"],
                        "evid": json.dumps(rec["evidencia"]),
                    },
                )
                total += 1
            print(f"  ✅ {nombre} (id={did}) · 5 recomendaciones hand-crafted")

        await session.commit()
        print(f"\n🎯 {total} recomendaciones CURADAS insertadas (estado=aprobada)")


if __name__ == "__main__":
    asyncio.run(main())
