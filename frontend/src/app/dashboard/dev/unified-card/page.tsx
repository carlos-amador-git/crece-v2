"use client";

/**
 * F1 ruta dev oculta · 2026-05-19
 *
 * Galería visual del UnifiedPostCard en sus 3 variants y 6 estados de datos.
 * Protegida por role check `admin` (otros roles → 404 visible).
 * NO se referencia desde el sidebar. URL directa: /dashboard/dev/unified-card.
 *
 * Sirve como reemplazo de Storybook (no instalado en el repo, per Gemini
 * cross-audit Content Hub F1) para que CEO valide visualmente antes de F2/F3.
 */

import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  UnifiedPostCard,
  UnifiedPostCardSkeleton,
  type PostUnified,
} from "@/components/posts/unified-post-card";

const SAMPLES: Array<{ label: string; post: PostUnified }> = [
  {
    label: "Apify-only · post típico Monitoreo",
    post: {
      id: 5221,
      published_at: "2026-05-08T15:16:42+00:00",
      platform: "FACEBOOK",
      content:
        "⚽ ¡La fiebre mundialista ya se vive con todo! 🔥 Desde Oaxaca nos sumamos al trend y presentamos nuestra estampa #Panini 😎🇲🇽. A solo 34 días del Mundial, ya estamos listos para apoyar con todo a la selección.",
      url: "https://www.facebook.com/saymipinedavelasco/posts/pfbid031aCgWWn3W7rrzLmpndaB3XnQLmJYzvin9GWeXTZtsj8jUmiVxUnshVSLCCgU7AfLl",
      likes_publicos: 2834,
      reactors_capturados: null,
      comments_total: 5,
      shares: 44,
      views: null,
      polaridad_avg: null,
      data_source: "apify",
      handle: "saymipinedavelasco",
    },
  },
  {
    label: "Apify + RADAR (mixto) · cobertura parcial",
    post: {
      id: 5241,
      published_at: "2026-05-06T17:48:01+00:00",
      platform: "FACEBOOK",
      content:
        "Oaxaca se fortalece como sede del turismo deportivo. Muy contenta de reunirme con Rommel Pacheco Marrufo, Director General de la Comisión Nacional de Cultura Física y Deporte (CONADE).",
      url: null,
      likes_publicos: 1268,
      reactors_capturados: 196,
      comments_total: 5,
      shares: 2,
      polaridad_avg: 1.0,
      polaridad_label: "positivo",
      data_source: "mixed",
      handle: "saymipinedavelasco",
    },
  },
  {
    label: "Apify + RADAR + NLP · loser con polaridad negativa",
    post: {
      id: 5081,
      published_at: "2026-05-09T17:00:00+00:00",
      platform: "FACEBOOK",
      content:
        "🏆 ¡Hoy los Alebrijes de Ixcotel se coronaron campeones de la Liga Juvenil Nacional Sub-13! ⚽️ Quiero felicitar con mucho orgullo a mi hijo Gener y a todo este gran equipo.",
      url: null,
      likes_publicos: 918,
      reactors_capturados: 142,
      comments_total: 42,
      shares: 1,
      polaridad_avg: -0.21,
      polaridad_label: "negativo",
      data_source: "mixed",
      handle: "saymipinedavelasco",
    },
  },
];

export default function DevUnifiedCardPage() {
  const { user } = useAuth();
  const role = (user as { role?: string } | null)?.role;
  if (role !== "admin" && role !== "ADMIN") {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <p className="text-sm text-muted-foreground">404 · Página no encontrada</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-heading text-2xl font-bold">UnifiedPostCard · galería dev</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          F1 plan Content Hub · ruta oculta para validación visual CEO antes de
          refactor F2/F3. Sin uso productivo. Acceso solo admin.
        </p>
      </div>

      {(["feed", "ranking", "compact"] as const).map((variant) => (
        <section key={variant} className="space-y-3">
          <h2 className="font-heading text-lg font-semibold capitalize">
            Variant: {variant}
          </h2>
          <div
            className={`grid gap-4 ${
              variant === "compact"
                ? "grid-cols-1 md:grid-cols-3"
                : "grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
            }`}
          >
            {SAMPLES.map(({ label, post }, idx) => (
              <div key={`${variant}-${idx}`} className="space-y-1">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  {label}
                </p>
                <UnifiedPostCard post={post} variant={variant} rank={idx + 1} />
              </div>
            ))}
          </div>
        </section>
      ))}

      <section className="space-y-3">
        <h2 className="font-heading text-lg font-semibold">Skeletons</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <p className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
              feed
            </p>
            <UnifiedPostCardSkeleton variant="feed" />
          </div>
          <div>
            <p className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
              ranking
            </p>
            <UnifiedPostCardSkeleton variant="ranking" />
          </div>
          <div>
            <p className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
              compact
            </p>
            <UnifiedPostCardSkeleton variant="compact" />
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-heading text-lg font-semibold">Empty state</h2>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Card sin datos</CardTitle>
          </CardHeader>
          <CardContent>
            <UnifiedPostCard
              post={{
                id: 0,
                published_at: null,
                platform: "FACEBOOK",
                content: null,
                url: null,
                likes_publicos: null,
                reactors_capturados: null,
                comments_total: null,
                data_source: "unknown",
              }}
            />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
