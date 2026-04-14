"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSidebarStore } from "@/lib/store";
import { useAuth } from "@/lib/auth";
import { useKpiOverview } from "@/lib/api/hooks/use-overview";
import { formatNumber } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  Map,
  BarChart3,
  Brain,
  Settings,
  ChevronLeft,
  ChevronRight,
  X,
  FileText,
  Shield,
  Send,
  MapPin,
  Vote,
  Bot,
  ClipboardList,
  Sliders,
} from "lucide-react";

const sections = [
  {
    label: "Principal",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { href: "/dashboard/dirigentes", label: "Dirigentes", icon: Users },
      { href: "/dashboard/social", label: "Social", icon: MessageSquare },
    ],
  },
  {
    label: "Analisis",
    items: [
      { href: "/dashboard/benchmark", label: "Benchmarks", icon: BarChart3 },
      { href: "/dashboard/planes", label: "Planes IA", icon: Brain },
      { href: "/dashboard/bot-detection", label: "Salud Digital", icon: Bot },
    ],
  },
  {
    label: "Fase 2",
    items: [
      { href: "/dashboard/ciudadanos", label: "Ciudadanos", icon: Users },
      { href: "/dashboard/scoring", label: "Scoring", icon: BarChart3 },
      { href: "/dashboard/contenido", label: "Contenido", icon: FileText },
      { href: "/dashboard/compliance", label: "Compliance", icon: Shield },
      { href: "/dashboard/campanas", label: "Campanas", icon: Send },
      { href: "/dashboard/canvassing", label: "Canvassing", icon: MapPin },
      { href: "/dashboard/participacion", label: "Participacion", icon: Vote },
    ],
  },
  {
    label: "Sistema",
    items: [
      { href: "/dashboard/settings/analisis-politico", label: "Analisis Politico", icon: Sliders, prefetch: false },
      // prefetch disabled: evita 404 de RSC prefetch si el bundle de /settings
      // no está aún en el deploy más reciente; la página carga en navegación real.
      { href: "/dashboard/settings", label: "Configuracion", icon: Settings, prefetch: false },
    ],
  },
  {
    label: "Admin MD",
    adminOnly: true,
    items: [
      { href: "/dashboard/admin/clasificacion", label: "Clasificacion Manual", icon: ClipboardList, prefetch: false },
    ],
  },
];

/** Map role keys to display labels */
const roleLabels: Record<string, string> = {
  admin: "Administrador",
  analyst: "Analista",
  field_operator: "Operador de Campo",
  viewer: "Visor",
};

export function Sidebar() {
  const pathname = usePathname();
  const { collapsed, toggle, mobileOpen, setMobileOpen } = useSidebarStore();

  let user: { full_name?: string; role?: string } | null = null;
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const auth = useAuth();
    user = auth.user;
  } catch {
    // AuthProvider not mounted — fall back to defaults
  }

  const displayName = user?.full_name ?? "Admin";
  const userWithDirigente = user as { full_name?: string; role?: string; dirigente_id?: number } | null;
  const isDirigente = !!userWithDirigente?.dirigente_id;
  const displayRole = isDirigente
    ? "Dirigente"
    : user?.role ? (roleLabels[user.role] ?? user.role) : "Admin";

  // When the signed-in user is a dirigente, reuse the overview query (cached)
  // to enrich the sidebar footer with IPD + audiencia.
  const { data: kpiSidebar } = useKpiOverview("30d");
  const ipdLabel = kpiSidebar?.avg_ipd_score != null
    ? kpiSidebar.avg_ipd_score.toFixed(1)
    : null;
  const audienciaLabel = kpiSidebar?.total_audiencia != null
    ? formatNumber(kpiSidebar.total_audiencia)
    : null;
  const initials = displayName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  const content = (
    <TooltipProvider delayDuration={0}>
      <div className="flex h-full flex-col">
        {/* ── Logo area ────────────────────────────────────── */}
        <div className="flex h-16 items-center gap-3 border-b px-4">
          <span
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cta font-heading text-base font-black text-cta-foreground"
            aria-hidden="true"
          >
            C
          </span>
          {!collapsed && (
            <div className="flex flex-col leading-none">
              <span className="font-heading text-lg font-bold tracking-tight">
                CRECE
              </span>
              <span className="text-[10px] text-muted-foreground">v2.0</span>
            </div>
          )}
          {/* Mobile close */}
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menu"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* ── Navigation ───────────────────────────────────── */}
        <ScrollArea className="flex-1 py-4">
          <nav aria-label="Navegacion principal">
            {sections.filter((section) => {
              if ((section as { adminOnly?: boolean }).adminOnly) {
                return user?.role === "admin";
              }
              return true;
            }).map((section) => (
              <div key={section.label} className="mb-4">
                {/* Section label with decorative line */}
                {!collapsed && (
                  <div className="mb-1 flex items-center gap-2 px-4">
                    <p className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      {section.label}
                    </p>
                    <Separator className="flex-1" />
                  </div>
                )}
                {collapsed && <Separator className="mx-auto my-2 w-8" />}
                <ul className="space-y-0.5 px-2">
                  {section.items.map((item) => {
                    const active = isActive(item.href);
                    const linkContent = (
                      <Link
                        href={item.href}
                        prefetch={(item as { prefetch?: boolean }).prefetch ?? undefined}
                        onClick={() => setMobileOpen(false)}
                        className={cn(
                          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150 ease-out",
                          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                          active
                            ? "bg-accent/10 text-accent"
                            : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                          collapsed && "justify-center px-2"
                        )}
                        style={
                          active
                            ? { borderLeft: "3px solid hsl(var(--accent))" }
                            : { borderLeft: "3px solid transparent" }
                        }
                        aria-current={active ? "page" : undefined}
                      >
                        <item.icon className="h-4.5 w-4.5 shrink-0" />
                        {!collapsed && <span>{item.label}</span>}
                      </Link>
                    );

                    if (collapsed) {
                      return (
                        <li key={item.href}>
                          <Tooltip>
                            <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                            <TooltipContent side="right">
                              {item.label}
                            </TooltipContent>
                          </Tooltip>
                        </li>
                      );
                    }

                    return <li key={item.href}>{linkContent}</li>;
                  })}
                </ul>
              </div>
            ))}
          </nav>
        </ScrollArea>

        {/* ── User info — bottom ───────────────────────────── */}
        <div className="border-t px-3 py-3">
          {collapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex justify-center">
                  <span
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground"
                    aria-label={displayName}
                  >
                    {initials}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p className="font-medium">{displayName}</p>
                <p className="text-xs text-muted-foreground">{displayRole}</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            <div className="flex items-center gap-3">
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground"
                aria-hidden="true"
              >
                {initials}
              </span>
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-sm font-medium leading-tight">
                  {displayName}
                </span>
                <div className="mt-0.5 flex flex-wrap items-center gap-1">
                  <span className="inline-flex w-fit rounded-sm bg-accent/10 px-1.5 py-0.5 text-[10px] font-medium text-accent">
                    {displayRole}
                  </span>
                  {isDirigente && ipdLabel && (
                    <span
                      className="inline-flex w-fit items-center rounded-sm bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground tabular-nums"
                      title="Indice de Penetracion Digital"
                    >
                      IPD {ipdLabel}/10
                    </span>
                  )}
                  {isDirigente && audienciaLabel && (
                    <span
                      className="inline-flex w-fit items-center rounded-sm bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground tabular-nums"
                      title="Total de seguidores"
                    >
                      {audienciaLabel}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Collapse toggle — desktop only ───────────────── */}
        <div className="hidden border-t p-2 lg:block">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-center rounded-lg transition-colors duration-150 ease-out"
            onClick={toggle}
            aria-label={collapsed ? "Expandir sidebar" : "Colapsar sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4" />
                <span className="text-xs text-muted-foreground">Colapsar</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </TooltipProvider>
  );

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 transition-opacity duration-150 ease-out lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-[260px] border-r bg-card transition-transform duration-150 ease-out lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        role="navigation"
      >
        {content}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className="hidden h-dvh border-r bg-card transition-[width] duration-150 ease-out lg:block"
        style={{
          width: collapsed
            ? "var(--sidebar-collapsed-width)"
            : "var(--sidebar-width)",
        }}
        role="navigation"
      >
        {content}
      </aside>
    </>
  );
}
