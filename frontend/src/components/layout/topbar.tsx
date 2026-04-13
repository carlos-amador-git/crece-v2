"use client";

import { useAuth } from "@/lib/auth";
import { useSidebarStore } from "@/lib/store";
import { useAlerts } from "@/lib/api/hooks/use-overview";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Bell,
  Search,
  Menu,
  Moon,
  Sun,
  LogOut,
  User,
  ChevronRight,
} from "lucide-react";
import { useState, useEffect, useCallback, Fragment } from "react";

/** Map pathname segments to human-readable labels */
const segmentLabels: Record<string, string> = {
  dashboard: "Dashboard",
  dirigentes: "Dirigentes",
  social: "Social",
  electoral: "Electoral",
  benchmark: "Benchmarks",
  planes: "Planes IA",
  settings: "Configuracion",
};

/** Map role keys to display labels */
const roleLabels: Record<string, string> = {
  admin: "Administrador",
  analyst: "Analista",
  field_operator: "Operador de Campo",
  viewer: "Visor",
};

function useBreadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  return segments.map((seg, i) => ({
    label: segmentLabels[seg] ?? seg.charAt(0).toUpperCase() + seg.slice(1),
    href: "/" + segments.slice(0, i + 1).join("/"),
    isLast: i === segments.length - 1,
  }));
}

export function Topbar() {
  const { user, logout } = useAuth();
  const { setMobileOpen } = useSidebarStore();
  const breadcrumbs = useBreadcrumbs();
  const [darkMode, setDarkMode] = useState(false);
  const { data: unreadAlerts } = useAlerts(true);
  const hasNotifications = (unreadAlerts?.length ?? 0) > 0;

  useEffect(() => {
    const stored = localStorage.getItem("crece_theme");
    if (
      stored === "dark" ||
      (!stored &&
        window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
      setDarkMode(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setDarkMode((prev) => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add("dark");
        localStorage.setItem("crece_theme", "dark");
      } else {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("crece_theme", "light");
      }
      return next;
    });
  }, []);

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((w) => w[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "U";

  const displayRole = user?.role
    ? (roleLabels[user.role] ?? user.role)
    : "Usuario";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-card px-4 lg:px-6">
      {/* Mobile hamburger */}
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="Abrir menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Breadcrumb */}
      <nav
        aria-label="Ubicacion actual"
        className="hidden items-center gap-1 text-sm lg:flex"
      >
        {breadcrumbs.map((crumb, i) => (
          <Fragment key={crumb.href}>
            {i > 0 && (
              <ChevronRight
                className="h-3.5 w-3.5 text-muted-foreground/60"
                aria-hidden="true"
              />
            )}
            {crumb.isLast ? (
              <span className="font-medium text-foreground" aria-current="page">
                {crumb.label}
              </span>
            ) : (
              <span className="text-muted-foreground">{crumb.label}</span>
            )}
          </Fragment>
        ))}
      </nav>

      {/* Search */}
      <div className="relative ml-auto hidden max-w-sm flex-1 sm:block">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Buscar dirigentes, publicaciones..."
          className="pl-9 pr-14"
          aria-label="Buscar"
        />
        <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 select-none rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
          ⌘K
        </kbd>
      </div>

      <div className="flex items-center gap-1">
        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="transition-colors duration-150 ease-out"
          aria-label={
            darkMode ? "Cambiar a modo claro" : "Cambiar a modo oscuro"
          }
        >
          {darkMode ? (
            <Sun className="h-4.5 w-4.5" />
          ) : (
            <Moon className="h-4.5 w-4.5" />
          )}
        </Button>

        {/* Notifications */}
        <Button
          variant="ghost"
          size="icon"
          className="relative transition-colors duration-150 ease-out"
          aria-label={
            hasNotifications
              ? "Notificaciones: hay nuevas"
              : "Notificaciones: sin novedades"
          }
        >
          <Bell className="h-4.5 w-4.5" />
          {hasNotifications && (
            <span
              className="absolute right-2 top-2 h-2 w-2 rounded-full bg-cta"
              aria-hidden="true"
            />
          )}
        </Button>

        <Separator orientation="vertical" className="mx-1 h-6" />

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="relative h-9 w-9 rounded-full transition-colors duration-150 ease-out"
              aria-label="Menu de usuario"
            >
              <Avatar className="h-8 w-8">
                <AvatarImage
                  src={user?.avatar_url}
                  alt={user?.full_name ?? "Usuario"}
                />
                <AvatarFallback className="text-xs font-semibold">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col gap-1.5">
                <p className="text-sm font-medium leading-none">
                  {user?.full_name ?? "Usuario"}
                </p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user?.email ?? ""}
                </p>
                <Badge
                  variant="secondary"
                  className="w-fit text-[10px] font-medium"
                >
                  {displayRole}
                </Badge>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              Perfil
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout}>
              <LogOut className="mr-2 h-4 w-4" />
              Cerrar sesion
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
