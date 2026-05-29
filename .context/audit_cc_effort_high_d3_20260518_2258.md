# Audit CC effort=high · Dirigente 3 · 20260518_2258

**Sample:** 50 · **Seed:** 42 · **CC effort:** high

## Comparativo CC-high (nuevo) vs CC-stored (effort=low del backfill)

- Total muestreados: **50** · CC-high parse OK: **50** · fail: 0
- **Comments con clasificacion distinta:** 21 (42.0%)
- **Comments con polaridad signo distinta:** 17 (34.0%)
- **Criticas detectadas por CC-high pero NO por CC-low:** 5
- **Pasaron de personal -> celebratorio:** 8

## Diagnostico empirico

- Si `criticas detectadas` >= 5 -> bug era effort=low, fix = re-correr backfill con effort=high
- Si `criticas detectadas` < 3 y `cambios totales` < 30% -> bug es estructural (prompt/matriz), needs opcion b
- Si ambos altos -> ambos problemas existen, fix combinado

## Tabla completa

| id | content (60c) | CC-low stored | CC-high nuevo | cambio? |
|---|---|---|---|---|
| 4313 | Amiga querida, sabes la admiración, respeto y cariño que te  | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 4287 | Se parece a Franky Moustro !!! | personal/dirigente/+0 | personal/dirigente/+0 | — |
| 4168 | Saludos Maestra Saymi Pineda Velasco🫶 | personal/dirigente/+0 | personal/dirigente/+0 | — |
| 3774 | Jugaron en el desierto? | personal/dirigente/+0 | critico/dirigente/-1 | ✓ |
| 3926 | Maestra Saymi Pineda Velasco Estamos muy contentos por su vi | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 2070 | Hace el mejor trabajo turístico en la costa y Oaxaca muchas  | personal/dirigente/+0 | celebratorio/dirigente/+1 | ✓ |
| 4409 | Buenas derramas económicas para los Huatulqueños | celebratorio/tema_especifico/+1 | celebratorio/tema_especifico/+1 | — |
| 4398 | ¡Gracias a todas y todos los participantes! Estamos haciendo | informativo/ciudadania/+0 | informativo/ciudadania/+0 | — |
| 3678 | Mujer de territorio ❤️ | personal/dirigente/+0 | celebratorio/dirigente/+1 | ✓ |
| 4496 | Oaxaca, tierra del buen sazón.  🥰🥰 | celebratorio/tema_especifico/+1 | celebratorio/tema_especifico/+1 | — |
| 3836 | Felicidades para usted y su mami dios las bendiga | personal/dirigente/+0 | personal/dirigente/+0 | — |
| 4515 | Buen día Licenciada Saymi Pineda Velasco ,claro que si que r | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 2073 | el #TTM 2026 es el escenario donde Oaxaca demuestra por qué  | personal/dirigente/+0 | celebratorio/tema_especifico/+1 | ✓ |
| 4486 | Muchas felicidades presidenta del DIF. Estatal, que sea un d | celebratorio/tema_especifico/+1 | celebratorio/dirigente/+1 | ✓ |
| 3758 | Julio mes de la Guelaguetza.  Debemos disfrutar estas incomp | personal/dirigente/+0 | celebratorio/tema_especifico/+1 | ✓ |
| 3723 | Estuvo bien bueno el partido. Muy bien equipo 👏  en horabuen | personal/dirigente/+0 | celebratorio/tema_especifico/+1 | ✓ |
| 3719 | Ojala yvel gobierno voltee a el equipo de expansión. Y le de | solidario/gobierno/+0 | propositivo/gobierno/+1 | ✓ |
| 4548 | Saludos guapa secretaria en hora buena ! | personal/dirigente/+0 | personal/dirigente/+0 | — |
| 4393 | La Sierra Sur tiene un gran potencial y da gusto ver esfuerz | celebratorio/tema_especifico/+1 | celebratorio/tema_especifico/+1 | — |
| 4300 | Muchas gracias x las feliciaciones para mi querida president | personal/otro/+0 | personal/otro/+0 | — |
| 3803 | Oiga Lic ... Así aspira a hacer Gobernadora hay que procurar | propositivo/dirigente/+1 | critico/dirigente/-1 | ✓ |
| 3740 | Animo amigo en esta irreparable pérdida. | solidario/dirigente/+1 | solidario/dirigente/+1 | — |
| 4112 | Muy bien, maestra! Echele ganas, demuestre lo que una costeñ | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 3762 | Oaxaca y su Guelaguetza | personal/dirigente/+0 | informativo/tema_especifico/+0 | ✓ |
| 4360 | https://www.facebook.com/share/v/18QcdXgWDW/  Solicitamos ap | informativo/dirigente/+0 | propositivo/dirigente/+1 | ✓ |
| 3704 | Muchas felicidades!! ✨️ fer 🫂 | personal/dirigente/+0 | personal/dirigente/+0 | — |
| 3800 | Bueno le tocó salir de su burbuja y se dan cuenta que ni un  | personal/dirigente/+0 | critico/gobierno/-1 | ✓ |
| 4237 | Excelente noticia, el trabajo en conjunto da grandes resulta | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 3679 | Saludos Saymi Pineda Velasco | personal/dirigente/+0 | personal/dirigente/+0 | — |
| 4247 | La Presa Lázaro Cárdenas representa una gran oportunidad par | propositivo/tema_especifico/+1 | propositivo/tema_especifico/+1 | — |
| 3746 | Trabajando en unidad se logran más oportunidades para nuestr | personal/dirigente/+0 | celebratorio/tema_especifico/+1 | ✓ |
| 3922 | Qué orgullo ver a Lila Downs llevar la voz y el corazón de O | celebratorio/tema_especifico/+1 | celebratorio/tema_especifico/+1 | — |
| 3724 | Mejor hubieran jugado en arrazola xoxo llega más gente a ver | personal/ciudadania/+0 | critico/tema_especifico/-1 | ✓ |
| 541 | Con el gran olor a aguas negras y drenaje | personal/dirigente/+0 | critico/gobierno/-1 | ✓ |
| 3677 | Excelente trabajo Secretaria! | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 3589 | Oaxaca tiene siempre algo que compartir | personal/dirigente/+0 | personal/tema_especifico/+0 | ✓ |
| 4424 | Que bien Lic Saymi Pineda Velasco por impulsar la educación  | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 527 | Por un turismo más consiente y guías también. 👏🏼  -agradecem | personal/dirigente/+0 | propositivo/tema_especifico/+1 | ✓ |
| 4514 | Excelente. Gracias | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 3685 | No cabe duda que la Mtra. Saymi. Es mujer de territorio. | personal/dirigente/+0 | celebratorio/dirigente/+1 | ✓ |
| 4111 | No cabe duda que nuestro Oaxaca tiene las mayores riquezas d | celebratorio/tema_especifico/+1 | celebratorio/tema_especifico/+1 | — |
| 4460 | Este tipo de acciones llevan tanta alegría a nuestros niños  | celebratorio/tema_especifico/+1 | celebratorio/tema_especifico/+1 | — |
| 4425 | Excelente trabajo mi Lic Saymi Pineda Velasco   #AmorPorOaxa | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |
| 4451 | Oaxaca tiene todo para brillar ante México y el mundo: cultu | celebratorio/tema_especifico/+1 | celebratorio/tema_especifico/+1 | — |
| 521 | Un gobierno de territorio 👏🏽 | personal/gobierno/+0 | celebratorio/gobierno/+1 | ✓ |
| 4303 | Espacio de diálogo y encuentro con las ideas | informativo/tema_especifico/+0 | informativo/tema_especifico/+0 | — |
| 3738 | Amigo Carlos David, fortaleza en estos momentos para ti y tu | personal/dirigente/+0 | solidario/ciudadania/+1 | ✓ |
| 4330 | Excelente día secretaria | personal/dirigente/+0 | personal/dirigente/+0 | — |
| 4489 | El bienestar de las infancias y adolescencias sello distinti | celebratorio/dirigente/+1 | celebratorio/gobierno/+1 | ✓ |
| 4560 | Muy bien secretaria Saymi Pineda Velasco en hora buena salud | celebratorio/dirigente/+1 | celebratorio/dirigente/+1 | — |