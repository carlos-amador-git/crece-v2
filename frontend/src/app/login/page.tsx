"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Shield, BarChart3, MapPin, Loader2, AlertCircle } from "lucide-react";

/* ────────────────────────────────────────────────────────────
   Dot Grid — pure CSS electoral-section visualization
   A 12x8 grid of small dots. A handful are "lit" in teal or
   orange to suggest live data without heavy animation.
   ──────────────────────────────────────────────────────────── */

const GRID_COLS = 12;
const GRID_ROWS = 8;

/** Indices of dots that pulse teal (accent / data) */
const TEAL_DOTS = new Set([5, 14, 17, 29, 38, 41, 53, 60, 66, 74, 83, 90]);
/** Indices of dots that pulse orange (MC brand) */
const ORANGE_DOTS = new Set([9, 22, 35, 47, 56, 71, 78, 88]);

function DotGrid() {
  const dots = Array.from({ length: GRID_COLS * GRID_ROWS }, (_, i) => {
    const isTeal = TEAL_DOTS.has(i);
    const isOrange = ORANGE_DOTS.has(i);
    const isLit = isTeal || isOrange;

    return (
      <span
        key={i}
        aria-hidden="true"
        className={[
          "block size-1.5 rounded-full transition-colors duration-200",
          isLit ? "" : "bg-white/[0.08]",
          isTeal ? "bg-accent dot-pulse-teal" : "",
          isOrange ? "bg-cta dot-pulse-orange" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      />
    );
  });

  return (
    <div
      aria-hidden="true"
      className="grid gap-3"
      style={{
        gridTemplateColumns: `repeat(${GRID_COLS}, minmax(0, 1fr))`,
      }}
    >
      {dots}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Feature highlights — left panel
   ──────────────────────────────────────────────────────────── */

const FEATURES = [
  {
    icon: Shield,
    text: "Monitoreo de crisis y alertas en tiempo real",
  },
  {
    icon: BarChart3,
    text: "Benchmarking competitivo con datos del INE",
  },
  {
    icon: MapPin,
    text: "Inteligencia electoral georreferenciada",
  },
] as const;

/* ────────────────────────────────────────────────────────────
   Login form (right panel)
   ──────────────────────────────────────────────────────────── */

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ email, password });
      router.push("/dashboard");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Error al iniciar sesion";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-dvh flex-col lg:flex-row">
      {/* ── Left panel (brand + features + dot grid) ─────── */}
      <div
        className={[
          "relative flex flex-col justify-between overflow-hidden",
          /* Dark navy background — uses primary token (215 70% 12%) */
          "bg-primary text-primary-foreground",
          /* Mobile: short hero. Desktop: 60% width */
          "px-8 py-10 lg:w-[60%] lg:px-16 lg:py-16",
        ].join(" ")}
      >
        {/* Top section: wordmark + subtitle + features */}
        <div className="relative z-10 max-w-lg">
          <h1 className="font-heading text-4xl font-extrabold tracking-tight text-balance lg:text-5xl">
            CRECE
          </h1>
          <p className="mt-2 text-base font-medium text-white/70 lg:text-lg">
            Inteligencia Politica en Tiempo Real
          </p>

          <ul className="mt-8 hidden space-y-4 lg:block" role="list">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-white/[0.08]">
                  <Icon className="size-4 text-accent" aria-hidden="true" />
                </span>
                <span className="text-sm text-white/80">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Dot grid — positioned at bottom, fades into background */}
        <div className="relative z-10 mt-8 hidden lg:block">
          <DotGrid />
        </div>

        {/* Credit */}
        <p className="relative z-10 mt-6 text-xs text-white/30 lg:mt-8">
          ConsultoriaMD
        </p>
      </div>

      {/* ── Right panel (login form) ─────────────────────── */}
      <div className="flex flex-1 flex-col items-center justify-center bg-background px-6 py-12 lg:px-16">
        <div className="w-full max-w-sm">
          {/* Form header */}
          <header className="mb-8">
            <h2 className="font-heading text-2xl font-bold tracking-tight text-foreground text-balance">
              Iniciar sesion
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Ingresa tus credenciales para acceder al panel
            </p>
          </header>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Inline error */}
            {error && (
              <div
                className="flex items-center gap-2 rounded-md border border-destructive/20 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
                role="alert"
              >
                <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
                {error}
              </div>
            )}

            {/* Email */}
            <div className="space-y-2">
              <label
                htmlFor="login-email"
                className="text-sm font-medium leading-none text-foreground"
              >
                Correo electronico
              </label>
              <Input
                id="login-email"
                type="email"
                placeholder="tu@correo.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                autoFocus
                className="focus-visible:ring-accent"
              />
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label
                htmlFor="login-password"
                className="text-sm font-medium leading-none text-foreground"
              >
                Contrasena
              </label>
              <Input
                id="login-password"
                type="password"
                placeholder="Tu contrasena"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="focus-visible:ring-accent"
              />
            </div>

            {/* Submit — MC Orange CTA */}
            <Button
              type="submit"
              className="w-full bg-cta text-cta-foreground hover:bg-cta/90 focus-visible:ring-cta transition-colors duration-150"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2
                    className="size-4 animate-spin"
                    aria-hidden="true"
                  />
                  Ingresando...
                </>
              ) : (
                "Iniciar sesion"
              )}
            </Button>
          </form>

          {/* Forgot password */}
          <p className="mt-6 text-center text-sm">
            <a
              href="/forgot-password"
              className="text-muted-foreground transition-colors duration-150 hover:text-foreground"
            >
              ¿Olvidaste tu contraseña?
            </a>
          </p>

          {/* Version badge */}
          <p className="mt-8 text-center text-xs text-muted-foreground">
            CRECE v2.0
          </p>
        </div>
      </div>

    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Page export — wraps in AuthProvider
   ──────────────────────────────────────────────────────────── */

export default function LoginPage() {
  return (
    <AuthProvider>
      <LoginForm />
    </AuthProvider>
  );
}
