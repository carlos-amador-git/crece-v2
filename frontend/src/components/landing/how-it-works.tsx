"use client";

import { useRef } from "react";
import { motion, useInView } from "motion/react";
import { Plug, Cpu, Rocket } from "lucide-react";

const STEPS = [
  {
    number: "01",
    icon: Plug,
    title: "Conectar",
    description:
      "Vincula las cuentas de redes sociales de tus dirigentes. Sin acceso a contraseñas — solo perfiles públicos y APIs oficiales.",
  },
  {
    number: "02",
    icon: Cpu,
    title: "Analizar",
    description:
      "Nuestros modelos de NLP procesan menciones, sentimiento, toxicidad y temas. La IA genera diagnósticos y estrategias personalizadas.",
  },
  {
    number: "03",
    icon: Rocket,
    title: "Actuar",
    description:
      "Recibe alertas de crisis, planes de acción y reportes listos para compartir con tu equipo. Todo en un solo dashboard.",
  },
] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function HowItWorks() {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section
      ref={ref}
      id="how-it-works"
      className="border-t border-border/40 bg-muted/20 py-20 lg:py-28"
    >
      <div className="mx-auto max-w-6xl px-6">
        {/* Header */}
        <motion.div
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          transition={{ staggerChildren: 0.08 }}
          className="mx-auto max-w-2xl text-center"
        >
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="text-sm font-semibold uppercase tracking-wide text-accent"
          >
            Proceso
          </motion.p>
          <motion.h2
            variants={fadeUp}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="mt-3 font-heading text-3xl font-extrabold tracking-tight text-foreground text-balance sm:text-4xl"
          >
            De datos dispersos a estrategia en 3 pasos
          </motion.h2>
        </motion.div>

        {/* Steps */}
        <motion.div
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          transition={{ staggerChildren: 0.12, delayChildren: 0.2 }}
          className="mt-14 grid gap-8 md:grid-cols-3"
        >
          {STEPS.map(({ number, icon: Icon, title, description }) => (
            <motion.div
              key={number}
              variants={fadeUp}
              transition={{ duration: 0.45, ease: "easeOut" }}
              className="relative text-center"
            >
              {/* Step number */}
              <span className="font-heading text-6xl font-extrabold text-border/60 select-none">
                {number}
              </span>

              {/* Icon */}
              <div className="mx-auto -mt-4 flex size-14 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                <Icon className="size-6" />
              </div>

              <h3 className="mt-5 font-heading text-xl font-bold text-foreground">
                {title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground text-pretty">
                {description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
