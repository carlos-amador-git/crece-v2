"use client";

import { useRef } from "react";
import { motion, useInView } from "motion/react";
import { Button } from "@/components/ui/button";
import { ArrowRight, CheckCircle2 } from "lucide-react";

const BENEFITS = [
  "Setup completo en 48 horas",
  "Sin contratos de largo plazo",
  "Soporte directo con el equipo de desarrollo",
  "Datos protegidos — procesamiento local disponible",
] as const;

export function CtaSection() {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section ref={ref} id="contact" className="py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="overflow-hidden rounded-2xl bg-primary px-8 py-14 text-primary-foreground sm:px-14 lg:px-20"
        >
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-heading text-3xl font-extrabold tracking-tight text-balance sm:text-4xl">
              Transforma tu estrategia política con datos reales
            </h2>
            <p className="mt-4 text-base text-white/70 text-pretty">
              Agenda una demostración personalizada y descubre cómo CRECE puede
              darle ventaja digital a tu equipo.
            </p>

            {/* Benefits */}
            <ul className="mx-auto mt-8 flex max-w-md flex-col gap-2.5 text-left" role="list">
              {BENEFITS.map((benefit) => (
                <li key={benefit} className="flex items-center gap-2.5 text-sm text-white/80">
                  <CheckCircle2 className="size-4 shrink-0 text-accent" />
                  {benefit}
                </li>
              ))}
            </ul>

            {/* CTA */}
            <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
              <Button
                size="lg"
                className="cursor-pointer bg-cta text-cta-foreground transition-colors duration-150 hover:bg-cta/90 focus-visible:ring-cta"
                asChild
              >
                <a href="mailto:contacto@mdconsultoria-ti.org?subject=Demo%20CRECE%20v2">
                  Agendar demostración
                  <ArrowRight className="ml-2 size-4" />
                </a>
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="cursor-pointer border-white/20 text-white hover:bg-white/10 hover:text-white"
                asChild
              >
                <a href="mailto:contacto@mdconsultoria-ti.org?subject=Información%20CRECE">
                  Solicitar información
                </a>
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
