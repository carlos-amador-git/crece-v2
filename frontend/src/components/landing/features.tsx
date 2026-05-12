"use client";

import { useRef } from "react";
import { motion, useInView } from "motion/react";
import {
  Activity,
  BarChart3,
  Brain,
  Globe,
  MessageSquareWarning,
  Target,
} from "lucide-react";

const FEATURES = [
  {
    icon: Activity,
    title: "Diagnóstico Digital",
    description:
      "Índice de Penetración Digital (IPD) 0-10 por dirigente. Mide presencia real en cada plataforma con métricas normalizadas.",
    accent: "bg-emerald-500/10 text-emerald-600",
  },
  {
    icon: Globe,
    title: "Monitoreo Social",
    description:
      "Scrapers en 6 plataformas con NLP multi-modelo: sentimiento, controversia, toxicidad y temas trending en tiempo real.",
    accent: "bg-sky-500/10 text-sky-600",
  },
  {
    icon: BarChart3,
    title: "Benchmarking Competitivo",
    description:
      "Compara dirigentes vs competidores y vs promedios nacionales del partido con datos verificados del INE.",
    accent: "bg-violet-500/10 text-violet-600",
  },
  {
    icon: Brain,
    title: "Planes Estratégicos con IA",
    description:
      "Generación de estrategias con Claude y Gemma local. Streaming en tiempo real, costos controlados, datos sensibles protegidos.",
    accent: "bg-amber-500/10 text-amber-600",
  },
  {
    icon: MessageSquareWarning,
    title: "Alertas de Crisis",
    description:
      "Detección automática de picos de negatividad, contenido viral adverso y controversias emergentes antes de que escalen.",
    accent: "bg-red-500/10 text-red-600",
  },
  {
    icon: Target,
    title: "Inteligencia Electoral",
    description:
      "Datos georreferenciados por sección electoral, análisis de tendencias de voto y optimización de rutas de canvassing.",
    accent: "bg-primary/10 text-primary",
  },
] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function Features() {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section ref={ref} id="features" className="py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-6">
        {/* Section header */}
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
            Capacidades
          </motion.p>
          <motion.h2
            variants={fadeUp}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="mt-3 font-heading text-3xl font-extrabold tracking-tight text-foreground text-balance sm:text-4xl"
          >
            Todo lo que necesitas para ganar terreno digital
          </motion.h2>
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="mt-4 text-muted-foreground text-pretty"
          >
            Seis módulos integrados que convierten datos dispersos en ventaja
            estratégica medible.
          </motion.p>
        </motion.div>

        {/* Feature grid */}
        <motion.div
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          transition={{ staggerChildren: 0.06, delayChildren: 0.2 }}
          className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3"
        >
          {FEATURES.map(({ icon: Icon, title, description, accent }) => (
            <motion.article
              key={title}
              variants={fadeUp}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="group rounded-xl border border-border/60 bg-card p-6 transition-shadow duration-150 hover:shadow-md"
            >
              <div
                className={`inline-flex size-10 items-center justify-center rounded-lg ${accent}`}
              >
                <Icon className="size-5" />
              </div>
              <h3 className="mt-4 font-heading text-lg font-bold text-foreground">
                {title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground text-pretty">
                {description}
              </p>
            </motion.article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
