"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import { hitlApi } from "@/lib/api/hitl";
import type {
  HitlComment,
  HitlEditPayload,
  HitlPost,
  HitlSampleResponse,
} from "@/lib/api/hitl";
import { ApiError } from "@/lib/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { AlertTriangle, FileSearch, MessageCircle } from "lucide-react";
import {
  EvaluacionConfig,
  type EvaluacionConfigState,
} from "./EvaluacionConfig";
import { CommentsGroupedByPost } from "./CommentsGroupedByPost";
import { PostEvaluator } from "./PostEvaluator";

const DEFAULT_CONFIG: EvaluacionConfigState = {
  days: 90,
  platform: "all",
  scope: "cronologico",
  onlyPending: true,
};

interface RowFeedback {
  saving: boolean;
  error: string | null;
}

export function EvaluacionNlpClient() {
  const { user, isLoading: authLoading } = useAuth();
  const [config, setConfig] = useState<EvaluacionConfigState>(DEFAULT_CONFIG);
  const [sample, setSample] = useState<HitlSampleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rowState, setRowState] = useState<Record<string, RowFeedback>>({});

  // Resolve dirigente_id: VIEWER opera sobre su dirigente (user.dirigente_id).
  // ADMIN/ANALYST también arrancan en su dirigente; expansión multi-actor queda fuera de S4.
  const dirigenteId = user?.dirigente_id ?? null;

  useEffect(() => {
    if (authLoading) return;
    if (!dirigenteId) {
      setLoading(false);
      setLoadError(
        "Tu cuenta no está asociada a un dirigente. Pide al admin asignarte uno."
      );
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    hitlApi
      .getSample({
        dirigente_id: dirigenteId,
        days: config.days,
        platform: config.platform,
        scope: config.scope,
        include_reviewed: !config.onlyPending,
        n_comments: 50,
        n_posts: 20,
      })
      .then((res) => {
        if (!cancelled) setSample(res);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : "Error cargando muestra";
        setLoadError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, dirigenteId, config]);

  const setRowFeedback = (key: string, feedback: RowFeedback) =>
    setRowState((prev) => ({ ...prev, [key]: feedback }));

  // Optimistic helper: applies a server response to the local sample row.
  const applyResponseToComment = (
    id: number,
    patch: Partial<HitlComment>
  ) => {
    setSample((prev) =>
      prev
        ? {
            ...prev,
            comments: prev.comments.map((c) =>
              c.id === id ? { ...c, ...patch } : c
            ),
          }
        : prev
    );
  };

  const applyResponseToPost = (id: number, patch: Partial<HitlPost>) => {
    setSample((prev) =>
      prev
        ? {
            ...prev,
            posts: prev.posts.map((p) =>
              p.id === id ? { ...p, ...patch } : p
            ),
          }
        : prev
    );
  };

  const handleSaveComment = async (id: number, payload: HitlEditPayload) => {
    const key = `comment-${id}`;
    setRowFeedback(key, { saving: true, error: null });
    // Optimistic snapshot for rollback
    const snapshot = sample?.comments.find((c) => c.id === id) ?? null;
    applyResponseToComment(id, {
      ...(payload.tono !== undefined && { nlp_tono: payload.tono }),
      ...(payload.target !== undefined && { nlp_target: payload.target }),
      ...(payload.off_topic !== undefined && { off_topic: payload.off_topic }),
      review_status: "edited",
    });
    try {
      const res = await hitlApi.patchComment(id, payload);
      applyResponseToComment(id, {
        nlp_tono: res.nlp_tono,
        nlp_target: res.nlp_target,
        off_topic: res.off_topic,
        review_status: res.review_status,
        score: res.score,
        last_reviewed_at: res.last_reviewed_at,
        last_reviewed_by: res.last_reviewed_by,
      });
      setRowFeedback(key, { saving: false, error: null });
      bumpProgress(snapshot?.review_status, res.review_status);
    } catch (err) {
      // Rollback
      if (snapshot) applyResponseToComment(id, snapshot);
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Error al guardar";
      setRowFeedback(key, { saving: false, error: msg });
    }
  };

  const handleConfirmComment = async (id: number) => {
    const key = `comment-${id}`;
    setRowFeedback(key, { saving: true, error: null });
    const snapshot = sample?.comments.find((c) => c.id === id) ?? null;
    applyResponseToComment(id, { review_status: "confirmed" });
    try {
      const res = await hitlApi.confirmComment(id);
      applyResponseToComment(id, {
        review_status: res.review_status,
        last_reviewed_at: res.last_reviewed_at,
        last_reviewed_by: res.last_reviewed_by,
      });
      setRowFeedback(key, { saving: false, error: null });
      bumpProgress(snapshot?.review_status, res.review_status);
    } catch (err) {
      if (snapshot) applyResponseToComment(id, snapshot);
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Error al confirmar";
      setRowFeedback(key, { saving: false, error: msg });
    }
  };

  const handleSavePost = async (id: number, payload: HitlEditPayload) => {
    const key = `post-${id}`;
    setRowFeedback(key, { saving: true, error: null });
    const snapshot = sample?.posts.find((p) => p.id === id) ?? null;
    applyResponseToPost(id, {
      ...(payload.tono !== undefined && { nlp_tono: payload.tono }),
      ...(payload.target !== undefined && { nlp_target: payload.target }),
      ...(payload.off_topic !== undefined && { off_topic: payload.off_topic }),
      review_status: "edited",
    });
    try {
      const res = await hitlApi.patchPost(id, payload);
      applyResponseToPost(id, {
        nlp_tono: res.nlp_tono,
        nlp_target: res.nlp_target,
        off_topic: res.off_topic,
        review_status: res.review_status,
        score: res.score,
        last_reviewed_at: res.last_reviewed_at,
        last_reviewed_by: res.last_reviewed_by,
      });
      setRowFeedback(key, { saving: false, error: null });
      bumpProgress(snapshot?.review_status, res.review_status);
    } catch (err) {
      if (snapshot) applyResponseToPost(id, snapshot);
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Error al guardar";
      setRowFeedback(key, { saving: false, error: msg });
    }
  };

  const handleConfirmPost = async (id: number) => {
    const key = `post-${id}`;
    setRowFeedback(key, { saving: true, error: null });
    const snapshot = sample?.posts.find((p) => p.id === id) ?? null;
    applyResponseToPost(id, { review_status: "confirmed" });
    try {
      const res = await hitlApi.confirmPost(id);
      applyResponseToPost(id, {
        review_status: res.review_status,
        last_reviewed_at: res.last_reviewed_at,
        last_reviewed_by: res.last_reviewed_by,
      });
      setRowFeedback(key, { saving: false, error: null });
      bumpProgress(snapshot?.review_status, res.review_status);
    } catch (err) {
      if (snapshot) applyResponseToPost(id, snapshot);
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Error al confirmar";
      setRowFeedback(key, { saving: false, error: msg });
    }
  };

  // Locally bump progress counters when a row transitions from unreviewed → reviewed.
  const bumpProgress = (
    prevStatus: string | null | undefined,
    nextStatus: string
  ) => {
    if (
      (prevStatus === null || prevStatus === undefined || prevStatus === "unreviewed") &&
      (nextStatus === "confirmed" || nextStatus === "edited")
    ) {
      setSample((s) =>
        s
          ? {
              ...s,
              progress: {
                reviewed_total: s.progress.reviewed_total + 1,
                pending_total: Math.max(0, s.progress.pending_total - 1),
              },
            }
          : s
      );
    }
  };

  const totalRows = useMemo(() => {
    if (!sample) return 0;
    return sample.posts.length + sample.comments.length;
  }, [sample]);

  const progressPct = useMemo(() => {
    if (!sample) return 0;
    const { reviewed_total, pending_total } = sample.progress;
    const total = reviewed_total + pending_total;
    if (total === 0) return 0;
    return Math.round((reviewed_total / total) * 100);
  }, [sample]);

  const dirigenteName =
    sample?.dirigente?.full_name ?? user?.full_name ?? "tu dirigente";

  if (authLoading) {
    return <PageSkeleton />;
  }

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-1">
        <h1 className="font-heading text-2xl font-bold tracking-tight">
          Evaluación NLP de tu actividad
        </h1>
        <p className="text-sm text-muted-foreground">
          Hola {dirigenteName}, tienes{" "}
          <span className="font-medium text-foreground tabular-nums">
            {sample?.progress.pending_total ?? 0}
          </span>{" "}
          elementos pendientes de revisar. El sistema propone una clasificación
          y tú confirmas o la corriges.
        </p>
      </header>

      <EvaluacionConfig value={config} onChange={setConfig} />

      {/* Progress bar */}
      <Card>
        <CardContent className="space-y-2 p-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              Progreso · {sample?.progress.reviewed_total ?? 0} revisados /{" "}
              {(sample?.progress.reviewed_total ?? 0) +
                (sample?.progress.pending_total ?? 0)}{" "}
              total
            </span>
            <span className="font-medium text-foreground tabular-nums">
              {progressPct}%
            </span>
          </div>
          <Progress value={progressPct} className="h-2" />
        </CardContent>
      </Card>

      {loadError && (
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <AlertTriangle className="h-5 w-5 text-rose-500" />
            <p className="text-sm text-rose-600 dark:text-rose-400">
              {loadError}
            </p>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <PageSkeleton />
      ) : sample && totalRows === 0 ? (
        <EmptyState />
      ) : sample ? (
        <Tabs defaultValue="comments" className="w-full">
          <TabsList className="h-9 w-full justify-start gap-1 bg-muted/40">
            <TabsTrigger value="comments" className="gap-1.5 text-xs">
              <MessageCircle className="h-3.5 w-3.5" />
              Comentarios
              <span className="ml-1 text-[10px] text-muted-foreground/70">
                {sample.comments.length}
              </span>
            </TabsTrigger>
            <TabsTrigger value="posts" className="gap-1.5 text-xs">
              <FileSearch className="h-3.5 w-3.5" />
              Tus publicaciones
              <span className="ml-1 text-[10px] text-muted-foreground/70">
                {sample.posts.length}
              </span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="comments" className="mt-4">
            <CommentsGroupedByPost
              comments={sample.comments}
              rowState={rowState}
              onSave={handleSaveComment}
              onConfirm={handleConfirmComment}
            />
          </TabsContent>

          <TabsContent value="posts" className="mt-4 space-y-3">
            {sample.posts.length === 0 ? (
              <Card>
                <CardContent className="p-4 text-sm text-muted-foreground">
                  No hay publicaciones pendientes con los filtros actuales.
                </CardContent>
              </Card>
            ) : (
              sample.posts.map((post) => {
                const fb = rowState[`post-${post.id}`];
                return (
                  <PostEvaluator
                    key={`post-${post.id}`}
                    post={post}
                    saving={fb?.saving}
                    error={fb?.error}
                    onSave={handleSavePost}
                    onConfirm={handleConfirmPost}
                  />
                );
              })
            )}
          </TabsContent>
        </Tabs>
      ) : null}
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-10 w-2/3" />
      <Skeleton className="h-24" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-48" />
      <Skeleton className="h-48" />
    </div>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center gap-2 py-12 text-center">
        <FileSearch className="h-10 w-10 text-muted-foreground/50" />
        <p className="text-sm font-medium">No hay elementos pendientes</p>
        <p className="max-w-sm text-xs text-muted-foreground">
          Cambia los filtros (rango, plataforma o desactiva &ldquo;solo
          pendientes&rdquo;) para revisar más actividad.
        </p>
      </CardContent>
    </Card>
  );
}
