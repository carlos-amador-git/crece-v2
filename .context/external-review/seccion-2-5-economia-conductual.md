## §2.5 — Economía del comportamiento aplicada al receptor

La audiencia política no consume contenido como analista racional sino como ser humano con sesgos cognitivos bien documentados. Ignorar este marco es la principal causa de que las recomendaciones de los productos de analytics internacionales resulten genéricas en el mercado mexicano: optimizan para métricas de plataforma sin entender cómo el cerebro del votante procesa la información política. CRECE v2 integra cinco marcos teóricos como fundamento de las recomendaciones del Plan IA y de la interpretación de señales en el dashboard. Esta sección los formaliza para que cualquier sesión de Claude Code que genere output hacia el cliente pueda fundamentar las sugerencias con evidencia y no con opinión.

### §2.5.1 — Kahneman y Tversky: Sistema 1 y Sistema 2, Prospect Theory

Kahneman distingue entre el Sistema 1 de procesamiento rápido, emocional y automático, y el Sistema 2 de procesamiento lento, deliberativo y costoso. El consumo de contenido político en redes sociales ocurre casi exclusivamente en Sistema 1: el usuario promedio decide en menos de dos segundos si dar like, compartir o seguir scrolleando. Las publicaciones políticas que apelan a razonamiento elaborado sin antes ganar atención emocional no son procesadas. Prospect Theory agrega que las personas reaccionan más fuerte a pérdidas potenciales que a ganancias equivalentes, con un factor de asimetría documentado entre 2 y 2.5.

En contexto político mexicano, esto explica por qué la campaña de Sheinbaum en 2024 enmarcó el segundo piso de la transformación como continuidad de beneficios ya obtenidos y no como nuevas promesas abstractas. La narrativa activa aversión a la pérdida: votar por la oposición implica perder derechos adquiridos. Gálvez intentó el encuadre opuesto, prometer ganancias nuevas, que según Prospect Theory tiene menor fuerza movilizadora a igualdad de mérito argumental.

**Aplicación en CRECE v2:** el Plan IA del Sprint S4 debe privilegiar recomendaciones de encuadre en modo pérdida sobre modo ganancia cuando el objetivo sea movilización de base. El bloque #15 Rage Click Flag detecta cuando el Sistema 1 del receptor se activa por indignación sin generar conversión real.

### §2.5.2 — Cialdini: seis principios de influencia

Cialdini documenta seis armas de influencia que operan bajo el umbral consciente: reciprocidad, compromiso y coherencia, prueba social, autoridad, simpatía, y escasez. En contenido político digital, la prueba social es la más explotable: mostrar que mucha gente como el receptor apoya una posición es más persuasivo que el argumento racional para la posición. La autoridad funciona cuando se cita una fuente institucional que el receptor respeta, lo cual convierte a INEGI, IMSS y Banco de México en anclas retóricas defensibles frente a cualquier adversario.

En política mexicana, Milei en 2023 operó intensivamente el principio de autoridad citando estadísticas económicas como blindaje argumental, y la reciprocidad mediante respuesta personal a seguidores en los primeros noventa minutos post publicación. Bukele consolidó su culto digital con repetición disciplinada de tres o cuatro frases bandera durante meses, explotando el principio de compromiso y coherencia: una vez que el seguidor valida públicamente una postura del líder, la refuerza cada vez que la repite.

**Aplicación en CRECE v2:** el bloque #09 Share-to-Like Ratio mide movilización profunda porque compartir activa compromiso y coherencia (el seguidor asume costo reputacional en su red privada). El bloque #10 Start/Stop/Continue debe incorporar recomendaciones específicas de activación de prueba social ("destaca testimonios de votantes ordinarios en los primeros tres comentarios") y autoridad ("responde al primer crítico serio con cifra de fuente oficial INEGI o IMSS").

### §2.5.3 — Haidt: Moral Foundations Theory

Haidt documenta seis fundamentos morales que activan respuestas emocionales automáticas: cuidado versus daño, equidad versus injusticia, lealtad versus traición, autoridad versus subversión, pureza versus degradación, y libertad versus opresión. Los progresistas responden principalmente a cuidado y equidad; los conservadores responden a los seis con distribución más equilibrada. Un mensaje político que activa tres fundamentos morales simultáneamente supera sistemáticamente a uno que activa solo uno.

En contexto mexicano, el 4T activa cuidado (programas sociales), equidad (desigualdad histórica) y lealtad (identidad popular). La oposición tradicional activa principalmente autoridad (instituciones) y pureza (anticorrupción). Máynez con Movimiento Ciudadano intentó activar libertad y equidad simultáneamente, dirigido al votante joven que no se siente representado por los dos bloques históricos. La moral outrage, la indignación moral visible en comments con lenguaje de pureza y traición, es predictor fuerte de viralización pero no de persuasión: genera engagement sin cambiar posiciones.

**Aplicación en CRECE v2:** el bloque #05 Sentiment Plutchik debe extenderse para detectar clustering de lenguaje moralizado en comments siguiendo el léxico de Haidt. El bloque #15 Rage Click Flag captura específicamente la moral outrage como señal de engagement tóxico. El Plan IA debe recomendar construcción de mensajes que activen dos o tres fundamentos morales compatibles con la base del dirigente, no apelaciones genéricas de un solo fundamento.

### §2.5.4 — Bail 2018: Exposición a opiniones opuestas aumenta polarización

Bail y colegas publicaron en PNAS en 2018 un experimento con 1,239 usuarios de Twitter donde republicanos expuestos sistemáticamente a un bot liberal se volvieron más conservadores, y demócratas expuestos a un bot conservador se volvieron levemente más liberales. El hallazgo contradice la intuición tecno-optimista de que exponer a la gente a opiniones distintas reduce polarización. La realidad es el backfire effect: la exposición activa defensa identitaria y refuerza la postura previa.

En política mexicana, esto tiene consecuencia operativa crítica: atacar frontalmente a un rival en redes consolida su base, no la erosiona. El rival óptimo es el que se ignora o el que se rodea con contenido que reencuadra el debate, no el que se confronta directamente. Gálvez en 2024 invirtió recursos sustanciales en réplica directa a Sheinbaum, lo cual según Bail consolida a la base de Sheinbaum en lugar de erosionarla, mientras agota a la propia.

**Aplicación en CRECE v2:** el Plan IA del Sprint S4 debe incluir regla explícita de no recomendar confrontación frontal con adversario de mayor audiencia, porque amplifica. El bloque #11 Cross-Partisan Validation Score mide endorsement genuino fuera de la base como indicador de expansión real. El bloque #12 CIB Detector ITESO diferencia ataque coordinado artificial de crítica orgánica para ajustar la respuesta estratégica.

### §2.5.5 — Tajfel: Social Identity Theory

Tajfel y Turner establecen que el comportamiento político es tribalismo antes que cálculo racional de políticas públicas. Todo mensaje político activa un "nosotros versus ellos" aunque no lo intente explícitamente, y el receptor procesa la información filtrando primero por pertenencia identitaria: si el emisor pertenece al endogrupo, el mensaje es validado antes de ser evaluado; si pertenece al exogrupo, es descartado antes de ser evaluado.

En México, la polarización 4T versus oposición opera como identidad social antes que como preferencia programática. Un votante morenista y un votante panista pueden coincidir en ochenta por ciento de posiciones concretas pero votar en bloques opuestos porque su identidad tribal está activada. La densidad de pronombres "nosotros" y "ellos" en comments, el uso de emojis de bandera tribal (banderas nacionales versus puños morados), y la intimidad parasocial (llamar al líder "mi Claudia" o "Samuelito") son señales conductuales detectables que predicen resistencia a escándalos y capacidad de movilización offline.

**Aplicación en CRECE v2:** el pipeline NLP Layer 2 debe incluir detector de densidad de pronombres identitarios endogrupo versus exogrupo en comments. El bloque #11 Cross-Partisan Validation detecta cuando un post recibe validación de cuentas clasificadas en el exogrupo ideológico, señal rara y valiosa. La intimidad parasocial detectada en comments se convierte en señal de cohesión de base que debe preservarse y no sobreexplotarse con contenido institucional frío.

### §2.5.6 — Tabla de mapeo: principio conductual a bloque del inventario

| Principio conductual | Bloque(s) del inventario CRECE v2 | Cómo se aplica |
|---|---|---|
| Kahneman Sistema 1 vs Sistema 2 | #10 Start/Stop/Continue · #15 Rage Click Flag | Plan IA privilegia hooks emocionales en primeros 3 segundos. Rage Flag detecta Sistema 1 tóxico |
| Prospect Theory aversión a la pérdida | #10 Start/Stop/Continue · #16 Rastreador Promesas | Recomendaciones en modo pérdida. Promesas se enmarcan como "evitar perder" |
| Cialdini prueba social | #09 Share-to-Like Ratio · #11 Cross-Partisan Validation | Shares demuestran validación pública. Cross-partisan amplifica prueba social |
| Cialdini autoridad | #10 Start/Stop/Continue | Plan IA sugiere respuesta a críticos con fuente INEGI/IMSS/Banco de México |
| Cialdini reciprocidad | #22 Gap de Respuesta (Tier 3) | Respuesta en menos de 60 min genera lealtad desproporcionada |
| Cialdini compromiso y coherencia | #09 Share-to-Like Ratio · #29 Message Stickiness | Share activa compromiso. Stickiness mide arraigo de slogan en terceros |
| Haidt Moral Foundations | #05 Sentiment Plutchik (extendido) · #15 Rage Click Flag | Detecta clustering moral en comments. Rage Flag captura moral outrage |
| Bail backfire effect | Regla Plan IA + #11 Cross-Partisan · #12 CIB Detector | No recomendar confrontación frontal. Distinguir ataque coordinado de crítica orgánica |
| Tajfel Social Identity | NLP Layer 2 extendido · #11 Cross-Partisan Validation | Densidad de pronombres nosotros/ellos. Endorsement cruzado como señal de expansión |

### §2.5.7 — Regla transversal para el Plan IA

Toda recomendación generada por el Plan IA del Sprint S4 debe poder justificarse con al menos un principio conductual de los cinco marcos anteriores. Las recomendaciones genéricas tipo "mejora tu narrativa" o "conecta con tu audiencia" quedan explícitamente prohibidas. El formato de recomendación aceptable sigue la plantilla: acción específica, ventana temporal, criterio de éxito medible, principio conductual que aprovecha, y evidencia empírica de respaldo (post modelo del propio dirigente o de un caso comparable documentado).

**Ejemplo de recomendación aceptable:** "Responde al primer crítico serio del post del martes con cifra exacta de INEGI sobre ocupación en el sector. Ventana: primeras 2 horas post ataque. Éxito: ratio replies/likes del hilo baja de 0.8 a menos de 0.4 en 24 horas. Principio: Cialdini autoridad ancla el debate en evidencia institucional. Evidencia: tu respuesta del 15 de marzo al ataque de @adversario obtuvo esta misma caída de ratio."

**Ejemplo de recomendación rechazable:** "Mejora tu comunicación con la base electoral activando más emociones positivas." Sin acción específica, sin ventana, sin criterio medible, sin principio explícito, sin evidencia. Este tipo de output no puede escapar del Plan IA hacia el cliente.
