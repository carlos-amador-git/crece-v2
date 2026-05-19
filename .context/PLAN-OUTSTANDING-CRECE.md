# Propuesta: CRECE "Outstanding" & Humanizado 🚀

Esta propuesta integra el workflow técnico de la guía **"Outstanding Web"** con la visión estratégica de humanizar la marca mediante videos de personas reales (jóvenes y adultos) interactuando positivamente con su entorno digital.

## Objetivo
Transformar la interfaz actual de CRECE en una experiencia cinematográfica que demuestre, de forma visceral, que los datos se traducen en **conexiones humanas reales**.

---

## Fase 1: Limpieza y Fundaciones (El Esqueleto)
*Objetivo: Preparar la UI para que los videos sean los protagonistas.*

### Sprint 1.1: UI De-cluttering & Glassmorphism
- **Acción:** Eliminar bordes duros, líneas divisorias y fondos sólidos en `Cards` y `Sidebars`.
- **Técnica:** Implementar `backdrop-blur` y opacidades variables (Glassmorphism). Los datos deben "flotar" sobre la vida real.
- **Resultado:** Una interfaz "limpia" preparada para recibir fondos expansivos.

---

## Fase 2: Factoría de Assets Humanos (La Estética)
*Objetivo: Generar los visuales que validan el éxito de la plataforma.*

### Sprint 2.1: Generación de Clips "Vida Real" (IA Visual)
- **Acción:** Usar Luma o Runway para generar clips de 5-10s.
- **Prompts Clave:** 
  - *Hero Login:* "Montaje cinemático de jóvenes y adultos en un café de la CDMX, mirando sus teléfonos, sonriendo genuinamente, luz de atardecer, profundidad de campo."
  - *Onboarding:* "Primer plano de un político asintiendo con satisfacción mientras revisa una tablet en una oficina moderna."
- **Técnica:** Mantener el "Espacio Negativo" en el centro para no obstruir los formularios de login (Fase 2.1 de la guía).

---

## Fase 3: Implementación de Alto Impacto (El Factor "Wow")
*Objetivo: Integrar el código para que la página se sienta viva.*

### Sprint 3.1: Hero Login con Scroll-Tied Playback
- **Acción:** Implementar el video de fondo en el Login.
- **Técnica:** El video no es un simple loop; su reproducción se ancla al scroll del usuario mediante GSAP.
- **Impacto:** Al mover el ratón o hacer scroll, las personas en el video parecen reaccionar al movimiento del usuario.

### Sprint 3.2: El Truco del "Focal Point" (Cards de Aceptación)
- **Acción:** En el dashboard de Aceptación, usar **un solo video vertical** de una persona sonriendo para alimentar el fondo de 3 tarjetas de KPIs.
- **Configuración:** 
  - Tarjeta A (Aprobación): `object-position: top` (enfocado en los ojos/expresión).
  - Tarjeta B (Sentimiento): `object-position: center` (enfocado en la sonrisa).
  - Tarjeta C (Crecimiento): `object-position: bottom` (enfocado en las manos con el celular).
- **Impacto:** Cohesión visual absoluta con costo de rendimiento mínimo.

---

## Fase 4: Pulido y Micro-Interacciones (El Cierre)
*Objetivo: Detalles premium y rendimiento.*

### Sprint 4.1: Iconografía Animada
- **Acción:** Sustituir iconos de Lucide estáticos por versiones animadas (Lottie o Material Symbols) que se disparen al hover sobre las métricas.

### Sprint 4.2: Footer Parallax Reveal
- **Acción:** En el dashboard principal, el video de fondo se revela totalmente al llegar al final de la página, "empujando" el contenido hacia arriba para mostrar el CTA final.

---

## 📋 Checklist de Validación
- [ ] ¿El texto es legible sobre los videos (Overlay/Blur)?
- [ ] ¿El video del Login tiene el centro despejado?
- [ ] ¿Estamos usando un solo video para múltiples tarjetas (Focal Point)?
- [ ] ¿El rendimiento es óptimo (Lazy loading de videos)?

---
**Siguiente Paso Inmediato:** Iniciar Sprint 1.1 en la página de Login.
