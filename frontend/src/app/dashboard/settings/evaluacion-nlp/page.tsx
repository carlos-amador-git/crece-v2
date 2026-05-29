import { EvaluacionNlpClient } from "@/components/evaluacion/EvaluacionNlpClient";

export const metadata = {
  title: "Evaluación NLP · CRECE",
  description:
    "Editor humano-en-el-loop para confirmar o corregir la clasificación NLP del sistema sobre tu actividad en redes.",
};

export default function EvaluacionNlpPage() {
  return <EvaluacionNlpClient />;
}
