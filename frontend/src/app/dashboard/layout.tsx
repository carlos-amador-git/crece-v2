"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { useSidebarStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

function SyntheticDataBanner() {
  const { activeOrg, user } = useAuth();
  const isAdmin = user?.role === "admin";
  const cfg = (activeOrg as { config?: { has_synthetic_data?: boolean } } | null)?.config;
  if (!cfg?.has_synthetic_data) return null;

  return (
    <div className="flex items-center justify-center gap-2 bg-amber-500/10 px-4 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-400">
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
      DATOS SIMULACION — {activeOrg?.nombre}
      {isAdmin && (
        <span className="text-amber-600/60 dark:text-amber-500/60">
          · los datos de esta org son sinteticos para demo
        </span>
      )}
    </div>
  );
}

function DashboardShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const collapsed = useSidebarStore((s) => s.collapsed);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <p className="text-sm text-muted-foreground">Cargando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Saltar al contenido
      </a>
      <div className="flex h-dvh overflow-hidden">
        <Sidebar />
        <div
          className={cn(
            "flex flex-1 flex-col overflow-hidden transition-[margin-left] duration-200",
            "lg:ml-0"
          )}
        >
          <Topbar />
          <SyntheticDataBanner />
          <main id="main-content" className="flex-1 overflow-y-auto overflow-x-hidden">
            <div className="mx-auto w-full min-w-0 max-w-7xl px-4 py-6 lg:px-6">
              {children}
            </div>
          </main>
        </div>
      </div>
    </>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <DashboardShell>{children}</DashboardShell>
    </AuthProvider>
  );
}
