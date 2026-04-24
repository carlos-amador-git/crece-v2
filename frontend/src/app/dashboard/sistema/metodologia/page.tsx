import Link from "next/link";
import { ArrowLeft, FileText, Database, Gauge, AlertTriangle, Scale, BookOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const metadata = {
  title: "Metodología · CRECE",
  description: "Cómo se calculan los bloques del Diagnóstico Tier 1 y los Diferenciadores Tier 2.",
};

export default function MetodologiaPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 py-4">
      <header className="flex flex-col gap-2 border-b pb-4">
        <Button variant="ghost" size="sm" asChild className="-ml-2 h-7 w-fit px-2">
          <Link href="/dashboard" className="flex items-center gap-1 text-xs text-muted-foreground">
            <ArrowLeft className="h-3 w-3" aria-hidden="true" />
            Volver al dashboard
          </Link>
        </Button>
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">Metodología</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Cómo se calculan las métricas de tu Diagnóstico y los Diferenciadores. Fuentes, supuestos y rangos de
          referencia aplicados a la política mexicana.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <BookOpen className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Resumen en lenguaje llano
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
          <p>
            CRECE compara tu desempeño digital contra <span className="font-medium text-foreground">otros políticos
            mexicanos</span> de tu mismo tamaño de audiencia, no contra influencers comerciales. La política mexicana
            tiene interacciones sustantivamente menores que el promedio comercial; por eso los umbrales son
            específicos a este contexto.
          </p>
          <p>
            Un bloque en rojo significa que estás por debajo de lo que logran políticos comparables en tu plataforma
            — no que tu cuenta esté "mal" en abstracto. Un bloque en verde significa que estás dentro o por encima
            del rango esperado.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Gauge className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Engagement Rate (ER) y rangos empíricos
          </CardTitle>
          <CardDescription>Aplicado en B01 "Engagement vs. tu estrato", B04 Benchmark, y derivados.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
          <p>
            El <span className="font-medium text-foreground">Engagement Rate</span> es el porcentaje de tu audiencia
            que interactúa con una publicación (likes, comentarios, compartidos ÷ seguidores o alcance, según la
            plataforma).
          </p>
          <p>
            Los rangos de referencia provienen del benchmark empírico <span className="font-mono text-xs">Zenodo v1</span> con
            n=316 observaciones en Nano X (X/Twitter, estrato de audiencia pequeña). Para otras plataformas y
            estratos se usan entre 150–200 observaciones cada uno. Rango observado en política mexicana: 0.01%–1.1%.
          </p>
          <p className="rounded-md border border-border/60 bg-muted/40 p-3 text-xs">
            <span className="font-medium text-foreground">Punto importante:</span> el benchmark comercial de Influencer
            Marketing (Sprout Social · IM Commercial) reporta rangos 3%–7%; la política mexicana cae ~100× por debajo
            en varias celdas. Usar el benchmark comercial como referencia llevaría a marcar casi cualquier cuenta
            política como "roja". Por eso los umbrales de CRECE son específicos al contexto político mexicano.
          </p>
          <p>
            Fuente: <Link href="https://github.com/MarxCha/crece-v2/blob/main/backend/data/zenodo/v1/methodology.md"
            target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:no-underline">
            repositorio con la metodología técnica completa →
            </Link>
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Database className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Fuentes académicas utilizadas
          </CardTitle>
          <CardDescription>Referencias para los bloques específicos del diagnóstico.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-relaxed text-muted-foreground">
          <div className="flex gap-3">
            <Badge variant="outline" className="shrink-0">B02</Badge>
            <div>
              <p className="font-medium text-foreground">Escalón de viralidad (Brookings Breakout Scale)</p>
              <p className="text-xs">
                Escala 1–6 de Brookings Institution para medir viralidad. La escala clasifica contenido desde
                "micro-viral" (Cat 1: cientos de vistas) hasta "viralidad institucional" (Cat 6: millones + cobertura de
                medios). CRECE aplica el mismo criterio adaptado al estrato mexicano.
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <Badge variant="outline" className="shrink-0">B05</Badge>
            <div>
              <p className="font-medium text-foreground">Emociones (Rueda de Plutchik)</p>
              <p className="text-xs">
                Las 6 emociones base provienen del modelo Plutchik (1980): alegría, tristeza, confianza, miedo, enojo,
                anticipación. Se clasifica qué emociones dominantes provoca tu contenido en la audiencia.
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <Badge variant="outline" className="shrink-0">B12</Badge>
            <div>
              <p className="font-medium text-foreground">Detector de coordinación artificial (CIB · ITESO/DFRLab)</p>
              <p className="text-xs">
                Metodología CIB (Coordinated Inauthentic Behaviour) del DFRLab (Atlantic Council) adaptada por el
                ITESO para el contexto mexicano. Detecta patrones de publicación sincronizada y amplificación
                coordinada que sugieren cuentas no orgánicas.
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <Badge variant="outline" className="shrink-0">B06</Badge>
            <div>
              <p className="font-medium text-foreground">Detector de crisis (spike detection)</p>
              <p className="text-xs">
                Detección estadística de outliers sobre el rate de posts tóxicos por hora. Baseline = media móvil de 24h;
                crisis se declara cuando el rate actual supera 3 desviaciones estándar del baseline.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <AlertTriangle className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Limitaciones conocidas
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">Sentimiento sin contexto de afiliación:</span> hoy el
            sentimiento mostrado es crudo — no ajusta si eres oficialismo u oposición. Para un dirigente de
            oposición, una crítica al gobierno se marca como "negativo" aunque en términos políticos suele ser
            positivo para tu narrativa. La aplicación del framework político 3-capas está en plan de corto plazo
            (ventana §9.8 · 2026-05-20).
          </p>
          <p>
            <span className="font-medium text-foreground">Conteos de comentarios/compartidos:</span> algunos scrapers
            no logran leer comentarios y compartidos de ciertas plataformas consistentemente. Un valor de 0 puede
            significar "sin interacciones reales" o "no recolectado". El equipo está diferenciando ambos casos en
            la próxima ventana de mantenimiento.
          </p>
          <p>
            <span className="font-medium text-foreground">Dirigentes plurinominales:</span> cargos sin sección
            electoral asignada muestran un mensaje específico en la pestaña "Electoral". No hay detalle territorial
            porque la Constitución no los liga a un polígono.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Scale className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Gobernanza y trazabilidad
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
          <p>
            Cada cambio en umbrales, fórmulas o reglas queda documentado en el registro de decisiones del proyecto
            (<span className="font-mono text-xs">.context/DECISIONS.md</span>). Los ajustes estructurales se revisan
            en la ventana §9.8 cada 30 días del piloto.
          </p>
          <p>
            Si ves un número que no entiendes o un verdict que no te hace sentido, contacta a tu consultor asignado —
            la honestidad sobre limitaciones es parte de la metodología.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
