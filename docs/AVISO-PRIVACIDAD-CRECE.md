# Aviso de Privacidad — CRECE v2

**Última actualización:** 14 de abril de 2026
**Responsable del tratamiento:** MD Consultoría SC — Ciudad de México, México

---

## 1. Identidad y domicilio del responsable

MD Consultoría SC (en adelante "MD Consultoría"), responsable del tratamiento de datos personales recabados por la plataforma CRECE v2. Para cualquier contacto relacionado con este aviso o el ejercicio de derechos ARCO: **privacidad@mdconsultoria-ti.org**.

## 2. Datos personales tratados

CRECE v2 es una plataforma de inteligencia política. Recaba y trata los siguientes tipos de datos:

### 2.1 De los dirigentes políticos (clientes de CRECE)
- Nombre completo, cargo, partido, entidad federativa
- Handles de redes sociales públicas (Twitter/X, Facebook, Instagram, TikTok, YouTube, LinkedIn)
- Contenido de publicaciones públicas del dirigente en dichas redes
- Métricas públicas de sus cuentas (followers, engagement)

### 2.2 De usuarios que interactúan con publicaciones del dirigente
- **Contenido de comentarios públicos** (solo el texto del comentario, no el perfil completo del comentarista)
- **Identificador pseudonimizado** del comentarista (hash SHA-256 con salt — NO se almacena el user_id crudo, nombre, ni foto)
- Conteo de likes, replies, fecha del comentario (datos públicos agregados)

**NO recabamos:**
- Nombre real, correo electrónico, teléfono ni dirección de comentaristas
- Lista de seguidores individual
- Datos sensibles (salud, orientación sexual, religión, afiliación partidista explícita)
- Ubicación GPS de usuarios

## 3. Fuente de los datos

Todos los datos provienen de **fuentes de acceso público**: redes sociales donde el dirigente y los comentaristas han elegido publicar contenido visible para el público general. MD Consultoría NO accede a cuentas privadas ni a información protegida por configuraciones de privacidad del usuario.

## 4. Finalidades del tratamiento

**Finalidades primarias (sin las cuales no puede prestarse el servicio):**
1. Análisis estadístico agregado de la presencia digital del dirigente contratante
2. Cálculo del Índice de Aceptación (IA) sobre publicaciones: qué proporción de reacciones públicas aprueba, rechaza o es neutral
3. Identificación de narrativas, temas y tendencias en el discurso público relacionado con el dirigente
4. Generación de reportes de inteligencia política para el cliente

**Finalidades secundarias (opcionales):**
- Investigación académica sobre comunicación política mexicana (solo datos agregados, nunca identificables)
- Mejora de algoritmos NLP en español político (entrenamiento con datos despersonalizados)

El cliente o usuario puede oponerse a las finalidades secundarias escribiendo a privacidad@mdconsultoria-ti.org.

## 5. Fundamento legal

El tratamiento se realiza con fundamento en:
- Artículo 10 fracción IV de la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP): **los datos provienen de fuentes de acceso público**, lo que exime del consentimiento expreso para su recolección
- Artículo 16 fracción II LFPDPPP: **interés legítimo** del dirigente contratante para conocer la aceptación pública de sus mensajes, proporcional y necesario para ejercer su función política

Aún así, MD Consultoría aplica el principio de **minimización de datos** (art. 11 LFPDPPP) mediante pseudonimización por hash y nunca almacena PII crudo de comentaristas.

## 6. Transferencias

**MD Consultoría NO transfiere datos personales a terceros.** Los proveedores de infraestructura (Coolify para hosting, PostgreSQL para almacenamiento) son encargados de tratamiento bajo contrato que garantiza confidencialidad, no responsables independientes.

## 7. Derechos ARCO

Todo titular de datos personales puede ejercer derechos de Acceso, Rectificación, Cancelación u Oposición (ARCO) mediante:

**Canal:** privacidad@mdconsultoria-ti.org
**Información requerida:**
- Identificación oficial del titular (INE/pasaporte)
- Descripción clara del derecho que se ejerce
- Dato o información específica sobre la que se ejerce el derecho (para comentaristas: URL del comentario público)

**Plazo de respuesta:** 20 días hábiles a partir de la recepción completa de la solicitud (art. 32 LFPDPPP).

### 7.1 Cancelación de datos de comentarista

Dado que usamos pseudonimización por hash, podemos **cancelar** (borrar) todos los comentarios asociados a un hash específico si el titular demuestra:
1. Que el user_id público coincide con el hash en nuestra base (podemos recalcular el hash a partir del user_id que el titular provee)
2. Titularidad del perfil público correspondiente

## 8. Retención de datos

**Datos de dirigentes cliente:** durante la vigencia del contrato de servicio + 5 años posteriores (fines fiscales y de auditoría).

**Comentarios públicos con hash:**
- 180 días desde su captura, después de lo cual se **borran del sistema**
- Las métricas agregadas (IA scores por post, tendencias) se conservan sin asociación individual
- Cron job automático ejecuta la eliminación diaria

**Datos agregados e históricos:** indefinido (no identificables).

## 9. Uso de cookies y tecnologías de rastreo

CRECE v2 es una plataforma SaaS accesible por usuarios autorizados. Usa cookies estrictamente necesarias para sesión (autenticación JWT) y organización activa (multi-tenant). NO usa cookies de analítica o publicidad.

## 10. Seguridad

- Cifrado TLS 1.3 en tránsito
- PostgreSQL con Row Level Security (RLS) por organización
- Columnas PII cifradas con pgcrypto
- Acceso al sistema por JWT con expiración corta
- Auditoría de accesos administrativos

## 11. Cambios al aviso de privacidad

MD Consultoría notificará cualquier cambio sustancial mediante aviso en la plataforma y por correo electrónico a los dirigentes contratantes. La versión vigente siempre estará disponible en `/legal/privacidad` de la plataforma.

---

**Responsable:** MD Consultoría SC
**Contacto:** privacidad@mdconsultoria-ti.org
**Fecha de entrada en vigor:** 14 de abril de 2026
