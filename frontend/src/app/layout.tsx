import type { Metadata } from "next";
import { Instrument_Sans, DM_Sans } from "next/font/google";
import { QueryProvider } from "@/lib/query-provider";
import "./globals.css";

const instrumentSans = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "CRECE v2.0 — Inteligencia Politica",
  description:
    "Plataforma de inteligencia politica: monitoreo social, analisis electoral, benchmarking competitivo y planes estrategicos con IA.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="es"
      suppressHydrationWarning
      className={`${instrumentSans.variable} ${dmSans.variable}`}
    >
      <body className="min-h-screen bg-background font-body antialiased">
        <QueryProvider>{children}</QueryProvider>
        {/* Chatwoot widget — CRECE inbox */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function(d,t) {
                var BASE_URL="https://chatmx.mdconsultoria-ti.org";
                var g=d.createElement(t),s=d.getElementsByTagName(t)[0];
                g.src=BASE_URL+"/packs/js/sdk.js";
                g.defer=true;
                g.async=true;
                s.parentNode.insertBefore(g,s);
                g.onload=function(){
                  window.chatwootSettings = {
                    hideMessageBubble: false,
                    position: "right",
                    locale: "es",
                    type: "standard"
                  };
                  window.chatwootSDK.run({
                    websiteToken: "rVsDDzAbVn8Lq7foP1tHrJAG",
                    baseUrl: BASE_URL
                  });
                }
              })(document,"script");
            `,
          }}
        />
      </body>
    </html>
  );
}
