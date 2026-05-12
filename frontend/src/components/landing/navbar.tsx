"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { label: "Capacidades", href: "#features" },
  { label: "Proceso", href: "#how-it-works" },
  { label: "Métricas", href: "#stats" },
] as const;

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-md">
      <nav
        className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6"
        aria-label="Navegación principal"
      >
        {/* Wordmark */}
        <Link
          href="/"
          className="font-heading text-xl font-extrabold tracking-tight text-primary"
        >
          CRECE
        </Link>

        {/* Desktop nav */}
        <ul className="hidden items-center gap-8 md:flex" role="list">
          {NAV_LINKS.map(({ label, href }) => (
            <li key={href}>
              <a
                href={href}
                className="text-sm font-medium text-muted-foreground transition-colors duration-150 hover:text-foreground"
              >
                {label}
              </a>
            </li>
          ))}
        </ul>

        {/* Desktop CTAs */}
        <div className="hidden items-center gap-3 md:flex">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/login">Iniciar sesión</Link>
          </Button>
          <Button
            size="sm"
            className="cursor-pointer bg-cta text-cta-foreground transition-colors duration-150 hover:bg-cta/90 focus-visible:ring-cta"
            asChild
          >
            <a href="#contact">Solicitar demo</a>
          </Button>
        </div>

        {/* Mobile menu button */}
        <button
          type="button"
          className="cursor-pointer md:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? (
            <X className="size-5 text-foreground" />
          ) : (
            <Menu className="size-5 text-foreground" />
          )}
        </button>
      </nav>

      {/* Mobile panel */}
      <div
        className={cn(
          "overflow-hidden border-t border-border/40 bg-background transition-[max-height] duration-200 ease-out md:hidden",
          mobileOpen ? "max-h-64" : "max-h-0"
        )}
      >
        <div className="space-y-1 px-6 py-4">
          {NAV_LINKS.map(({ label, href }) => (
            <a
              key={href}
              href={href}
              className="block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground"
              onClick={() => setMobileOpen(false)}
            >
              {label}
            </a>
          ))}
          <div className="flex flex-col gap-2 pt-3">
            <Button variant="outline" size="sm" asChild>
              <Link href="/login">Iniciar sesión</Link>
            </Button>
            <Button
              size="sm"
              className="cursor-pointer bg-cta text-cta-foreground hover:bg-cta/90"
              asChild
            >
              <a href="#contact">Solicitar demo</a>
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
