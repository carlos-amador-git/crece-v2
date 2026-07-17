"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useOnboardDirigente,
  useOnboardingProgress,
  type OnboardingHandle,
  type OnboardingPlatform,
  type RolPolitico,
} from "@/lib/api/hooks/use-onboarding";

type Step = 1 | 2 | 3 | 4;

const PLATFORMS: OnboardingPlatform[] = [
  "TWITTER",
  "INSTAGRAM",
  "FACEBOOK",
  "TIKTOK",
  "YOUTUBE",
];

const STEP_LABELS: Record<
  "scraping" | "analyzing" | "calculating_ipd" | "ready",
  string
> = {
  scraping: "Scraping inicial",
  analyzing: "Análisis NLP",
  calculating_ipd: "Calculando IPD",
  ready: "Listo",
};

export function OnboardingWizard() {
  const [step, setStep] = useState<Step>(1);
  const [dirigenteId, setDirigenteId] = useState<number | null>(null);

  // Step 1 — Datos básicos + credenciales
  const [fullName, setFullName] = useState("");
  const [cargo, setCargo] = useState("");
  const [municipio, setMunicipio] = useState("Cuauhtémoc");
  const [partido, setPartido] = useState("MC");
  // DISENO-actores-politicos-2026-07-16: rol obligatorio — decisión humana
  // explícita, sin default (el backend rechaza el alta sin él).
  const [rolPolitico, setRolPolitico] = useState<RolPolitico | "">("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Step 2 — Handles
  const [handles, setHandles] = useState<OnboardingHandle[]>([
    { platform: "TWITTER", handle: "" },
  ]);

  const onboard = useOnboardDirigente();
  const progressQuery = useOnboardingProgress(dirigenteId, step === 4);

  const step1Valid =
    fullName.length >= 3 &&
    cargo.length >= 2 &&
    rolPolitico !== "" &&
    email.includes("@") &&
    password.length >= 8;
  const step2Valid = handles.every((h) => h.handle.trim().length > 0);

  const addHandle = () =>
    setHandles((prev) => [...prev, { platform: "TWITTER", handle: "" }]);

  const updateHandle = (i: number, patch: Partial<OnboardingHandle>) =>
    setHandles((prev) =>
      prev.map((h, idx) => (idx === i ? { ...h, ...patch } : h)),
    );

  const removeHandle = (i: number) =>
    setHandles((prev) => prev.filter((_, idx) => idx !== i));

  const submit = async () => {
    try {
      if (rolPolitico === "") return; // guard — step1Valid ya lo exige
      const res = await onboard.mutateAsync({
        full_name: fullName,
        cargo,
        municipio,
        partido,
        rol_politico: rolPolitico,
        email,
        password,
        handles: handles.map((h) => ({ ...h, handle: h.handle.trim() })),
      });
      setDirigenteId(res.dirigente_id);
      setStep(4);
    } catch (err) {
      // Error message shown via onboard.error
      console.error("onboard failed", err);
    }
  };

  return (
    <Card className="max-w-3xl">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Onboarding Político</CardTitle>
            <p className="text-sm text-muted-foreground">
              Alta de un nuevo político en menos de 5 minutos
            </p>
          </div>
          <div className="flex gap-2">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className={`h-8 w-8 rounded-full text-center leading-8 text-xs font-semibold ${
                  step === n
                    ? "bg-primary text-primary-foreground"
                    : step > n
                      ? "bg-emerald-600 text-white"
                      : "bg-muted text-muted-foreground"
                }`}
              >
                {step > n ? "✓" : n}
              </div>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {step === 1 && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-muted-foreground">
              Paso 1 — Datos básicos
            </h3>
            <div className="grid gap-3">
              <div>
                <label className="text-xs text-muted-foreground">Nombre completo</label>
                <Input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ej. Alejandro Piña Medina"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground">Cargo</label>
                  <Input
                    value={cargo}
                    onChange={(e) => setCargo(e.target.value)}
                    placeholder="Ej. Alcalde de Cuauhtémoc"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Municipio</label>
                  <Input
                    value={municipio}
                    onChange={(e) => setMunicipio(e.target.value)}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground">Partido</label>
                  <Input
                    value={partido}
                    onChange={(e) => setPartido(e.target.value)}
                    placeholder="Ej. MORENA"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">
                    Rol político (define cómo se califica)
                  </label>
                  <Select
                    value={rolPolitico}
                    onValueChange={(v) => setRolPolitico(v as RolPolitico)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona el rol" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="oficialismo">Oficialismo</SelectItem>
                      <SelectItem value="oposicion">Oposición</SelectItem>
                      <SelectItem value="independiente">Independiente</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground">Email login</label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="politico@crece.mx"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">
                    Password temporal (mín 8)
                  </label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end">
              <Button disabled={!step1Valid} onClick={() => setStep(2)}>
                Siguiente →
              </Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-muted-foreground">
              Paso 2 — Handles de redes sociales
            </h3>
            <div className="space-y-2">
              {handles.map((h, i) => (
                <div key={i} className="flex gap-2">
                  <Select
                    value={h.platform}
                    onValueChange={(v) =>
                      updateHandle(i, { platform: v as OnboardingPlatform })
                    }
                  >
                    <SelectTrigger className="w-[140px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PLATFORMS.map((p) => (
                        <SelectItem key={p} value={p}>
                          {p}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    placeholder="@handle"
                    value={h.handle}
                    onChange={(e) => updateHandle(i, { handle: e.target.value })}
                  />
                  {handles.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => removeHandle(i)}>
                      ✕
                    </Button>
                  )}
                </div>
              ))}
              <Button variant="outline" size="sm" onClick={addHandle}>
                + Agregar handle
              </Button>
            </div>
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep(1)}>
                ← Atrás
              </Button>
              <Button disabled={!step2Valid} onClick={() => setStep(3)}>
                Siguiente →
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-muted-foreground">
              Paso 3 — Confirmación
            </h3>
            <div className="space-y-2 rounded-md border p-4 text-sm">
              <div>
                <span className="text-muted-foreground">Nombre:</span>{" "}
                <strong>{fullName}</strong>
              </div>
              <div>
                <span className="text-muted-foreground">Cargo:</span> {cargo}
              </div>
              <div>
                <span className="text-muted-foreground">Municipio:</span> {municipio}
              </div>
              <div>
                <span className="text-muted-foreground">Email login:</span> {email}
              </div>
              <div className="pt-2">
                <span className="text-muted-foreground">Handles:</span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {handles.map((h, i) => (
                    <Badge key={i} variant="outline">
                      {h.platform}: {h.handle}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
            {onboard.error && (
              <p className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-600 dark:bg-rose-950/30">
                {(onboard.error as Error).message}
              </p>
            )}
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep(2)}>
                ← Atrás
              </Button>
              <Button onClick={submit} disabled={onboard.isPending}>
                {onboard.isPending ? "Creando…" : "Crear dirigente"}
              </Button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-muted-foreground">
              Paso 4 — Progreso del scraping
            </h3>
            {progressQuery.data ? (
              <>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>
                      Estado: <strong>{progressQuery.data.sync_status}</strong>
                    </span>
                    <span>{progressQuery.data.progress_pct}%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-primary transition-all duration-500"
                      style={{ width: `${progressQuery.data.progress_pct}%` }}
                    />
                  </div>
                </div>
                <ul className="space-y-2">
                  {progressQuery.data.steps.map((s) => (
                    <li
                      key={s.name}
                      className="flex items-center gap-3 rounded-md border border-border/50 px-3 py-2 text-sm"
                    >
                      <span
                        className={`h-2 w-2 shrink-0 rounded-full ${
                          s.status === "done"
                            ? "bg-emerald-500"
                            : s.status === "running"
                              ? "bg-amber-400 animate-pulse"
                              : s.status === "error"
                                ? "bg-rose-500"
                                : "bg-muted-foreground/30"
                        }`}
                      />
                      <span className="flex-1">{STEP_LABELS[s.name]}</span>
                      <span className="text-xs text-muted-foreground">
                        {s.status}
                      </span>
                    </li>
                  ))}
                </ul>
                {progressQuery.data.sync_status === "ready" && (
                  <div className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400">
                    Dirigente listo. Redirigiendo al dashboard…
                    <RedirectOnReady dirigenteId={progressQuery.data.dirigente_id} />
                  </div>
                )}
                {progressQuery.data.error && (
                  <p className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-600 dark:bg-rose-950/30">
                    Error: {progressQuery.data.error}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Iniciando…</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RedirectOnReady({ dirigenteId }: { dirigenteId: number }) {
  // S5.5 — auto-login/redirect. Por ahora solo redirige a la vista del
  // dirigente recién creado. Token handoff real queda en deuda.
  if (typeof window !== "undefined") {
    setTimeout(() => {
      window.location.href = `/dashboard/dirigentes?highlight=${dirigenteId}`;
    }, 2000);
  }
  return null;
}
