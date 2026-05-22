import Link from "next/link";

const FOOTER_LINKS = {
  Plataforma: [
    { label: "Diagnóstico Digital", href: "#features" },
    { label: "Monitoreo Social", href: "#features" },
    { label: "Benchmarking", href: "#features" },
    { label: "Planes con IA", href: "#features" },
  ],
  Empresa: [
    { label: "Sobre nosotros", href: "https://mdconsultoria-ti.org" },
    { label: "Contacto", href: "mailto:contacto@mdconsultoria-ti.org" },
  ],
  Legal: [
    { label: "Aviso de privacidad", href: "/privacidad" },
    { label: "Términos de servicio", href: "/terminos" },
  ],
} as const;

export function Footer() {
  return (
    <footer className="border-t border-border/40 bg-muted/20">
      <div className="mx-auto max-w-6xl px-6 py-12 lg:py-16">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {/* Brand */}
          <div>
            <Link
              href="/"
              className="font-heading text-xl font-extrabold tracking-tight text-primary"
            >
              CRECE
            </Link>
            <p className="mt-3 text-sm text-muted-foreground text-pretty">
              Plataforma de inteligencia política. Monitoreo social, análisis
              electoral y estrategia con IA.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(FOOTER_LINKS).map(([heading, links]) => (
            <nav key={heading} aria-label={heading}>
              <h3 className="text-sm font-semibold text-foreground">{heading}</h3>
              <ul className="mt-3 space-y-2" role="list">
                {links.map(({ label, href }) => (
                  <li key={label}>
                    <a
                      href={href}
                      className="text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
                    >
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border/40 pt-8 text-xs text-muted-foreground sm:flex-row">
          <p>&copy; {new Date().getFullYear()} MD Consultoría TI. Todos los derechos reservados.</p>
          <p>
            Hecho con datos reales para{" "}
            <span className="font-medium text-foreground">dirigentes políticos de México</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
