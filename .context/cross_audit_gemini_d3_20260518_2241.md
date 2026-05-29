# Cross-audit NLP · Dirigente 3 · 20260518_2241

**Sample size pedido:** 50 · **Seed:** 42

## Metrics

- Total muestreados: **50**
- Gemini parse OK: **50** · parse fail: 0
- Acuerdo tono: **56.0%** (28/50)
- Acuerdo target: **64.0%** (32/50)
- Acuerdo polaridad signo: **58.0%** (29/50)
- Acuerdo total (tono+target): **46.0%** (23/50)

## Threshold de aceptacion

- `agreement_full >= 85%` -> matriz v2 valida sin cambios
- `agreement_polaridad >= 90%` -> sin bias sistematico de signo
- Por debajo de cualquiera -> revisar matriz o re-entrenar

## Discrepancias

| id | content (60c) | CC tono/target/pol | Gemini tono/target/pol |
|---|---|---|---|
| 4313 | Amiga querida, sabes la admiración, respeto y cariño que te  | celebratorio/dirigente/+1 | personal/dirigente/+0 |
| 4287 | Se parece a Franky Moustro !!! | personal/dirigente/+0 | personal/otro/+0 |
| 3774 | Jugaron en el desierto? | personal/dirigente/+0 | informativo/tema_especifico/+0 |
| 2070 | Hace el mejor trabajo turístico en la costa y Oaxaca muchas  | personal/dirigente/+0 | celebratorio/dirigente/+1 |
| 3678 | Mujer de territorio ❤️ | personal/dirigente/+0 | celebratorio/dirigente/+1 |
| 4496 | Oaxaca, tierra del buen sazón.  🥰🥰 | celebratorio/tema_especifico/+1 | personal/otro/+0 |
| 2073 | el #TTM 2026 es el escenario donde Oaxaca demuestra por qué  | personal/dirigente/+0 | celebratorio/tema_especifico/+1 |
| 4486 | Muchas felicidades presidenta del DIF. Estatal, que sea un d | celebratorio/tema_especifico/+1 | personal/dirigente/+0 |
| 3758 | Julio mes de la Guelaguetza.  Debemos disfrutar estas incomp | personal/dirigente/+0 | celebratorio/tema_especifico/+1 |
| 3723 | Estuvo bien bueno el partido. Muy bien equipo 👏  en horabuen | personal/dirigente/+0 | celebratorio/tema_especifico/+1 |
| 3719 | Ojala yvel gobierno voltee a el equipo de expansión. Y le de | solidario/gobierno/+0 | propositivo/gobierno/+1 |
| 4300 | Muchas gracias x las feliciaciones para mi querida president | personal/otro/+0 | personal/dirigente/+0 |
| 3803 | Oiga Lic ... Así aspira a hacer Gobernadora hay que procurar | propositivo/dirigente/+1 | critico/dirigente/-1 |
| 3740 | Animo amigo en esta irreparable pérdida. | solidario/dirigente/+1 | solidario/otro/+1 |
| 3762 | Oaxaca y su Guelaguetza | personal/dirigente/+0 | celebratorio/tema_especifico/+1 |
| 3800 | Bueno le tocó salir de su burbuja y se dan cuenta que ni un  | personal/dirigente/+0 | critico/dirigente/-1 |
| 3746 | Trabajando en unidad se logran más oportunidades para nuestr | personal/dirigente/+0 | celebratorio/gobierno/+1 |
| 3724 | Mejor hubieran jugado en arrazola xoxo llega más gente a ver | personal/ciudadania/+0 | critico/tema_especifico/-1 |
| 541 | Con el gran olor a aguas negras y drenaje | personal/dirigente/+0 | critico/gobierno/-1 |
| 3589 | Oaxaca tiene siempre algo que compartir | personal/dirigente/+0 | celebratorio/tema_especifico/+1 |
| 527 | Por un turismo más consiente y guías también. 👏🏼  -agradecem | personal/dirigente/+0 | propositivo/autopromocion/+1 |
| 3685 | No cabe duda que la Mtra. Saymi. Es mujer de territorio. | personal/dirigente/+0 | celebratorio/dirigente/+1 |
| 4460 | Este tipo de acciones llevan tanta alegría a nuestros niños  | celebratorio/tema_especifico/+1 | celebratorio/dirigente/+1 |
| 521 | Un gobierno de territorio 👏🏽 | personal/gobierno/+0 | celebratorio/gobierno/+1 |
| 4303 | Espacio de diálogo y encuentro con las ideas | informativo/tema_especifico/+0 | celebratorio/tema_especifico/+1 |
| 3738 | Amigo Carlos David, fortaleza en estos momentos para ti y tu | personal/dirigente/+0 | solidario/otro/+1 |
| 4489 | El bienestar de las infancias y adolescencias sello distinti | celebratorio/dirigente/+1 | celebratorio/gobierno/+1 |