"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-full bg-muted ${className ?? ""}`}>
      <div
        className="h-full bg-accent transition-all duration-500"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
import { CheckCircle2, Circle, Sparkles, Zap, Brain, Target } from "lucide-react";

/**
 * Settings · Análisis Político — Niveles de profundidad
 *
 * Lenguaje 100% amigable al político. Sin mencionar modelos.
 * Gamifica el progreso hacia el siguiente nivel.
 */

type NivelKey = "rapido" | "enriquecido" | "contextual" | "personalizado";

interface Nivel {
  key: NivelKey;
  nombre: string;
  icono: typeof Zap;
  descripcion: string;
  beneficios: string[];
  status: "done" | "active" | "locked";
  unlock?: string;
}

const NIVELES: Nivel[] = [
  {
    key: "rapido",
    nombre: "Análisis Rápido",
    icono: Zap,
    descripcion: "Detecta emociones básicas del contenido: positivo, negativo, neutral.",
    beneficios: [
      "Clasificación automática de todos tus posts",
      "Tendencias de sentimiento por plataforma",
      "Alerta cuando hay picos negativos inusuales",
    ],
    status: "done",
  },
  {
    key: "enriquecido",
    nombre: "Análisis Enriquecido",
    icono: Sparkles,
    descripcion: "Además del sentimiento, detecta toxicidad, polémica y temas políticos del post.",
    beneficios: [
      "Identifica posts con tono ofensivo",
      "Clasifica temas: gobierno, seguridad, economía, educación, etc.",
      "Corrige sesgos naturales de cada red social",
    ],
    status: "done",
  },
  {
    key: "contextual",
    nombre: "Análisis Contextual",
    icono: Brain,
    descripcion:
      "El sistema entiende tu rol político (oficialismo/oposición) y evalúa cada post según TU framework estratégico, no una métrica genérica.",
    beneficios: [
      "Criticar al gobierno cuando eres oposición cuenta como discurso efectivo, no negativo",
      "Tú personalizas qué tipos de mensajes construyen vs dañan tu imagen",
      "Explicaciones en lenguaje político, no técnico",
    ],
    status: "active",
  },
  {
    key: "personalizado",
    nombre: "Análisis Personalizado",
    icono: Target,
    descripcion:
      "Un sistema entrenado específicamente con tus propias validaciones. Más rápido, más preciso, más adaptado a tu estilo.",
    beneficios: [
      "Análisis en tiempo real (sin esperas)",
      "Aprende tus matices particulares (ironía, tono local, doble lectura)",
      "Menor costo computacional",
    ],
    status: "locked",
    unlock: "Se desbloquea automáticamente al alcanzar 500 posts validados",
  },
];

export default function AnalisisPoliticoPage() {
  // TODO: traer del API el número real de validaciones
  const postsValidados = 47;
  const postsObjetivo = 500;
  const progreso = Math.min(100, (postsValidados / postsObjetivo) * 100);

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-6">
      {/* Header */}
      <header>
        <h1 className="font-heading text-2xl font-bold">Análisis Político</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Tu plataforma evoluciona contigo. Cada nivel de análisis aporta inteligencia más
          profunda sobre tu comunicación.
        </p>
      </header>

      {/* Current level banner */}
      <Card className="border-accent/30 bg-gradient-to-br from-accent/5 to-transparent">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-full bg-accent/20 p-3">
              <Brain className="h-6 w-6 text-accent" />
            </div>
            <div className="flex-1">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Nivel actual
                </span>
                <Badge variant="secondary" className="bg-accent/10 text-accent">
                  ACTIVO
                </Badge>
              </div>
              <h2 className="font-heading text-xl font-semibold">Análisis Contextual</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                El sistema evalúa tus posts según el framework estratégico que configuraste.{" "}
                <a
                  href="/dashboard/settings/framework-politico"
                  className="text-accent underline underline-offset-2"
                >
                  Ver mi framework →
                </a>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Progress to next level */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base">
            <span>Progreso al siguiente nivel: Análisis Personalizado</span>
            <span className="font-normal tabular-nums text-muted-foreground">
              {postsValidados} / {postsObjetivo}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Progress value={progreso} className="h-3" />
          <p className="mt-3 text-sm text-muted-foreground">
            Cada post que validas (acepta, rechaza o corrige la clasificación del sistema) suma a
            tu progreso. A los <strong>500 posts validados</strong>, se entrena un sistema
            específico para ti que es más rápido y preciso.
          </p>
          <div className="mt-4 flex gap-3">
            <a
              href="/dashboard/validacion"
              className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:opacity-90"
            >
              Validar posts pendientes →
            </a>
            <a
              href="/dashboard/settings/framework-politico"
              className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
            >
              Editar framework
            </a>
          </div>
        </CardContent>
      </Card>

      {/* All levels list */}
      <section>
        <h2 className="mb-4 font-heading text-lg font-semibold">Los 4 niveles</h2>
        <div className="space-y-3">
          {NIVELES.map((nivel) => {
            const Icono = nivel.icono;
            const isDone = nivel.status === "done";
            const isActive = nivel.status === "active";
            const isLocked = nivel.status === "locked";
            return (
              <Card
                key={nivel.key}
                className={
                  isActive
                    ? "border-accent/40 bg-accent/5"
                    : isLocked
                      ? "opacity-70"
                      : ""
                }
              >
                <CardContent className="p-5">
                  <div className="flex items-start gap-4">
                    <div
                      className={`rounded-lg p-2.5 ${
                        isDone || isActive
                          ? "bg-accent/15 text-accent"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <Icono className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-heading font-semibold">{nivel.nombre}</h3>
                        {isDone && (
                          <CheckCircle2
                            className="h-4 w-4 text-emerald-600"
                            aria-label="Completado"
                          />
                        )}
                        {isActive && (
                          <Badge className="h-5 bg-accent/10 px-2 text-[10px] font-semibold text-accent hover:bg-accent/10">
                            NIVEL ACTUAL
                          </Badge>
                        )}
                        {isLocked && (
                          <Circle
                            className="h-4 w-4 text-muted-foreground/60"
                            aria-label="Bloqueado"
                          />
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{nivel.descripcion}</p>
                      <ul className="mt-3 space-y-1">
                        {nivel.beneficios.map((b, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2 text-xs text-foreground/80"
                          >
                            <span className="mt-1 block h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" />
                            {b}
                          </li>
                        ))}
                      </ul>
                      {nivel.unlock && (
                        <p className="mt-3 text-xs italic text-muted-foreground">
                          🔒 {nivel.unlock}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Transparency note */}
      <Card className="border-dashed">
        <CardContent className="p-5">
          <p className="text-sm text-muted-foreground">
            <strong className="text-foreground">Compromiso de transparencia:</strong> todos los
            niveles de análisis son auditables. Puedes revisar las reglas, validar casos y
            exportar el framework completo en{" "}
            <a
              href="/dashboard/settings/framework-politico"
              className="text-accent underline underline-offset-2"
            >
              configuración del framework
            </a>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
