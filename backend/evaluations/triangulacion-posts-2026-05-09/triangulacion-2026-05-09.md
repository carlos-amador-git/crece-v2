# Triangulación NLP posts · 2026-05-09

## Resumen ejecutivo

- **Total:** 60 posts procesados
- **Parseados OK por Gemma:** 14
- **Errores Gemma:** 46
- **Modelo:** `gemma3:12b`
- **Tiempo total:** 10210.5s (170.18s/post)
- **Dirigentes piloto:** [1, 2, 8]
- **Random seed:** 42

## Distribución tono Gemma

| tono | n |
|------|---|
| ERROR | 46 |
| critico | 8 |
| propositivo | 4 |
| celebratorio | 1 |
| ataque | 1 |

## Distribución target Gemma

| target | n |
|--------|---|
| ERROR | 46 |
| gobierno | 8 |
| dirigente | 3 |
| ciudadania | 1 |
| movimiento | 1 |
| diputados | 1 |

## Distribución sentimiento Gemma

| sentimiento | n |
|-------------|---|
| ERROR | 46 |
| negativo | 11 |
| positivo | 3 |

## Preview 10 posts

| id | dirigente | content_preview | tono | target | sentimiento |
|----|-----------|-----------------|------|--------|-------------|
| 4505 | Alejandro | Su sonrisa es mi motor!  En sus ojos veo el futuro que quiero defender todos los | ERROR | ERROR | ERROR |
| 741 | Alejandro | RT @PublimetroMX: #OpiniónPublimetro / Las horas que el Estado les debe a las mu | ERROR | ERROR | ERROR |
| 4499 | Alejandro | Hasta las vacas saben elegir buena compañía y nosotros también. 😎 Por eso hacemo | ERROR | ERROR | ERROR |
| 744 | Alejandro | Cuando la gente se une, las reglas cambian.  La Procuraduría Federal del Consumi | ERROR | ERROR | ERROR |
| 4487 | Alejandro | Hasta las vacas saben elegir buena compañía y nosotros también. 😎 Por eso hacemo | ERROR | ERROR | ERROR |
| 3726 | Alejandro | La política se fortalece cuando nos preparamos.  En el taller “La democracia y s | ERROR | ERROR | ERROR |
| 561 | Alejandro | La deuda histórica con las y los trabajadores está en la cancha del Congreso.  L | ERROR | ERROR | ERROR |
| 3736 | Alejandro | La confianza de nuestras vecinas y vecinos nos sigue acompañando.  Venustiano Ca | propositivo | dirigente | positivo |
| 3758 | Alejandro | El día de hoy, nuestro Coordinador Nacional Jorge Álvarez Maynez, presentó la al | ERROR | ERROR | ERROR |
| 557 | Alejandro | Morena traicionó a las y los trabajadores: mandó la jornada laboral de 40 horas  | ERROR | ERROR | ERROR |

## Archivos generados

- `sample.csv` — sample crudo
- `results_gemma.csv` — clasificación Gemma
- `posts_for_claude.md` — posts formateados para Claude
- `triangulacion-2026-05-09.md` — este reporte

## Notas de validez

- Tonos fuera de vocabulario v2: 0
- Targets fuera de vocabulario v2: 2