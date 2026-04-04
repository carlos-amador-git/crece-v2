/**
 * Rutas tab — list assigned canvassing routes with progress,
 * drill into route detail with ordered points and "Mark Visited" action.
 */

import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Modal,
  ScrollView,
  RefreshControl,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api } from "@/lib/api";
import type { RutaCanvassing, PuntoRuta } from "@/lib/types";
import {
  ResultadoVisita,
  ResultadoVisitaLabels,
  type ResultadoVisitaType,
} from "@/constants/enums";
import { Colors, Spacing, FontSize, BorderRadius } from "@/constants/theme";

// ── Helpers ─────────────────────────────────────────────

function progressColor(pct: number): string {
  if (pct >= 80) return Colors.emerald;
  if (pct >= 40) return Colors.warning;
  return Colors.gray300;
}

// ── Mark Visited Modal ──────────────────────────────────

function MarkVisitedModal({
  visible,
  punto,
  rutaId,
  onClose,
  onDone,
}: {
  visible: boolean;
  punto: PuntoRuta | null;
  rutaId: number;
  onClose: () => void;
  onDone: () => void;
}) {
  const [resultado, setResultado] = useState<ResultadoVisitaType>(
    ResultadoVisita.ENCUESTA_COMPLETADA
  );
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!punto) return;
    setSubmitting(true);
    try {
      await api.patch(
        `/api/v1/canvassing/routes/${rutaId}/punto/${punto.id}`,
        { resultado }
      );
      onDone();
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al actualizar";
      Alert.alert("Error", msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={modalStyles.overlay}>
        <View style={modalStyles.sheet}>
          <Text style={modalStyles.title}>Registrar visita</Text>
          {punto && (
            <Text style={modalStyles.subtitle}>
              {punto.ciudadano_nombre ?? `Ciudadano #${punto.ciudadano_id}`}
            </Text>
          )}

          <View style={modalStyles.options}>
            {Object.values(ResultadoVisita).map((opt) => (
              <TouchableOpacity
                key={opt}
                style={[
                  modalStyles.optionBtn,
                  resultado === opt && modalStyles.optionBtnActive,
                ]}
                onPress={() => setResultado(opt)}
                accessibilityRole="radio"
                accessibilityState={{ selected: resultado === opt }}
                accessibilityLabel={ResultadoVisitaLabels[opt]}
              >
                <Text
                  style={[
                    modalStyles.optionText,
                    resultado === opt && modalStyles.optionTextActive,
                  ]}
                >
                  {ResultadoVisitaLabels[opt]}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <View style={modalStyles.actions}>
            <TouchableOpacity
              style={modalStyles.cancelBtn}
              onPress={onClose}
              accessibilityLabel="Cancelar"
            >
              <Text style={modalStyles.cancelText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                modalStyles.confirmBtn,
                submitting && { opacity: 0.7 },
              ]}
              onPress={handleSubmit}
              disabled={submitting}
              accessibilityLabel="Confirmar visita"
            >
              {submitting ? (
                <ActivityIndicator color={Colors.white} size="small" />
              ) : (
                <Text style={modalStyles.confirmText}>Confirmar</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

// ── Main Component ──────────────────────────────────────

export default function RutasScreen() {
  const [rutas, setRutas] = useState<RutaCanvassing[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRuta, setSelectedRuta] = useState<RutaCanvassing | null>(null);
  const [markPunto, setMarkPunto] = useState<PuntoRuta | null>(null);

  const fetchRutas = useCallback(async () => {
    try {
      const data = await api.get<RutaCanvassing[]>(
        "/api/v1/canvassing/routes"
      );
      setRutas(data);
    } catch (err) {
      console.error("Failed to fetch routes:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchRutas();
  }, [fetchRutas]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchRutas();
  }, [fetchRutas]);

  async function fetchRouteDetail(id: number) {
    try {
      const detail = await api.get<RutaCanvassing>(
        `/api/v1/canvassing/routes/${id}`
      );
      setSelectedRuta(detail);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al cargar ruta";
      Alert.alert("Error", msg);
    }
  }

  function handleMarkDone() {
    if (selectedRuta) {
      fetchRouteDetail(selectedRuta.id);
    }
    fetchRutas();
  }

  // ── Route list item ─────────────────────────────────

  function renderRouteItem({ item }: { item: RutaCanvassing }) {
    const pct =
      item.puntos_total > 0
        ? Math.round((item.puntos_completados / item.puntos_total) * 100)
        : 0;

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => fetchRouteDetail(item.id)}
        accessibilityRole="button"
        accessibilityLabel={`Ruta ${item.nombre}, ${pct} por ciento completada`}
      >
        <View style={styles.cardHeader}>
          <Text style={styles.cardTitle} numberOfLines={1}>
            {item.nombre}
          </Text>
          <Text style={[styles.stateBadge, { color: progressColor(pct) }]}>
            {item.estado.replace("_", " ")}
          </Text>
        </View>

        <Text style={styles.cardMeta}>
          {item.fecha_asignada} · {item.puntos_total} puntos
          {item.distancia_total_km != null &&
            ` · ${item.distancia_total_km.toFixed(1)} km`}
        </Text>

        {/* Progress bar */}
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${pct}%`,
                backgroundColor: progressColor(pct),
              },
            ]}
          />
        </View>
        <Text style={styles.progressText}>
          {item.puntos_completados}/{item.puntos_total} visitados ({pct}%)
        </Text>
      </TouchableOpacity>
    );
  }

  // ── Route detail modal ──────────────────────────────

  function renderPuntoItem(punto: PuntoRuta) {
    return (
      <View key={punto.id} style={styles.puntoRow}>
        <View style={styles.puntoOrder}>
          {punto.visitado ? (
            <Ionicons
              name="checkmark-circle"
              size={24}
              color={Colors.emerald}
            />
          ) : (
            <View style={styles.puntoCircle}>
              <Text style={styles.puntoCircleText}>{punto.orden}</Text>
            </View>
          )}
        </View>

        <View style={styles.puntoInfo}>
          <Text
            style={[
              styles.puntoName,
              punto.visitado && styles.puntoNameDone,
            ]}
          >
            {punto.ciudadano_nombre ?? `Ciudadano #${punto.ciudadano_id}`}
          </Text>
          {punto.resultado && (
            <Text style={styles.puntoResultado}>
              {ResultadoVisitaLabels[punto.resultado]}
            </Text>
          )}
        </View>

        {!punto.visitado && (
          <TouchableOpacity
            style={styles.markBtn}
            onPress={() => setMarkPunto(punto)}
            accessibilityRole="button"
            accessibilityLabel={`Marcar visita para ${punto.ciudadano_nombre ?? "ciudadano"}`}
          >
            <Text style={styles.markBtnText}>Visitar</Text>
          </TouchableOpacity>
        )}
      </View>
    );
  }

  // ── Render ──────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={rutas}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderRouteItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="map-outline" size={48} color={Colors.gray300} />
            <Text style={styles.emptyText}>Sin rutas asignadas</Text>
            <Text style={styles.emptySubtext}>
              Las rutas seran asignadas por tu coordinador
            </Text>
          </View>
        }
      />

      {/* Route Detail Modal */}
      <Modal
        visible={selectedRuta !== null}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setSelectedRuta(null)}
      >
        {selectedRuta && (
          <View style={styles.detailContainer}>
            <View style={styles.detailHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.detailTitle}>{selectedRuta.nombre}</Text>
                <Text style={styles.detailMeta}>
                  {selectedRuta.fecha_asignada}
                  {selectedRuta.distancia_total_km != null &&
                    ` · ${selectedRuta.distancia_total_km.toFixed(1)} km`}
                  {selectedRuta.tiempo_estimado_min != null &&
                    ` · ~${selectedRuta.tiempo_estimado_min} min`}
                </Text>
              </View>
              <TouchableOpacity
                onPress={() => setSelectedRuta(null)}
                hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
                accessibilityLabel="Cerrar detalle de ruta"
              >
                <Ionicons name="close" size={28} color={Colors.gray600} />
              </TouchableOpacity>
            </View>

            {/* Progress summary */}
            {selectedRuta.progress && (
              <View style={styles.progressSummary}>
                <Text style={styles.progressSummaryText}>
                  {selectedRuta.progress.completados}/
                  {selectedRuta.progress.total} puntos ·{" "}
                  {Math.round(selectedRuta.progress.porcentaje)}%
                </Text>
                {selectedRuta.progress.distancia_restante_km != null && (
                  <Text style={styles.progressSummaryText}>
                    {selectedRuta.progress.distancia_restante_km.toFixed(1)} km
                    restantes
                  </Text>
                )}
              </View>
            )}

            <ScrollView style={styles.puntosList}>
              {selectedRuta.puntos
                .sort((a, b) => a.orden - b.orden)
                .map(renderPuntoItem)}
              <View style={{ height: Spacing.xxl }} />
            </ScrollView>
          </View>
        )}
      </Modal>

      {/* Mark Visited Bottom Sheet */}
      <MarkVisitedModal
        visible={markPunto !== null}
        punto={markPunto}
        rutaId={selectedRuta?.id ?? 0}
        onClose={() => setMarkPunto(null)}
        onDone={handleMarkDone}
      />
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.gray50,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  list: {
    padding: Spacing.base,
  },
  card: {
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    padding: Spacing.base,
    marginBottom: Spacing.md,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: Spacing.xs,
  },
  cardTitle: {
    fontSize: FontSize.base,
    fontWeight: "700",
    color: Colors.gray800,
    flex: 1,
  },
  stateBadge: {
    fontSize: FontSize.xs,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  cardMeta: {
    fontSize: FontSize.sm,
    color: Colors.gray500,
    marginBottom: Spacing.sm,
  },
  progressBar: {
    height: 6,
    backgroundColor: Colors.gray200,
    borderRadius: 3,
    overflow: "hidden",
    marginBottom: Spacing.xs,
  },
  progressFill: {
    height: "100%",
    borderRadius: 3,
  },
  progressText: {
    fontSize: FontSize.xs,
    color: Colors.gray500,
  },
  empty: {
    alignItems: "center",
    paddingTop: 80,
  },
  emptyText: {
    fontSize: FontSize.lg,
    fontWeight: "600",
    color: Colors.gray500,
    marginTop: Spacing.base,
  },
  emptySubtext: {
    fontSize: FontSize.sm,
    color: Colors.gray400,
    marginTop: Spacing.xs,
    textAlign: "center",
  },
  detailContainer: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  detailHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingHorizontal: Spacing.base,
    paddingTop: Spacing.xl,
    paddingBottom: Spacing.base,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  detailTitle: {
    fontSize: FontSize.xl,
    fontWeight: "800",
    color: Colors.primary,
  },
  detailMeta: {
    fontSize: FontSize.sm,
    color: Colors.gray500,
    marginTop: Spacing.xs,
  },
  progressSummary: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.md,
    backgroundColor: Colors.gray50,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  progressSummaryText: {
    fontSize: FontSize.sm,
    fontWeight: "600",
    color: Colors.gray600,
  },
  puntosList: {
    flex: 1,
    paddingHorizontal: Spacing.base,
  },
  puntoRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray100,
    minHeight: 56,
  },
  puntoOrder: {
    width: 36,
    alignItems: "center",
  },
  puntoCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.gray200,
    justifyContent: "center",
    alignItems: "center",
  },
  puntoCircleText: {
    fontSize: FontSize.xs,
    fontWeight: "700",
    color: Colors.gray600,
  },
  puntoInfo: {
    flex: 1,
    marginLeft: Spacing.md,
  },
  puntoName: {
    fontSize: FontSize.base,
    fontWeight: "600",
    color: Colors.gray800,
  },
  puntoNameDone: {
    color: Colors.gray400,
    textDecorationLine: "line-through",
  },
  puntoResultado: {
    fontSize: FontSize.xs,
    color: Colors.gray500,
    marginTop: 2,
  },
  markBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
    minHeight: 44,
    justifyContent: "center",
  },
  markBtnText: {
    color: Colors.white,
    fontSize: FontSize.sm,
    fontWeight: "700",
  },
});

const modalStyles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  sheet: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    padding: Spacing.lg,
    paddingBottom: Spacing.xxl,
  },
  title: {
    fontSize: FontSize.xl,
    fontWeight: "800",
    color: Colors.primary,
    marginBottom: Spacing.xs,
  },
  subtitle: {
    fontSize: FontSize.base,
    color: Colors.gray600,
    marginBottom: Spacing.base,
  },
  options: {
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  optionBtn: {
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.base,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.gray200,
    backgroundColor: Colors.gray50,
    minHeight: 48,
    justifyContent: "center",
  },
  optionBtnActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primary,
  },
  optionText: {
    fontSize: FontSize.base,
    color: Colors.gray700,
    fontWeight: "500",
  },
  optionTextActive: {
    color: Colors.white,
    fontWeight: "700",
  },
  actions: {
    flexDirection: "row",
    gap: Spacing.md,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: Spacing.md,
    alignItems: "center",
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.gray300,
    minHeight: 48,
    justifyContent: "center",
  },
  cancelText: {
    fontSize: FontSize.base,
    color: Colors.gray600,
    fontWeight: "600",
  },
  confirmBtn: {
    flex: 1,
    paddingVertical: Spacing.md,
    alignItems: "center",
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.emerald,
    minHeight: 48,
    justifyContent: "center",
  },
  confirmText: {
    fontSize: FontSize.base,
    color: Colors.white,
    fontWeight: "700",
  },
});
