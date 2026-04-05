"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "motion/react";

/* ── Animated counter hook ───────────────────────────────── */

function useCounter(end: number, duration: number, inView: boolean) {
  const [count, setCount] = useState(0);
  const hasAnimated = useRef(false);

  useEffect(() => {
    if (!inView || hasAnimated.current) return;
    hasAnimated.current = true;

    const startTime = performance.now();
    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * end));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [inView, end, duration]);

  return count;
}

/* ── Stats data ──────────────────────────────────────────── */

const STATS = [
  { value: 145, suffix: "+", label: "Endpoints de API", description: "Cobertura completa de datos" },
  { value: 37, suffix: "", label: "Tablas de datos", description: "Modelo relacional profundo" },
  { value: 6, suffix: "", label: "Plataformas monitoreadas", description: "Twitter, IG, FB, TikTok, YT, web" },
  { value: 48, suffix: "hrs", label: "Tiempo de setup", description: "De cero a operación" },
] as const;

/* ── Counter card ────────────────────────────────────────── */

function StatCard({
  value,
  suffix,
  label,
  description,
  inView,
}: (typeof STATS)[number] & { inView: boolean }) {
  const count = useCounter(value, 1800, inView);

  return (
    <div className="text-center">
      <p className="font-heading text-4xl font-extrabold tabular-nums text-primary sm:text-5xl">
        {count}
        <span className="text-accent">{suffix}</span>
      </p>
      <p className="mt-2 text-sm font-semibold text-foreground">{label}</p>
      <p className="mt-0.5 text-xs text-muted-foreground text-pretty">
        {description}
      </p>
    </div>
  );
}

/* ── Stats section ───────────────────────────────────────── */

export function Stats() {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      ref={ref}
      id="stats"
      className="border-y border-border/40 bg-muted/30 py-16 lg:py-20"
    >
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="grid grid-cols-2 gap-8 sm:gap-12 lg:grid-cols-4"
        >
          {STATS.map((stat) => (
            <StatCard key={stat.label} {...stat} inView={inView} />
          ))}
        </motion.div>
      </div>
    </section>
  );
}
