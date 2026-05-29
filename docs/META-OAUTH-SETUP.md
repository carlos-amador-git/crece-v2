# Meta OAuth Setup — CRECE v2

**Objetivo:** conectar Instagram + Facebook de los 8 dirigentes a CRECE usando OAuth oficial (Graph API), sin App Review, en Development Mode.

## Paso 1: Meta Business Manager

Verificar que MD Consultoría tenga Business Manager activo:

1. Ir a [business.facebook.com](https://business.facebook.com)
2. Login con cuenta admin MD Consultoría
3. Si no existe: Crear → "MD Consultoría SC" → RFC + dirección fiscal
4. Configuración → Verificación del negocio → subir docs legales (acta constitutiva, RFC)

## Paso 2: Crear App Meta

1. Ir a [developers.facebook.com/apps](https://developers.facebook.com/apps)
2. "Create App" → tipo: **Business** → nombre: **"CRECE v2"**
3. Asociar al Business Manager MD Consultoría
4. Copiar **App ID** y **App Secret** → guardar en `backend/.env`:
   ```
   META_APP_ID=xxxxxxxxxxxxxxx
   META_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

## Paso 3: Configurar productos OAuth

1. En la App → "Add Product" → **Facebook Login for Business** + **Instagram**
2. Facebook Login for Business → Settings → Valid OAuth Redirect URIs:
   ```
   http://localhost:8002/api/v1/auth/callback/meta
   https://crece.mdconsultoria-ti.org/api/v1/auth/callback/meta
   ```
3. Products → Facebook Login → Permissions → **solicitar** (sin App Review para Dev Mode):
   - `pages_show_list`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_manage_insights`
   - `business_management`

## Paso 4: Agregar dirigentes como Administrators

**IMPORTANTE:** NO usar rol "Tester" (lenguaje amateur). Usar **"Administrator"**.

Meta App → Roles → **Add People** → rol **"Administrator"** para cada dirigente:

| Dirigente | Email FB (a confirmar) |
|---|---|
| Alejandro Piña Medina | `???@???` |
| Rafael Solano Pérez | `???@???` |
| Saymi Adriana Pineda Velasco | `???@???` |
| Yesenia Nolasco Ramírez | `???@???` |
| Gabriela Jiménez Godoy | `???@???` |
| César Cravioto Romero | `???@???` |
| Laura Ballesteros Mancilla | `???@???` |
| Jorge Álvarez Máynez | `???@???` |

Cada dirigente recibirá email automático de Meta:
> *"You've been added as an Administrator of the app CRECE v2"*

(Palabra "Administrator", nunca "Tester".)

## Paso 5: Email previo a dirigentes (enviado por CRECE)

**Template** — enviar 5 min ANTES de invitación Meta para explicar el flujo:

---

**Asunto:** Acceso a CRECE — Conecta tus redes sociales

[Nombre del dirigente],

MD Consultoría te agrega como usuario de la app CRECE v2.

En los próximos minutos recibirás una invitación oficial de Meta (Facebook) para confirmar tu rol. Solo tienes que hacer click en el botón que te llegue — el proceso toma 10 segundos.

Una vez confirmado, podrás conectar tu cuenta de **Instagram** y **Facebook** directamente en CRECE, con dos beneficios inmediatos:

1. **Analytics oficiales de Meta** — reach, impresiones, audiencia demográfica real (no estimados)
2. **Detección de seguidores fantasma** — identificamos cuentas bot/fake que inflan tus números

Los datos se procesan bajo nuestro Aviso de Privacidad (LFPDPPP art. 10-IV). Solo tú ves tus propios resultados — ningún otro usuario de CRECE tiene acceso cruzado.

Si tienes dudas, responde a este correo o llámanos a MD Consultoría.

— Equipo CRECE

---

## Paso 6: Instagram Business/Creator Account

**Pre-requisito técnico:** La cuenta IG del dirigente debe ser **Business** o **Creator** (no personal), y estar vinculada a la **Facebook Page** correspondiente.

Si la cuenta IG es personal, el dirigente debe:
1. IG App → Settings → Account → **Switch to Professional Account** (gratis, 1 click)
2. Conectar a su FB Page

Sin este paso, Graph API IG Business NO puede leer insights.

**Validación previa:** antes de mandar invitación, verificar en Instagram Web que el dirigente tiene "Cuenta Profesional" activa.

## Paso 7: Privacy Policy + Terms URLs

Meta exige URLs públicas en la App:

- Privacy Policy: `https://crece.mdconsultoria-ti.org/legal/privacidad` (ya existe Sprint C)
- Terms of Service: `https://crece.mdconsultoria-ti.org/legal/terminos` (crear si no existe)
- Data Deletion Instructions: `https://crece.mdconsultoria-ti.org/legal/eliminacion-datos` (necesario Meta, crear)

Configurar en App → Settings → Basic.

## Paso 8: Verificación Dev Mode funciona

Una vez dirigente acepta invitación:
1. CRECE → `/dashboard/configuracion/redes` → click "Conectar Instagram"
2. Popup Meta OAuth → dirigente selecciona cuenta IG Business → consent
3. CRECE recibe token → ingesta histórica inicia

## Checklist completo Sprint OAuth-00

- [ ] Business Manager MD Consultoría verificado con docs legales
- [ ] App "CRECE v2" creada + App ID/Secret en `.env`
- [ ] Facebook Login for Business configurado + redirect URIs
- [ ] 5 permisos solicitados
- [ ] Privacy Policy / Terms / Data Deletion URLs públicos
- [ ] 8 dirigentes agregados como Administrators con sus emails FB
- [ ] Email previo enviado a los 8 (template arriba)
- [ ] Invitaciones Meta auto-enviadas
- [ ] Verificar que cada cuenta IG es Business/Creator (no personal)
- [ ] 1 dirigente test conecta exitosamente
- [ ] Documentación actualizada con App ID público + scopes

## Límites Development Mode

- Hasta **25 Administrators/Developers** sin App Review
- Cuando CRECE crezca a 25+ clientes → someter App Review (4-8 semanas, pero con uso real documentado = aprobación ágil)
- Cada rotación de `auth_token` (cada 60 días) requiere que el dirigente haga re-login en CRECE → popup OAuth otra vez → 10s

## Qué NO hacer

- ❌ Usar rol "Tester" (lenguaje amateur)
- ❌ Usar app con email/cuenta personal del developer
- ❌ Pedir permiso `ads_management` sin justificación (requiere App Review)
- ❌ Skippear Privacy Policy (Meta rechaza)
- ❌ Olvidar el paso de IG Business account (falla silenciosa)
