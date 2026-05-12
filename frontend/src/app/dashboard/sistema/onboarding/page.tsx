"use client";

import { useAuth } from "@/lib/auth";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { Card, CardContent } from "@/components/ui/card";

export default function OnboardingPage() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="font-heading text-2xl font-bold">Onboarding Político</h1>
        <Card>
          <CardContent className="p-8 text-muted-foreground">Cargando…</CardContent>
        </Card>
      </div>
    );
  }

  if (user?.role !== "admin") {
    return (
      <div className="space-y-4">
        <h1 className="font-heading text-2xl font-bold">Onboarding Político</h1>
        <Card>
          <CardContent className="p-8 text-rose-600">
            Acceso restringido — solo administradores pueden dar de alta nuevos
            políticos.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-heading text-2xl font-bold">Onboarding Político</h1>
        <p className="text-sm text-muted-foreground">
          Alta de un nuevo político en menos de 5 minutos. Crea el usuario, los
          perfiles sociales, y dispara el scraping inicial + análisis NLP + cálculo
          del IPD.
        </p>
      </div>
      <OnboardingWizard />
    </div>
  );
}
