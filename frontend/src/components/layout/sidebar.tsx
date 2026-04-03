"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSidebarStore } from "@/lib/store";
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
  Shield,
  X,
} from "lucide-react";

const sections = [
  {
    label: "Principal",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { href: "/dashboard/dirigentes", label: "Dirigentes", icon: Users },
      { href: "/dashboard/social", label: "Social", icon: MessageSquare },
      { href: "/dashboard/electoral", label: "Electoral", icon: Map },
    ],
  },
  {
    label: "Analisis",
    items: [
      { href: "/dashboard/benchmark", label: "Benchmarks", icon: BarChart3 },
      { href: "/dashboard/planes", label: "Planes IA", icon: Brain },
    ],
  },
  {
    label: "Sistema",
    items: [
      { href: "/dashboard/settings", label: "Configuracion", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { collapsed, toggle, mobileOpen, setMobileOpen } = useSidebarStore();

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  const content = (
    <TooltipProvider delayDuration={0}>
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b px-4">
          <Shield className="h-7 w-7 shrink-0 text-accent" />
          {!collapsed && (
            <span className="font-heading text-lg font-bold tracking-tight">
              CRECE
            </span>
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

        {/* Navigation */}
        <ScrollArea className="flex-1 py-4">
          <nav aria-label="Navegacion principal">
            {sections.map((section) => (
              <div key={section.label} className="mb-4">
                {!collapsed && (
                  <p className="mb-1 px-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {section.label}
                  </p>
                )}
                {collapsed && <Separator className="mx-auto my-2 w-8" />}
                <ul className="space-y-0.5 px-2">
                  {section.items.map((item) => {
                    const active = isActive(item.href);
                    const linkContent = (
                      <Link
                        href={item.href}
                        onClick={() => setMobileOpen(false)}
                        className={cn(
                          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                          active
                            ? "bg-accent/10 text-accent"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground",
                          collapsed && "justify-center px-2"
                        )}
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

        {/* Collapse toggle — desktop only */}
        <div className="hidden border-t p-2 lg:block">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-center"
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
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-[260px] border-r bg-card transition-transform duration-300 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        role="navigation"
      >
        {content}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className="hidden h-screen border-r bg-card transition-[width] duration-200 lg:block"
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
