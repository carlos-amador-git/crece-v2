"use client";

/**
 * D10 ErrorBoundary · 2026-05-19 audit-full
 *
 * Catch de errores de render dentro del subtree. Imprescindible para vistas
 * que dependen de BFF: si /api/v1/posts/unified responde con shape inesperado
 * o el adapter rompe (campo nuevo, null inesperado), el subtree falla sin
 * tumbar toda la app.
 *
 * React 19 sigue requiriendo class component para ErrorBoundary — no hay
 * hook equivalente.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  /** Mensaje custom de fallback (e.g. "No pudimos cargar Top Posts"). */
  fallbackMessage?: string;
  /** Custom render del fallback. Si lo provees, ignora fallbackMessage. */
  fallback?: (error: Error, retry: () => void) => ReactNode;
  /** Callback opcional para telemetry. */
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (this.props.onError) {
      this.props.onError(error, info);
    } else if (typeof window !== "undefined") {
      console.error("[ErrorBoundary]", error, info);
    }
  }

  retry = () => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.retry);
      }
      return (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden="true" />
              Error al cargar esta sección
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {this.props.fallbackMessage ??
                "Algo no salió como esperábamos. El resto de la app sigue funcionando."}
            </p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={this.retry}
              className="gap-2"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Reintentar
            </Button>
          </CardContent>
        </Card>
      );
    }
    return this.props.children;
  }
}
