"use client";

import type { ComponentType, SVGProps } from "react";
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
  BarChart3,
  Brain,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  X,
  FileText,
  Shield,
  Send,
  MapPin,
  Vote,
  Bot,
  ClipboardList,
  Sliders,
  Gauge,
  Ghost,
  Activity,
  UserSquare2,
  Stethoscope,
  Sparkles,
  Rocket,
  Wand2,
  Trophy,
  Film,
  Star,
} from "lucide-react";

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

interface LeafItem {
  kind: "leaf";
  href: string;
  label: string;
  icon: IconType;
  prefetch?: boolean;
}

interface GroupItem {
  kind: "group";
  key: string; // para persistir estado expand/collapse
  label: string;
  icon: IconType;
  items: LeafItem[];
}

type SidebarItem = LeafItem | GroupItem;

interface Section {
  label: string;
  adminOnly?: boolean;
  clientOnly?: boolean;
  viewerHide?: boolean;
  items: SidebarItem[];
}

const leaf = (href: string, label: string, icon: IconType, prefetch?: boolean): LeafItem => ({
  kind: "leaf",
  href,
  label,
  icon,
  prefetch,
});

const group = (key: string, label: string, icon: IconType, items: LeafItem[]): GroupItem => ({
  kind: "group",
  key,
  label,
  icon,
  items,
});

const sections: Section[] = [
  {
    label: "Principal",
    clientOnly: true,
    items: [
      leaf("/dashboard", "Overview", LayoutDashboard),
      leaf("/dashboard/dirigentes", "Dirigentes", Users),
      leaf("/dashboard/diagnostico", "Diagnostico", Stethoscope),
      leaf("/dashboard/diagnostico-tier2", "Diferenciadores", Sparkles),
      leaf("/dashboard/diagnostico/foda", "FODA", Shield),
      group("social", "Social", MessageSquare, [
        leaf("/dashboard/social", "Monitoreo", Activity),
        leaf("/dashboard/social/comentarios", "Comentarios", MessageSquare),
        leaf("/dashboard/social/clima", "Clima Político", Activity),
        leaf("/dashboard/content/top", "Top Posts", Trophy),
      ]),
      group("aceptacion", "Indice Aceptacion", Gauge, [
        leaf("/dashboard/aceptacion", "Overview", LayoutDashboard),
        leaf("/dashboard/aceptacion/dirigentes", "Por dirigente", UserSquare2),
        leaf("/dashboard/aceptacion/fantasmas", "Fantasmas", Ghost),
        leaf("/dashboard/aceptacion/fans", "Fans y Perfiles", Star),
      ]),
      leaf("/dashboard/planes", "Planes IA", Brain),
      leaf("/dashboard/reels", "Reels (guiones)", Film),
      leaf("/dashboard/recomendaciones", "Recomendaciones", Wand2),
      leaf("/dashboard/settings/evaluacion-nlp", "Mi Evaluación", ClipboardList),
    ],
  },
  {
    label: "Configuración",
    clientOnly: true,
    items: [
      group("configuracion", "Configuración", Settings, [
        leaf("/dashboard/settings/analisis-politico", "Precisiones de análisis", Sliders, false),
        leaf("/dashboard/sistema/metodologia", "Metodología", FileText, false),
      ]),
    ],
  },
  {
    label: "Territorio y campana",
    clientOnly: true,
    viewerHide: true,
    items: [
      group("territorio", "Territorio y campana", MapPin, [
        leaf("/dashboard/ciudadanos", "Ciudadanos", Users),
        leaf("/dashboard/scoring", "Scoring", BarChart3),
        leaf("/dashboard/contenido", "Contenido", FileText),
        leaf("/dashboard/campanas", "Campanas", Send),
        leaf("/dashboard/canvassing", "Canvassing", MapPin),
        leaf("/dashboard/participacion", "Participacion", Vote),
        leaf("/dashboard/compliance", "Compliance", Shield),
      ]),
    ],
  },
  {
    label: "Sistema",
    clientOnly: true,
    viewerHide: true,
    items: [
      group("sistema", "Sistema", Settings, [
        leaf("/dashboard/settings/analisis-politico", "Analisis Politico", Sliders, false),
        leaf("/dashboard/bot-detection", "Salud Digital", Bot),
        leaf("/dashboard/sistema/metodologia", "Metodología", FileText, false),
        leaf("/dashboard/settings", "Configuracion", Settings, false),
      ]),
    ],
  },
  {
    label: "Admin MD",
    adminOnly: true,
    items: [
      leaf("/dashboard/admin/overview", "Operacion de flota", LayoutDashboard, false),
      leaf("/dashboard/admin/ranking", "Ranking competidores", BarChart3, false),
      leaf("/dashboard/admin/clasificacion", "Clasificacion", ClipboardList, false),
      leaf("/dashboard/admin/plan-ia-review", "Plan IA Review", Brain, false),
      leaf("/dashboard/onboarding/1", "Onboarding", Rocket, false),
    ],
  },
];

const roleLabels: Record<string, string> = {
  admin: "Administrador",
  analyst: "Analista",
  field_operator: "Operador de Campo",
  viewer: "Visor",
};

export function Sidebar() {
  const pathname = usePathname();
  const {
    collapsed,
    toggle,
    mobileOpen,
    setMobileOpen,
    expandedGroups,
    toggleGroup,
    setGroupExpanded,
  } = useSidebarStore();

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
    : user?.role
      ? (roleLabels[user.role] ?? user.role)
      : "Admin";

  const { data: kpiSidebar } = useKpiOverview("30d");
  const ipdLabel = kpiSidebar?.avg_ipd_score != null ? kpiSidebar.avg_ipd_score.toFixed(1) : null;
  const audienciaLabel =
    kpiSidebar?.total_audiencia != null ? formatNumber(kpiSidebar.total_audiencia) : null;
  const initials = displayName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    // Diagnóstico: highlight en /dashboard/diagnostico (dispatcher) y /dashboard/diagnostico/{id}
    // pero NO en /dashboard/diagnostico-tier2/... (mismo prefix).
    if (href === "/dashboard/diagnostico") {
      return (
        (pathname === "/dashboard/diagnostico" ||
          (pathname.startsWith("/dashboard/diagnostico/") &&
            !pathname.endsWith("/foda") &&
            !pathname.startsWith("/dashboard/diagnostico/foda"))) &&
        !pathname.startsWith("/dashboard/diagnostico-tier2")
      );
    }
    if (href === "/dashboard/diagnostico/foda") {
      return (
        pathname === "/dashboard/diagnostico/foda" ||
        (pathname.startsWith("/dashboard/diagnostico/") && pathname.endsWith("/foda"))
      );
    }
    if (href === "/dashboard/diagnostico-tier2") {
      return (
        pathname === "/dashboard/diagnostico-tier2" ||
        pathname.startsWith("/dashboard/diagnostico-tier2/")
      );
    }
    return pathname.startsWith(href);
  };

  const groupHasActive = (g: GroupItem) => g.items.some((it) => isActive(it.href));

  // Si un grupo tiene item activo y está colapsado, lo abrimos automáticamente
  // en el primer render. Persistencia respeta la preferencia del usuario después.
  const isGroupExpanded = (g: GroupItem) => {
    if (groupHasActive(g)) return true;
    return expandedGroups[g.key] ?? false;
  };

  const renderLeaf = (item: LeafItem, insideGroup = false) => {
    const active = isActive(item.href);
    const linkContent = (
      <Link
        href={item.href}
        prefetch={item.prefetch ?? undefined}
        onClick={() => setMobileOpen(false)}
        className={cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150 ease-out",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
          active
            ? "bg-accent/10 text-accent"
            : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
          collapsed && "justify-center px-2",
          insideGroup && !collapsed && "pl-9",
        )}
        style={
          active
            ? { borderLeft: "3px solid hsl(var(--accent))" }
            : { borderLeft: "3px solid transparent" }
        }
        aria-current={active ? "page" : undefined}
      >
        <item.icon className="h-4 w-4 shrink-0" />
        {!collapsed && <span>{item.label}</span>}
      </Link>
    );

    if (collapsed) {
      return (
        <li key={item.href}>
          <Tooltip>
            <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
          </Tooltip>
        </li>
      );
    }
    return <li key={item.href}>{linkContent}</li>;
  };

  const renderGroup = (g: GroupItem) => {
    const expanded = isGroupExpanded(g);
    const active = groupHasActive(g);

    // Collapsed sidebar: grupo se presenta como icono único con tooltip listando
    // los hijos. Click expande sidebar entero y abre el grupo.
    if (collapsed) {
      return (
        <li key={g.key}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => {
                  toggle();
                  setGroupExpanded(g.key, true);
                }}
                className={cn(
                  "flex w-full items-center justify-center rounded-md px-2 py-2 text-sm font-medium transition-colors duration-150",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                  active
                    ? "bg-accent/10 text-accent"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
                aria-expanded={expanded}
                aria-label={`${g.label} — expandir`}
                style={
                  active
                    ? { borderLeft: "3px solid hsl(var(--accent))" }
                    : { borderLeft: "3px solid transparent" }
                }
              >
                <g.icon className="h-4 w-4 shrink-0" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-[200px]">
              <p className="font-semibold">{g.label}</p>
              <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                {g.items.map((sub) => (
                  <li key={sub.href}>{sub.label}</li>
                ))}
              </ul>
            </TooltipContent>
          </Tooltip>
        </li>
      );
    }

    return (
      <li key={g.key} className="space-y-0.5">
        <button
          type="button"
          onClick={() => toggleGroup(g.key)}
          className={cn(
            "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
            active && !expanded
              ? "text-accent"
              : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
          )}
          aria-expanded={expanded}
          aria-controls={`sidebar-group-${g.key}`}
          style={{ borderLeft: "3px solid transparent" }}
        >
          <g.icon className="h-4 w-4 shrink-0" />
          <span className="flex-1 text-left">{g.label}</span>
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 shrink-0 transition-transform duration-150",
              expanded ? "rotate-0" : "-rotate-90",
            )}
            aria-hidden="true"
          />
        </button>
        {expanded && (
          <ul id={`sidebar-group-${g.key}`} className="space-y-0.5" role="group">
            {g.items.map((sub) => renderLeaf(sub, true))}
          </ul>
        )}
      </li>
    );
  };

  const renderItem = (item: SidebarItem) =>
    item.kind === "leaf" ? renderLeaf(item) : renderGroup(item);

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
              <span className="font-heading text-lg font-bold tracking-tight">CRECE</span>
              <span className="text-[10px] text-muted-foreground">v2.0</span>
            </div>
          )}
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
            {sections
              .filter((section) => {
                const isAdmin = user?.role === "admin";
                const isViewer = user?.role === "viewer";
                if (section.adminOnly) return isAdmin;
                if (section.clientOnly && isAdmin) return false;
                if (section.viewerHide && isViewer) return false;
                return true;
              })
              .map((section) => (
                <div key={section.label} className="mb-4">
                  {!collapsed && (
                    <div className="mb-1 flex items-center gap-2 px-4">
                      <p className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        {section.label}
                      </p>
                      <Separator className="flex-1" />
                    </div>
                  )}
                  {collapsed && <Separator className="mx-auto my-2 w-8" />}
                  <ul className="space-y-0.5 px-2">{section.items.map(renderItem)}</ul>
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
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 transition-opacity duration-150 ease-out lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-[260px] border-r bg-card transition-transform duration-150 ease-out lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
        role="navigation"
      >
        {content}
      </aside>

      <aside
        className="hidden h-dvh border-r bg-card transition-[width] duration-150 ease-out lg:block"
        style={{
          width: collapsed ? "var(--sidebar-collapsed-width)" : "var(--sidebar-width)",
        }}
        role="navigation"
      >
        {content}
      </aside>
    </>
  );
}
