# CRECE v2.0 -- Guia de Usuario

**Plataforma de Inteligencia Electoral y Social**

Version: 2.0 | Ultima actualizacion: Abril 2026

---

## Tabla de contenido

1. [Acceso al Sistema](#1-acceso-al-sistema)
2. [Dashboard Principal](#2-dashboard-principal)
3. [Dirigentes](#3-dirigentes)
4. [Monitoreo Social](#4-monitoreo-social)
5. [Benchmarks](#5-benchmarks)
6. [Planes IA](#6-planes-ia)
7. [Salud Digital](#7-salud-digital-deteccion-de-bots)
8. [Ciudadanos (CRM)](#8-ciudadanos-crm)
9. [Scoring (Puntuacion de Votantes)](#9-scoring-puntuacion-de-votantes)
10. [Contenido (Content Factory)](#10-contenido-content-factory)
11. [Compliance (Blindaje Legal)](#11-compliance-blindaje-legal)
12. [Campanas (WhatsApp)](#12-campanas-whatsapp)
13. [Canvassing (Rutas de Campo)](#13-canvassing-rutas-de-campo)
14. [Participacion Ciudadana](#14-participacion-ciudadana)
15. [Configuracion](#15-configuracion)
16. [Consejos Generales](#16-consejos-generales)

---

## 1. Acceso al Sistema

### Direccion de acceso

Abra su navegador e ingrese la siguiente direccion:

    https://crece.mdconsultoria-ti.org

Si su equipo le proporciono una direccion de vista previa (Vercel preview URL), utilice esa en su lugar.

### Pantalla de inicio de sesion

Al abrir la plataforma vera una pantalla dividida en dos secciones. En la seccion izquierda se muestra la marca CRECE con el lema "Inteligencia Politica en Tiempo Real" y tres caracteristicas destacadas del sistema. En la seccion derecha se encuentra el formulario de acceso.

### Como iniciar sesion

1. En el campo **Correo electronico**, escriba la direccion de correo que le fue asignada.
2. En el campo **Contrasena**, escriba su contrasena.
3. Presione el boton naranja **Iniciar sesion**.
4. El sistema lo redirigira automaticamente al Dashboard Principal.

Si ve un mensaje de error en rojo debajo de los campos, verifique que su correo y contrasena esten escritos correctamente. Si el problema persiste, contacte al administrador del sistema.

### Tipos de acceso

La plataforma tiene tres niveles de acceso. Lo que usted puede ver y hacer depende del tipo de cuenta que le fue asignada:

| Tipo de usuario | Correo de ejemplo | Que puede hacer |
|---|---|---|
| **Administrador** | admin@consultoriamd.com | Acceso completo a todos los modulos, configuracion del sistema, gestion de usuarios |
| **Dirigente** | pina@crece.mx | Ve unicamente sus propios datos: metricas personales, planes, monitoreo de sus redes. Los filtros se aplican automaticamente |
| **Analista** | analista@crece.mx | Puede consultar datos de todos los dirigentes, crear contenido, gestionar campanas y generar planes |

### Acceso de demostracion

Debajo del formulario de inicio de sesion encontrara la seccion **Acceso Demo** con tres botones de acceso rapido. Cada boton ingresa automaticamente con un perfil de prueba para que pueda explorar la plataforma sin configurar nada.

- **Administrador** -- acceso completo con el correo admin@consultoriamd.com
- **Alejandro Pina** -- perfil de dirigente con datos reales de redes sociales
- **Rafael Solano** -- perfil de dirigente con presencia digital limitada

Contrasena de demostracion: `crece2026!`

---

## 2. Dashboard Principal

El Dashboard es la primera pantalla que vera despues de iniciar sesion. Ofrece una vista general del estado de todos los dirigentes y la actividad de la plataforma.

### Tarjetas de indicadores principales (KPIs)

En la parte superior vera cuatro tarjetas con los indicadores mas importantes:

- **Total Dirigentes** -- Numero de dirigentes registrados en la plataforma.
- **Avg IPD Score** -- Puntuacion promedio del Indice de Penetracion Digital de todos los dirigentes (escala de 0 a 10).
- **Posts (24h)** -- Total de publicaciones monitoreadas en las ultimas 24 horas.
- **Alertas Activas** -- Numero de alertas de crisis actualmente vigentes.

Cada tarjeta muestra una flecha verde hacia arriba o roja hacia abajo junto con un porcentaje, que indica si el valor subio o bajo respecto al periodo anterior.

### Filtros de periodo

Encima de las tarjetas encontrara cuatro botones para cambiar el rango de tiempo de los datos:

- **Hoy** -- Solo datos del dia actual.
- **7 dias** -- Ultima semana.
- **30 dias** -- Ultimo mes.
- **90 dias** -- Ultimo trimestre.

Seleccione el periodo que desee y los indicadores, graficas y publicaciones se actualizaran automaticamente.

### Grafica de tendencia de sentimiento

Debajo de los KPIs vera una grafica de lineas con tres trazos de colores que representan la evolucion del sentimiento en las publicaciones monitoreadas:

- Linea de sentimiento **positivo**
- Linea de sentimiento **negativo**
- Linea de sentimiento **neutral**

Esta grafica le permite identificar rapidamente si el tono general de la conversacion en redes esta mejorando o empeorando.

### Seguidores por plataforma

Una grafica de barras horizontales muestra el total de seguidores distribuidos por red social (Twitter, Instagram, Facebook, TikTok, YouTube). Cada barra tiene un color diferente segun la plataforma.

### Barra de estado del sistema

En la parte inferior del dashboard encontrara indicadores del estado tecnico:

- **Ultima sincronizacion** -- Fecha y hora del ultimo barrido de datos.
- **Workers activos** -- Numero de procesos de trabajo en ejecucion.
- **Scrapers en ejecucion** -- Estado de los recolectores de datos de redes sociales.

### Publicaciones recientes

Una lista de las publicaciones mas recientes detectadas por los scrapers, con vista previa del contenido, plataforma de origen y metricas de interaccion.

### Alertas de crisis

Cuando se detecta una situacion critica (pico de sentimiento negativo, mencion masiva adversa), aparecera un aviso destacado en la parte superior del dashboard con el detalle de la alerta. Si no hay alertas activas, esta seccion no se muestra.

---

## 3. Dirigentes

Esta seccion le permite consultar a los dirigentes politicos registrados en la plataforma.

### Lista de dirigentes

1. En la barra lateral izquierda, seleccione **Dirigentes** dentro de la seccion "Principal".
2. Vera una lista de tarjetas con todos los dirigentes registrados.
3. Cada tarjeta muestra: nombre del dirigente, partido politico y una insignia de color con su puntuacion IPD.

Los colores de la insignia IPD indican el nivel de presencia digital:

| Color | Rango IPD | Significado |
|---|---|---|
| Rojo | 0 -- 3.0 | Presencia digital debil |
| Amarillo | 3.1 -- 6.0 | Presencia digital en desarrollo |
| Verde | 6.1 -- 10.0 | Presencia digital solida |

### Buscar y filtrar

Use la barra de busqueda en la parte superior para localizar dirigentes por nombre. Los filtros de **partido** y **estado** le permiten reducir la lista.

### Ver detalle de un dirigente

1. Haga clic en la tarjeta del dirigente que desea consultar.
2. Se abrira una vista detallada con:
   - **Estadisticas de 7 dias**: publicaciones realizadas, nivel de engagement (interaccion), sentimiento general y crecimiento de seguidores.
   - **Cuentas de redes sociales**: lista de perfiles vinculados con enlaces directos.
   - **Publicaciones recientes**: las ultimas publicaciones detectadas en cada plataforma.
   - **Desglose IPD por plataforma**: puntuacion individual de cada red social que compone el indice general.

> **Nota para dirigentes**: Si usted ingreso con una cuenta de tipo Dirigente, vera directamente su propio perfil sin necesidad de buscar en la lista.

---

## 4. Monitoreo Social

El modulo de Monitoreo Social muestra todas las publicaciones recopiladas de las redes sociales de los dirigentes.

1. En la barra lateral, seleccione **Social** dentro de la seccion "Principal".
2. Vera un feed (listado cronologico) de publicaciones de todas las plataformas.

### Filtrar publicaciones

En la parte superior del feed encontrara los siguientes filtros:

- **Plataforma**: Twitter, Instagram, Facebook, TikTok, YouTube, Bluesky.
- **Sentimiento**: Positivo, Negativo o Neutral.
- **Rango de fechas**: Seleccione un periodo especifico.

### Informacion de cada publicacion

Cada publicacion en el feed muestra:

- Vista previa del texto de la publicacion.
- Icono de la plataforma de origen.
- Metricas de interaccion (likes, comentarios, compartidos).
- Insignia de sentimiento con color: verde (positivo), rojo (negativo) o gris (neutral).

### Distribucion de sentimiento

En la parte lateral o superior vera una grafica de pastel que muestra la proporcion de publicaciones positivas, negativas y neutrales en el periodo seleccionado.

---

## 5. Benchmarks

Este modulo le permite comparar el rendimiento digital de sus dirigentes contra competidores de otros partidos.

1. En la barra lateral, seleccione **Benchmarks** dentro de la seccion "Analisis".
2. Vera una tabla comparativa con los siguientes datos por cada dirigente:
   - Total de seguidores.
   - Numero de plataformas activas.
   - Puntuacion IPD.
3. Las filas estan ordenadas por ranking, de mayor a menor presencia digital.

La visualizacion le permite identificar rapidamente en que posicion se encuentran sus dirigentes respecto a la competencia.

---

## 6. Planes IA

La plataforma puede generar estrategias digitales personalizadas de 90 dias para cada dirigente utilizando inteligencia artificial.

### Como generar un plan

1. En la barra lateral, seleccione **Planes IA** dentro de la seccion "Analisis".
2. Seleccione al dirigente para el cual desea generar el plan.
3. Haga clic en el boton **Generar Plan**.
4. El sistema comenzara a procesar la solicitud. Vera un indicador de progreso.

> **Tiempo estimado**: La generacion de un plan toma aproximadamente de 5 a 8 minutos, ya que el procesamiento se realiza de forma local para proteger la confidencialidad de los datos.

### Contenido del plan generado

Un plan tipico incluye:

- **Objetivos estrategicos**: Metas concretas para los proximos 90 dias.
- **Tacticas por plataforma**: Acciones especificas para cada red social.
- **Calendario de contenido**: Programacion semanal de publicaciones recomendadas.
- **KPIs de seguimiento**: Indicadores para medir el exito del plan.

### Aprobar o rechazar un plan

Los planes generados quedan en estado de borrador hasta que un administrador los revise.

1. Abra el plan generado haciendo clic en su titulo.
2. Revise el contenido completo.
3. Seleccione **Aprobar** para que el plan pase a estado activo, o **Rechazar** si requiere ajustes.

### Historial de planes

En la parte inferior de la pantalla encontrara una lista con todos los planes generados anteriormente, incluyendo su estado (borrador, aprobado, rechazado) y la fecha de creacion.

---

## 7. Salud Digital (Deteccion de Bots)

Este modulo analiza la calidad de la audiencia e interacciones en las redes sociales de un dirigente, detectando patrones sospechosos que podrian indicar seguidores falsos o engagement artificial.

### Como ejecutar un analisis

1. En la barra lateral, seleccione **Salud Digital** dentro de la seccion "Analisis".
2. En el selector de dirigentes, elija a la persona que desea analizar. Si usted ingreso como dirigente, su perfil se selecciona automaticamente.
3. Haga clic en el boton **Analizar**.
4. Espere a que el sistema complete el analisis (puede tomar unos segundos).

### Resultados del analisis

Una vez completado, vera:

**Puntuacion general de salud (0-100)**

Se muestra un numero grande con un indicador de semaforo:

| Color | Rango | Significado |
|---|---|---|
| Verde | 70 -- 100 | Audiencia saludable, engagement organico |
| Amarillo | 40 -- 69 | Algunas senales de atencion, revisar recomendaciones |
| Rojo | 0 -- 39 | Engagement sospechoso, posible presencia de bots |

**Desglose por plataforma**

Para cada red social vinculada al dirigente vera:

- Tasa de engagement (porcentaje de interaccion respecto a seguidores).
- Total de seguidores.
- Engagement promedio por publicacion.
- Numero de publicaciones analizadas.

**Senales detectadas**

Una lista de observaciones que explican la puntuacion, por ejemplo:

- "Tasa de engagement saludable para el tamano de audiencia."
- "Porcentaje elevado de publicaciones con cero interaccion."

**Anomalias**

Si se detectaron publicaciones sospechosas, vera un contador de anomalias. Haga clic para expandir los detalles de cada publicacion marcada, incluyendo una vista previa del contenido y el tipo de anomalia detectada.

### Metodologia

El analisis considera los siguientes factores: tasa de engagement general, proporcion entre comentarios y likes, porcentaje de publicaciones sin ninguna interaccion, y la varianza en los niveles de engagement (patrones demasiado uniformes sugieren actividad artificial).

---

## 8. Ciudadanos (CRM)

El modulo de Ciudadanos funciona como un directorio de contactos con informacion relevante para la operacion politica.

1. En la barra lateral, seleccione **Ciudadanos** dentro de la seccion "Fase 2".
2. Vera una lista de ciudadanos registrados con su informacion basica.

### Buscar y filtrar

- **Busqueda por nombre**: Escriba el nombre del ciudadano en la barra de busqueda.
- **Seccion electoral**: Filtre por numero de seccion electoral.
- **Estado de promotor**: Filtre para ver unicamente ciudadanos marcados como promotores.

### Informacion de cada ciudadano

Al seleccionar un ciudadano vera:

- **Datos demograficos**: Nombre, edad, genero, seccion electoral.
- **Intencion de voto**: Si fue registrada, aparece la preferencia declarada.
- **Historial de interacciones**: Registro cronologico de contactos previos (visitas domiciliarias, llamadas, eventos).

### Marcar como promotor

Si un ciudadano muestra disposicion para apoyar activamente, puede marcarlo como promotor. Esta clasificacion aparecera en sus filtros y reportes.

---

## 9. Scoring (Puntuacion de Votantes)

El modulo de Scoring asigna una puntuacion de 0 a 100 a cada ciudadano registrado, estimando la probabilidad de que vote por Movimiento Ciudadano.

1. En la barra lateral, seleccione **Scoring** dentro de la seccion "Fase 2".
2. Vera una grafica de pastel con la distribucion de segmentos.

### Segmentos

Los ciudadanos se clasifican en cuatro grupos:

| Segmento | Descripcion |
|---|---|
| **Promotor** | Alta probabilidad de voto MC y disposicion a promover activamente |
| **Simpatizante** | Inclinacion favorable, persuadible con contacto adicional |
| **Indeciso** | Sin preferencia clara, requiere mayor atencion |
| **Opositor** | Baja probabilidad de voto MC |

La grafica de pastel muestra los porcentajes de cada segmento, lo cual permite planificar el enfoque de las acciones de campo.

> **Nota importante**: Actualmente el modulo de Scoring utiliza datos sinteticos generados a partir de parametros del INEGI para fines de demostracion. Los resultados no reflejan preferencias reales de votantes.

---

## 10. Contenido (Content Factory)

Este modulo utiliza inteligencia artificial para generar contenido de redes sociales adaptado a cada dirigente.

1. En la barra lateral, seleccione **Contenido** dentro de la seccion "Fase 2".
2. Seleccione al dirigente para el cual desea generar contenido.
3. Defina el tema o contexto de la publicacion.
4. El sistema generara variantes adaptadas a cada plataforma:
   - **Tweet**: Texto breve optimizado para Twitter.
   - **Caption de Instagram**: Texto con hashtags relevantes.
   - **Post de Facebook**: Texto mas extenso con formato adecuado.

### Etiquetado obligatorio INE

Todo contenido generado por inteligencia artificial incluye automaticamente la leyenda:

    "Contenido generado con inteligencia artificial"

Esta etiqueta es **obligatoria** por normativa del INE y no puede ser eliminada.

### Flujo de aprobacion

El contenido generado inicia en estado **Borrador**. Un administrador o analista debe revisarlo y cambiarlo a estado **Aprobado** antes de que pueda ser utilizado o publicado.

---

## 11. Compliance (Blindaje Legal)

El modulo de Compliance ayuda a monitorear el cumplimiento de los limites de gasto electoral establecidos por el INE.

1. En la barra lateral, seleccione **Compliance** dentro de la seccion "Fase 2".
2. Vera un resumen del gasto acumulado contra el tope de campana.

### Elementos principales

- **Tope de campana**: Limite maximo de gasto configurado (por defecto $500,000 MXN, ajustable por el administrador).
- **Gasto acumulado**: Total de gastos registrados hasta la fecha.
- **Barra de progreso**: Representacion visual de cuanto del tope se ha utilizado.

### Alertas de violacion

Si un gasto registrado excede los limites o se detectan inconsistencias, el sistema generara alertas con nivel de severidad (baja, media, alta). Revise estas alertas y tome las acciones correctivas necesarias.

### Datos electorales de referencia

El modulo incluye informacion de referencia de las elecciones CDMX 2024 para contexto.

### Importar gastos

Para registrar gastos en lote:

1. Prepare un archivo Excel con las columnas requeridas (concepto, monto, fecha, proveedor).
2. Haga clic en el boton de importacion.
3. Seleccione su archivo y confirme la carga.

---

## 12. Campanas (WhatsApp)

Este modulo permite crear y enviar campanas de mensajeria por WhatsApp a traves de la integracion con Chatwoot.

1. En la barra lateral, seleccione **Campanas** dentro de la seccion "Fase 2".
2. Haga clic en **Crear campana**.

### Pasos para crear una campana

1. **Definir audiencia**: Segmente los destinatarios utilizando los filtros disponibles:
   - Seccion electoral.
   - Rango de edad.
   - Genero.
   - Intencion de voto.
2. **Redactar mensaje**: Escriba el contenido del mensaje. Puede usar variables personalizadas (nombre del destinatario, seccion, etc.).
3. **Vista previa**: Revise como se vera el mensaje antes de enviarlo.
4. **Enviar**: Confirme y lance la campana.

### Seguimiento de envios

Despues de enviar, la plataforma muestra el estado de cada mensaje:

| Estado | Significado |
|---|---|
| Enviado | El mensaje salio del sistema |
| Entregado | El mensaje llego al telefono del destinatario |
| Leido | El destinatario abrio el mensaje |
| Fallido | El mensaje no pudo ser entregado |

---

## 13. Canvassing (Rutas de Campo)

El modulo de Canvassing permite planificar rutas optimizadas para operadores de campo que realizan visitas domiciliarias.

1. En la barra lateral, seleccione **Canvassing** dentro de la seccion "Fase 2".
2. Seleccione la seccion electoral donde desea planificar una ruta.
3. El sistema generara automaticamente una ruta de recorrido optimizada, minimizando la distancia total a pie.

### Funcionalidades

- **Visualizacion en mapa**: La ruta se muestra sobre un mapa con los puntos de visita numerados.
- **Seguimiento de ejecucion**: Los operadores de campo pueden marcar cada punto como visitado conforme avanzan por la ruta.

El calculo de rutas utiliza georreferenciacion con PostGIS para encontrar el recorrido mas eficiente entre los domicilios de la seccion seleccionada.

---

## 14. Participacion Ciudadana

Este modulo permite gestionar solicitudes y retroalimentacion de la ciudadania.

1. En la barra lateral, seleccione **Participacion** dentro de la seccion "Fase 2".
2. Vera una lista de solicitudes ciudadanas con su estado actual.

### Gestionar solicitudes

- **Crear solicitud**: Registre una nueva solicitud ciudadana con la descripcion del tema, ubicacion y datos de contacto.
- **Seguimiento de estado**: Cada solicitud pasa por los estados: Recibida, En proceso, Resuelta.
- **Responder**: Agregue notas de seguimiento y respuestas a cada solicitud.

### Mapa de calor de participacion

Una visualizacion geografica muestra las zonas con mayor concentracion de solicitudes ciudadanas, lo que permite identificar areas que requieren mayor atencion.

---

## 15. Configuracion

Disponible unicamente para usuarios con rol de **Administrador**.

1. En la barra lateral, seleccione **Configuracion** en la seccion "Sistema".
2. Desde aqui puede gestionar parametros generales de la plataforma, cuentas de usuario y configuraciones de integracion.

---

## 16. Consejos Generales

### Navegacion

- La **barra lateral izquierda** contiene todos los modulos organizados por seccion: Principal, Analisis, Fase 2 y Sistema.
- Para **colapsar la barra lateral** y ganar espacio en pantalla, haga clic en el icono de flecha en la parte inferior de la barra. Haga clic nuevamente para expandirla.
- En **dispositivos moviles**, la barra lateral se abre tocando el icono de menu (tres lineas horizontales) en la esquina superior izquierda.

### Barra superior

- En la barra superior encontrara un campo de **busqueda rapida** que le permite localizar secciones de la plataforma escribiendo su nombre.
- El interruptor de **modo oscuro** se encuentra en la barra superior. Active o desactive el modo oscuro segun su preferencia visual.
- Su **nombre de usuario y rol** se muestran en la parte inferior de la barra lateral con las iniciales de su nombre.

### Actualizacion de datos

Los datos de la plataforma se actualizan automaticamente cada 60 segundos. No es necesario recargar la pagina manualmente para ver informacion nueva.

### Roles y permisos

Recuerde que lo que puede ver y hacer depende de su tipo de cuenta:

- Los **dirigentes** ven unicamente sus propios datos. Los filtros se aplican automaticamente y no pueden ser modificados.
- Los **analistas** pueden consultar informacion de todos los dirigentes y tienen acceso a herramientas de creacion de contenido y planes.
- Los **administradores** tienen acceso completo a todos los modulos, incluyendo configuracion del sistema.

### Soporte

Si tiene preguntas o dificultades para utilizar la plataforma, contacte al equipo de soporte en:

    soporte@consultoriamd.com

---

*Documento elaborado por ConsultoriaMD para uso interno de operadores politicos, analistas y dirigentes de Movimiento Ciudadano CDMX.*
