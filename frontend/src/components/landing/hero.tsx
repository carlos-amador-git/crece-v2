"use client";

import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import {
  ArrowRight,
  TrendingUp,
  Shield,
  BarChart3,
  Activity,
} from "lucide-react";

/* ── Stylized dashboard preview ──────────────────────────── */

function DashboardMockup() {
  return (
    <div
      aria-hidden="true"
      className="relative mx-auto w-full max-w-lg rounded-xl border border-border bg-card shadow-xl lg:max-w-none"
    >
      {/* Window chrome */}
      <div className="flex items-center gap-1.5 border-b border-border px-4 py-3">
        <span className="size-2.5 rounded-full bg-red-400/60" />
        <span className="size-2.5 rounded-full bg-amber-400/60" />
        <span className="size-2.5 rounded-full bg-emerald-400/60" />
        <span className="ml-3 text-xs text-muted-foreground">
          crece.mdconsultoria-ti.org/dashboard
        </span>
      </div>

      {/* Mock content */}
      <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3">
        {/* KPI cards */}
        {[
          { label: "IPD Promedio", value: "6.8", icon: TrendingUp, color: "text-emerald" },
          { label: "Alertas Activas", value: "3", icon: Shield, color: "text-cta" },
          { label: "Sentimiento", value: "+12%", icon: Activity, color: "text-accent" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div
            key={label}
            className="rounded-lg border border-border/60 bg-background p-3"
          >
            <div className="flex items-center gap-1.5">
              <Icon className={`size-3.5 ${color}`} />
              <span className="text-[10px] text-muted-foreground">{label}</span>
            </div>
            <p className="mt-1 font-heading text-lg font-bold tabular-nums text-foreground">
              {value}
            </p>
          </div>
        ))}

        {/* Chart placeholder */}
        <div className="col-span-2 flex items-end gap-1 rounded-lg border border-border/60 bg-background p-3 sm:col-span-3">
          {[40, 55, 35, 70, 60, 85, 75, 90, 65, 80, 95, 72].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-primary/20"
              style={{ height: `${h * 0.6}px` }}
            >
              <div
                className="w-full rounded-t bg-primary"
                style={{ height: `${h * 0.35}px`, marginTop: `${h * 0.25}px` }}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Hero section ────────────────────────────────────────── */

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-28 pb-16 lg:pt-36 lg:pb-24">
      {/* Subtle background texture */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,hsl(var(--primary)/0.04)_0%,transparent_60%)]"
      />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 lg:grid-cols-[1fr_1.1fr] lg:gap-16">
        {/* Left — Copy */}
        <motion.div
          initial="hidden"
          animate="visible"
          transition={{ staggerChildren: 0.1 }}
        >
          <motion.div variants={fadeUp} transition={{ duration: 0.5, ease: "easeOut" }}>
            <Badge
              variant="secondary"
              className="mb-6 cursor-default border-accent/20 bg-accent/10 text-accent"
            >
              <BarChart3 className="mr-1.5 size-3" />
              Plataforma de Inteligencia Política
            </Badge>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="font-heading text-4xl font-extrabold leading-[1.1] tracking-tight text-foreground text-balance sm:text-5xl lg:text-6xl"
          >
            Decisiones políticas
            <br />
            <span className="text-primary">basadas en datos,</span>
            <br />
            no en intuición
          </motion.h1>

          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mt-6 max-w-lg text-lg text-muted-foreground text-pretty"
          >
            CRECE monitorea redes sociales, analiza sentimiento con IA y genera
            estrategias accionables para equipos de campaña y dirigentes políticos.
          </motion.p>

          <motion.div
            variants={fadeUp}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mt-8 flex flex-wrap gap-3"
          >
            <Button
              size="lg"
              className="cursor-pointer bg-cta text-cta-foreground transition-colors duration-150 hover:bg-cta/90 focus-visible:ring-cta"
              asChild
            >
              <a href="#contact">
                Solicitar demo
                <ArrowRight className="ml-2 size-4" />
              </a>
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="cursor-pointer transition-colors duration-150"
              asChild
            >
              <Link href="/login">Ver plataforma</Link>
            </Button>
          </motion.div>

          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mt-4 text-xs text-muted-foreground"
          >
            Sin compromiso · Setup en 48 hrs · Soporte dedicado
          </motion.p>
        </motion.div>

        {/* Right — Dashboard mockup */}
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, ease: "easeOut", delay: 0.3 }}
        >
          <DashboardMockup />
        </motion.div>
      </div>
    </section>
  );
}
