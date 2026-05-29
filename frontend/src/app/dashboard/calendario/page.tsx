/**
 * /dashboard/calendario — redirect a /dashboard/recomendaciones
 *
 * Opción 4 · 2026-05-12: el catálogo de efemerides se fusionó dentro de
 * Recomendaciones (ProximasFechasStrip) para eliminar duplicación de superficies.
 * Esta página queda como redirect permanente.
 */
import { redirect } from "next/navigation";

export default function CalendarioPage() {
  redirect("/dashboard/recomendaciones");
}
