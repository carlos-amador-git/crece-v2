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

      <Card id="er-mx" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Gauge className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Engagement Rate (ER) y rangos empíricos
          </CardTitle>
          <CardDescription>Aplicado en B01 "Conexión con tu audiencia", B04 "Frente a la competencia", y derivados.</CardDescription>
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
            Detalle de cada bloque del diagnóstico
          </CardTitle>
          <CardDescription>
            Cada card del dashboard tiene un icono ℹ️ que enlaza directo al bloque correspondiente aquí abajo.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5 text-sm leading-relaxed text-muted-foreground">
          <div id="b01" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B01</Badge>
            <div>
              <p className="font-medium text-foreground">Conexión con tu audiencia</p>
              <p className="text-xs">
                Mide qué tanto interactúa tu gente con tus publicaciones (likes, comentarios, compartidos ÷ seguidores
                o alcance, según plataforma). Tu Engagement Rate se compara contra el rango empírico de política
                mexicana (0.01%–1.1%), no contra benchmarks de Influencer Marketing (que sobre-estiman ~100×).
                Ver sección "Engagement Rate (ER) y rangos empíricos" arriba para fuente y metodología completa.
              </p>
            </div>
          </div>
          <div id="b02" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B02</Badge>
            <div>
              <p className="font-medium text-foreground">Alcance fuera de tu red (Brookings Breakout Scale)</p>
              <p className="text-xs">
                Escala 1–6 de Brookings Institution adaptada al estrato mexicano. Mide si tu contenido cruza
                fronteras algorítmicas: del "Base" (cientos de vistas, solo seguidores) al "Global" (millones +
                cobertura de medios). Cada nivel representa un orden de magnitud distinto de alcance no-pagado.
              </p>
            </div>
          </div>
          <div id="b03" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B03</Badge>
            <div>
              <p className="font-medium text-foreground">Salud de tus publicaciones (matriz 2×2)</p>
              <p className="text-xs">
                Cada post se clasifica por dos ejes: <span className="font-medium">engagement</span> (% interacción) y
                <span className="font-medium"> sentimiento</span> (positivo/negativo). Cuatro cuadrantes resultantes:
                <span className="font-medium"> Éxitos</span> (alto engagement + positivo),
                <span className="font-medium"> Riesgos</span> (alto engagement + negativo · estás amplificando crítica),
                <span className="font-medium"> Neutros</span> (alto engagement sin polarizar),
                <span className="font-medium"> Sin Eco</span> (bajo engagement · esfuerzo desperdiciado).
              </p>
            </div>
          </div>
          <div id="b04" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B04</Badge>
            <div>
              <p className="font-medium text-foreground">Frente a la competencia</p>
              <p className="text-xs">
                Comparativa directa de tu engagement contra los competidores configurados para tu org. Ranking ordenado
                por ER promedio del periodo. Los competidores se cargan desde "Configuración → Benchmark"
                (admin) y se actualizan vía scrapers de la plataforma. Si todos los rivales aparecen con datos demo,
                el banner amarillo lo indica explícitamente.
              </p>
            </div>
          </div>
          <div id="b05" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B05</Badge>
            <div>
              <p className="font-medium text-foreground">Sentimiento de la audiencia (Rueda de Plutchik)</p>
              <p className="text-xs">
                Las 6 emociones base provienen del modelo Plutchik (1980): Alegría, Tristeza, Confianza, Miedo, Enojo,
                Anticipación. Se clasifica qué emociones predominan en los comentarios de tu audiencia. El KPI
                principal "Confianza vs Enojo" es la proporción entre ambas — ratio alto = comunidad leal; ratio
                bajo = polarización u hostilidad organizada.
              </p>
            </div>
          </div>
          <div id="b06" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B06</Badge>
            <div>
              <p className="font-medium text-foreground">Semáforo de crisis (detección de spikes)</p>
              <p className="text-xs">
                Detección estadística de outliers sobre el rate de posts/comentarios tóxicos por hora. Baseline = media
                móvil de 24h; alerta se declara cuando el rate actual supera 3 desviaciones estándar del baseline. No
                detecta crítica "normal" — solo picos anómalos que sugieren ataque coordinado o evento de crisis.
              </p>
            </div>
          </div>
          <div id="b07" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B07</Badge>
            <div>
              <p className="font-medium text-foreground">Nuevos seguidores (atribución)</p>
              <p className="text-xs">
                Delta de seguidores en los últimos 14 días, descompuesto por publicación que más contribuyó al
                crecimiento. La atribución usa correlación temporal post→follow + boost de viralidad observado. No es
                causalidad directa, es la mejor aproximación disponible sin acceso a APIs internas de las plataformas.
              </p>
            </div>
          </div>
          <div id="b08" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B08</Badge>
            <div>
              <p className="font-medium text-foreground">Tu peso en la conversación (Share of Voice)</p>
              <p className="text-xs">
                Porcentaje de la conversación pública sobre tu tema principal que te pertenece. Numerador = menciones
                que te citan o respondes. Denominador = total de menciones del tema en el periodo. Útil para detectar
                si dominas o pierdes terreno en temas que defines como propios.
              </p>
            </div>
          </div>
          <div id="b09" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B09</Badge>
            <div>
              <p className="font-medium text-foreground">Poder Viral (ratio shares/likes normalizado)</p>
              <p className="text-xs">
                Mide si tu gente solo da "like" pasivo o realmente comparte tu contenido. Ratio = compartidos ÷ likes,
                normalizado por estrato. Escala cualitativa (1–10) derivada del ratio: alto significa contenido que
                cruza redes orgánicamente, bajo significa audiencia pasiva sin amplificación natural.
              </p>
            </div>
          </div>
          <div id="b10" className="scroll-mt-20 flex gap-3">
            <Badge variant="outline" className="shrink-0">B10</Badge>
            <div>
              <p className="font-medium text-foreground">Tu toque humano (humanización score)</p>
              <p className="text-xs mb-2">
                Score 0–100 que mide qué tan "persona real" vs "comunicación institucional acartonada" se percibe tu
                cuenta. Variables: uso de primera persona, emojis, fotos personales, lenguaje coloquial, narrativa propia.
                Estudios de comunicación política consistentemente muestran que perfiles más humanos generan más
                conexión emocional y engagement orgánico.
              </p>
              <p className="text-xs font-medium text-foreground">Acciones que aumentan el score:</p>
              <ul className="text-xs list-disc list-inside space-y-0.5 pl-1">
                <li>Usar primera persona ("Yo creo...", "Visité...")</li>
                <li>Emojis selectivos (no en exceso)</li>
                <li>Narrativa propia y anécdotas</li>
                <li>Fotos personales (no solo institucionales/eventos)</li>
                <li>Lenguaje coloquial, contracciones, regionalismos</li>
              </ul>
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
