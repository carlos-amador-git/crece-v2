"use client";

import { ArrowLeft, ArrowRight, RotateCcw, SkipForward } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Step1Perfil } from "@/components/onboarding/step1-perfil";
import { Step2AccountsManual } from "@/components/onboarding/step2-accounts-manual";
import { Step3SerpOpcional } from "@/components/onboarding/step3-serp-opcional";
import { Step4ValidacionPerfiles } from "@/components/onboarding/step4-validacion-perfiles";
import { Step5ConfirmacionHumana } from "@/components/onboarding/step5-confirmacion-humana";
import { Step6OAuth } from "@/components/onboarding/step6-oauth";
import { Step7Competidores } from "@/components/onboarding/step7-competidores";
import { Step8Promesas } from "@/components/onboarding/step8-promesas";
import { Step9Activacion } from "@/components/onboarding/step9-activacion";
import { Stepper, STEPS } from "@/components/onboarding/stepper";
import {
  useSaveProfile,
  useSaveManualAccounts,
  useConfirmAccounts,
  useSaveCompetidores,
  useSavePromesas,
  useWizardStore,
  type ConfirmedAccount,
} from "@/lib/api/hooks/use-onboarding";

const OPTIONAL_STEPS = new Set([3, 6]);

/**
 * Onboarding wizard S5 · 9 pasos · D-22 · D-23 · D-24.
 *
 * Flujo:
 *   1. Perfil (radio cards)
 *   2. URLs manuales por plataforma
 *   3. SERP asistido (opcional)
 *   4. Validación Apify (auto)
 *   5. Confirmación humana obligatoria (D-23 regla dura)
 *   6. OAuth stubs (opcional, X grayed D-19)
 *   7. Competidores (mínimo 1 · D-22)
 *   8. Promesas (mínimo 1 · D-17)
 *   9. Activación final → POST /onboarding/activate/{id}
 *
 * State persistido en localStorage (zustand middleware) para resistir
 * recargas y retomar donde quedó.
 */
export default function OnboardingWizardPage() {
  const params = useParams<{ dirigenteId: string }>();
  const dirigenteId = Number(params.dirigenteId);

  const {
    currentStep,
    setStep,
    nextStep,
    prevStep,
    setDirigente,
    perfil,
    manualAccounts,
    confirmations,
    validations,
    competidores,
    promesas,
    activated,
    reset,
  } = useWizardStore();

  // Mutations — side-effect al salir del paso guardamos snapshot al backend
  const saveProfile = useSaveProfile(dirigenteId);
  const saveAccounts = useSaveManualAccounts(dirigenteId);
  const confirmAccounts = useConfirmAccounts(dirigenteId);
  const saveCompetidores = useSaveCompetidores(dirigenteId);
  const savePromesas = useSavePromesas(dirigenteId);

  useEffect(() => {
    if (Number.isFinite(dirigenteId)) setDirigente(dirigenteId);
  }, [dirigenteId, setDirigente]);

  const atLeastOneConfirmed = useMemo(
    () => Object.values(confirmations).some(Boolean),
    [confirmations],
  );

  const canProceed = (() => {
    switch (currentStep) {
      case 1:
        return Boolean(perfil);
      case 2:
        return manualAccounts.length > 0;
      case 3:
        return true; // opcional
      case 4:
        return validations.length > 0;
      case 5:
        return atLeastOneConfirmed; // D-23 regla dura
      case 6:
        return true; // opcional
      case 7:
        return competidores.length > 0 && competidores.every((c) => c.full_name);
      case 8:
        return (
          promesas.length > 0 &&
          promesas.every((p) => p.texto_promesa && p.fecha_compromiso)
        );
      case 9:
        return activated;
      default:
        return false;
    }
  })();

  const handleNext = async () => {
    if (!canProceed && currentStep !== 9) return;
    // Persistir paso al backend antes de avanzar
    try {
      if (currentStep === 1 && perfil) await saveProfile.mutateAsync(perfil);
      if (currentStep === 2)
        await saveAccounts.mutateAsync(manualAccounts);
      if (currentStep === 5) {
        const confirmed: ConfirmedAccount[] = validations
          .filter((v) => confirmations[`${v.platform}:${v.handle}`])
          .map((v) => ({
            platform: v.platform,
            url: v.url,
            handle: v.handle,
            confirmed: true as const,
          }));
        await confirmAccounts.mutateAsync(confirmed);
      }
      if (currentStep === 7) await saveCompetidores.mutateAsync(competidores);
      if (currentStep === 8) await savePromesas.mutateAsync(promesas);
    } catch {
      // Seguimos aun si backend falla — estado está en localStorage
    }
    nextStep();
  };

  const handleSkip = () => {
    if (!OPTIONAL_STEPS.has(currentStep)) return;
    nextStep();
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return <Step1Perfil />;
      case 2:
        return <Step2AccountsManual />;
      case 3:
        return <Step3SerpOpcional dirigenteId={dirigenteId} />;
      case 4:
        return <Step4ValidacionPerfiles dirigenteId={dirigenteId} />;
      case 5:
        return <Step5ConfirmacionHumana />;
      case 6:
        return <Step6OAuth dirigenteId={dirigenteId} />;
      case 7:
        return <Step7Competidores />;
      case 8:
        return <Step8Promesas />;
      case 9:
        return <Step9Activacion dirigenteId={dirigenteId} />;
      default:
        return null;
    }
  };

  return (
    <div
      className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6"
      data-testid="page-onboarding-wizard"
    >
      {/* Header */}
      <header className="space-y-1">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Onboarding</span>
          <span aria-hidden>/</span>
          <span>Dirigente #{dirigenteId}</span>
        </div>
        <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          Asistente de activación
        </h1>
        <p className="text-sm text-muted-foreground">
          9 pasos para dejar al dirigente listo para scraping + benchmark. Puedes
          salir y retomar — guardamos el avance automáticamente.
        </p>
      </header>

      {/* Stepper */}
      <Card className="p-4 sm:p-5">
        <Stepper current={currentStep} onStepClick={setStep} />
      </Card>

      {/* Contenido del paso */}
      <Card className="p-4 sm:p-6">{renderStep()}</Card>

      {/* Navegación */}
      <div
        className="sticky bottom-0 z-10 -mx-4 flex items-center justify-between gap-2 border-t bg-background/95 px-4 py-3 backdrop-blur sm:mx-0 sm:rounded-md sm:border sm:px-4"
        data-testid="wizard-nav"
      >
        <Button
          variant="ghost"
          onClick={prevStep}
          disabled={currentStep === 1}
          data-testid="btn-back"
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Atrás
        </Button>

        <div className="flex items-center gap-2">
          {OPTIONAL_STEPS.has(currentStep) && currentStep !== 9 && (
            <Button
              variant="ghost"
              onClick={handleSkip}
              data-testid="btn-skip"
            >
              <SkipForward className="mr-1 h-4 w-4" />
              Saltar
            </Button>
          )}

          {currentStep === 9 ? (
            <Button
              variant="outline"
              onClick={() => {
                reset();
                setStep(1);
              }}
              data-testid="btn-reset"
            >
              <RotateCcw className="mr-1 h-4 w-4" />
              Reiniciar
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              disabled={!canProceed}
              data-testid="btn-next"
            >
              Siguiente
              <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Screenreader-friendly hint of hard-rule blockers */}
      {currentStep === 5 && !atLeastOneConfirmed && (
        <p className="sr-only" role="status">
          No puedes avanzar al siguiente paso sin confirmar al menos una cuenta.
          Regla D-23.
        </p>
      )}

      {/* Fallback nav for bottom of page on long steps */}
      <div className="pb-16" aria-hidden="true" />
    </div>
  );
}
