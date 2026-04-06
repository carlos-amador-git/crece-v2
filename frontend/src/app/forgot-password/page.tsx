"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Mail, CheckCircle2 } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // In production this would call POST /auth/forgot-password
    setSubmitted(true);
  };

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-6">
      <div className="w-full max-w-sm">
        {/* Back link */}
        <Link
          href="/login"
          className="mb-8 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Volver al login
        </Link>

        {!submitted ? (
          <>
            <header className="mb-8">
              <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground text-balance">
                Recuperar contraseña
              </h1>
              <p className="mt-2 text-sm text-muted-foreground text-pretty">
                Ingresa tu correo electrónico y te enviaremos instrucciones para
                restablecer tu contraseña.
              </p>
            </header>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label
                  htmlFor="reset-email"
                  className="text-sm font-medium leading-none text-foreground"
                >
                  Correo electrónico
                </label>
                <Input
                  id="reset-email"
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

              <Button
                type="submit"
                className="w-full cursor-pointer bg-cta text-cta-foreground transition-colors duration-150 hover:bg-cta/90 focus-visible:ring-cta"
              >
                <Mail className="mr-2 size-4" />
                Enviar instrucciones
              </Button>
            </form>
          </>
        ) : (
          <div className="text-center">
            <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-full bg-emerald-500/10">
              <CheckCircle2 className="size-6 text-emerald-600" />
            </div>
            <h2 className="font-heading text-xl font-bold text-foreground">
              Revisa tu correo
            </h2>
            <p className="mt-2 text-sm text-muted-foreground text-pretty">
              Si existe una cuenta con{" "}
              <span className="font-medium text-foreground">{email}</span>,
              recibirás un enlace para restablecer tu contraseña.
            </p>
            <Button
              variant="outline"
              className="mt-6 cursor-pointer"
              asChild
            >
              <Link href="/login">Volver al login</Link>
            </Button>
          </div>
        )}

        <p className="mt-10 text-center text-xs text-muted-foreground">
          CRECE v2.0
        </p>
      </div>
    </div>
  );
}
