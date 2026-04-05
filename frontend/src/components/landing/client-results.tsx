"use client";

import { useRef } from "react";
import { motion, useInView } from "motion/react";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  Users,
  BarChart3,
  ArrowUpRight,
  Twitter,
  Instagram,
  Facebook,
} from "lucide-react";

/* ── Client profiles data ────────────────────────────── */

const CLIENTS = [
  {
    name: "Alejandro Piña Medina",
    role: "Coordinador Comisión Operativa Estatal",
    partido: "MC",
    avatar: "AP",
    avatarBg: "bg-primary text-primary-foreground",
    ipd: { score: 3.7, target: 7.0, label: "En crecimiento" },
    metrics: [
      { label: "Seguidores", value: "7,131", icon: Users, trend: "+12%" },
      { label: "Engagement", value: "3.7%", icon: TrendingUp, trend: "+0.8%" },
      { label: "Posts/semana", value: "4.2", icon: BarChart3, trend: "+2.1" },
    ],
    platforms: [
      { name: "Twitter", icon: Twitter, followers: "3.1K", handle: "@Alejandro_Pinha" },
      { name: "Instagram", icon: Instagram, followers: "2.2K", handle: "@alejandro.pinha" },
      { name: "Facebook", icon: Facebook, followers: "1.8K", handle: "alejandropinamedina" },
    ],
    sentiment: { positive: 68, neutral: 20, negative: 12 },
    recommendation:
      "Plan de consolidación de 90 días generado con IA: expandir a TikTok y YouTube, incrementar frecuencia de posting a 12/semana.",
  },
  {
    name: "Rafael Solano Pérez",
    role: "Miembro Comisión Estatal · Analista La Razón",
    partido: "MC",
    avatar: "RS",
    avatarBg: "bg-accent text-accent-foreground",
    ipd: { score: 1.68, target: 5.0, label: "Oportunidad" },
    metrics: [
      { label: "Seguidores", value: "620", icon: Users, trend: "Nuevo" },
      { label: "Engagement", value: "4.7%", icon: TrendingUp, trend: "Alto" },
      { label: "Cobertura", value: "33%", icon: BarChart3, trend: "2/6 plat." },
    ],
    platforms: [
      { name: "Instagram", icon: Instagram, followers: "450", handle: "@rafasolanoperez" },
      { name: "Twitter", icon: Twitter, followers: "170", handle: "@rafasolanoperez" },
    ],
    sentiment: { positive: 80, neutral: 15, negative: 5 },
    recommendation:
      "Perfil ideal para estrategia de arranque: alto engagement orgánico, construir presencia en 4 plataformas faltantes.",
  },
] as const;

/* ── Animations ──────────────────────────────────────── */

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

/* ── Sentiment bar ───────────────────────────────────── */

function SentimentBar({ positive, neutral, negative }: { positive: number; neutral: number; negative: number }) {
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full">
      <div className="bg-emerald-500" style={{ width: `${positive}%` }} />
      <div className="bg-amber-400" style={{ width: `${neutral}%` }} />
      <div className="bg-red-400" style={{ width: `${negative}%` }} />
    </div>
  );
}

/* ── IPD gauge ───────────────────────────────────────── */

function IpdGauge({ score, target }: { score: number; target: number }) {
  const pct = (score / 10) * 100;
  const targetPct = (target / 10) * 100;

  return (
    <div className="relative">
      <div className="flex items-end gap-1">
        <span className="font-heading text-3xl font-extrabold tabular-nums text-primary">
          {score.toFixed(1)}
        </span>
        <span className="mb-1 text-sm text-muted-foreground">/10</span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
        <span>Actual</span>
        <span>Meta: {target.toFixed(1)}</span>
      </div>
    </div>
  );
}

/* ── Client card ─────────────────────────────────────── */

function ClientCard({ client, index }: { client: (typeof CLIENTS)[number]; index: number }) {
  return (
    <motion.article
      variants={fadeUp}
      transition={{ duration: 0.5, ease: "easeOut", delay: index * 0.15 }}
      className="overflow-hidden rounded-xl border border-border/60 bg-card shadow-sm"
    >
      {/* Header */}
      <div className="border-b border-border/40 bg-muted/30 px-6 py-5">
        <div className="flex items-center gap-4">
          <div
            className={`flex size-12 shrink-0 items-center justify-center rounded-full font-heading text-sm font-bold ${client.avatarBg}`}
          >
            {client.avatar}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-heading text-lg font-bold text-foreground truncate">
                {client.name}
              </h3>
              <Badge variant="outline" className="shrink-0 text-[10px]">
                {client.partido}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground truncate">{client.role}</p>
          </div>
        </div>
      </div>

      <div className="p-6">
        {/* IPD Score */}
        <div className="mb-5">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Índice de Penetración Digital
            </span>
            <Badge
              variant="secondary"
              className="text-[10px]"
            >
              {client.ipd.label}
            </Badge>
          </div>
          <IpdGauge score={client.ipd.score} target={client.ipd.target} />
        </div>

        {/* Metrics row */}
        <div className="mb-5 grid grid-cols-3 gap-3">
          {client.metrics.map(({ label, value, icon: Icon, trend }) => (
            <div key={label} className="rounded-lg bg-muted/40 p-3">
              <div className="flex items-center gap-1.5">
                <Icon className="size-3.5 text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground">{label}</span>
              </div>
              <p className="mt-1 font-heading text-base font-bold tabular-nums text-foreground">
                {value}
              </p>
              <p className="text-[10px] text-emerald-600">{trend}</p>
            </div>
          ))}
        </div>

        {/* Platforms */}
        <div className="mb-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Plataformas activas
          </p>
          <div className="space-y-2">
            {client.platforms.map(({ name, icon: Icon, followers, handle }) => (
              <div key={name} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <Icon className="size-4 text-muted-foreground" />
                  <span className="text-foreground">{handle}</span>
                </div>
                <span className="tabular-nums text-muted-foreground">{followers}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Sentiment */}
        <div className="mb-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Sentimiento público
          </p>
          <SentimentBar {...client.sentiment} />
          <div className="mt-1.5 flex justify-between text-[10px] text-muted-foreground">
            <span className="text-emerald-600">{client.sentiment.positive}% positivo</span>
            <span className="text-amber-500">{client.sentiment.neutral}% neutro</span>
            <span className="text-red-400">{client.sentiment.negative}% negativo</span>
          </div>
        </div>

        {/* AI Recommendation */}
        <div className="rounded-lg border border-accent/20 bg-accent/5 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-accent">
            <ArrowUpRight className="size-3.5" />
            Recomendación IA
          </div>
          <p className="text-xs leading-relaxed text-muted-foreground text-pretty">
            {client.recommendation}
          </p>
        </div>
      </div>
    </motion.article>
  );
}

/* ── Section ─────────────────────────────────────────── */

export function ClientResults() {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section ref={ref} className="border-t border-border/40 py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-6">
        {/* Header */}
        <motion.div
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          transition={{ staggerChildren: 0.08 }}
          className="mx-auto mb-14 max-w-2xl text-center"
        >
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="text-sm font-semibold uppercase tracking-wide text-accent"
          >
            Resultados reales
          </motion.p>
          <motion.h2
            variants={fadeUp}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="mt-3 font-heading text-3xl font-extrabold tracking-tight text-foreground text-balance sm:text-4xl"
          >
            Diagnósticos que transforman estrategias
          </motion.h2>
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="mt-4 text-muted-foreground text-pretty"
          >
            Perfiles reales analizados por CRECE. Cada dirigente recibe un
            diagnóstico digital personalizado con métricas accionables y planes
            generados con inteligencia artificial.
          </motion.p>
        </motion.div>

        {/* Client cards */}
        <motion.div
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          className="grid gap-8 lg:grid-cols-2"
        >
          {CLIENTS.map((client, i) => (
            <ClientCard key={client.name} client={client} index={i} />
          ))}
        </motion.div>
      </div>
    </section>
  );
}
