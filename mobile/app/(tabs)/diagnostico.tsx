/**
 * Diagnostico tab — shows IPD (Indice de Penetracion Digital) score
 * for the current user's dirigente or a selected one.
 * Calls GET /api/v1/dirigentes/{id}/diagnostico
 */

import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  FlatList,
  Modal,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api } from "@/lib/api";
import { Colors, Spacing, FontSize, BorderRadius } from "@/constants/theme";

// ── Types ──────────────────────────────────────────────

interface Metrica {
  plataforma: string;
  seguidores?: number;
  engagement?: number;
  score?: number;
}

interface Diagnostico {
  ipd_score: number;
  ipd_max?: number;
  dirigente_nombre?: string;
  metricas?: Metrica[];
  recomendaciones?: string[];
  ultima_actualizacion?: string;
  [key: string]: unknown;
}

interface Dirigente {
  id: number;
  nombre: string;
  apellido?: string;
  cargo?: string;
}

// ── IPD Gauge ──────────────────────────────────────────

function IPDGauge({ score, max }: { score: number; max: number }) {
  const pct = Math.min((score / max) * 100, 100);
  const color =
    score >= 7 ? Colors.emerald : score >= 4 ? Colors.accent : Colors.error;
  const label =
    score >= 7 ? "Bueno" : score >= 4 ? "Moderado" : "Bajo";

  return (
    <View style={gaugeStyles.container}>
      <Text style={[gaugeStyles.score, { color }]}>{score.toFixed(1)}</Text>
      <Text style={gaugeStyles.max}>/ {max}</Text>

      {/* Progress bar */}
      <View style={gaugeStyles.bar}>
        <View style={[gaugeStyles.fill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>

      <View style={[gaugeStyles.badge, { backgroundColor: color + "20" }]}>
        <Text style={[gaugeStyles.badgeText, { color }]}>{label}</Text>
      </View>
    </View>
  );
}

const gaugeStyles = StyleSheet.create({
  container: {
    alignItems: "center",
    paddingVertical: Spacing.lg,
  },
  score: {
    fontSize: 56,
    fontWeight: "900",
    lineHeight: 64,
  },
  max: {
    fontSize: FontSize.lg,
    color: Colors.gray400,
    fontWeight: "500",
    marginTop: Spacing.xs,
  },
  bar: {
    width: "100%",
    height: 8,
    backgroundColor: Colors.gray200,
    borderRadius: 4,
    marginTop: Spacing.lg,
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    borderRadius: 4,
  },
  badge: {
    marginTop: Spacing.md,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
  },
  badgeText: {
    fontSize: FontSize.sm,
    fontWeight: "700",
  },
});

// ── Platform icon helper ───────────────────────────────

function platformIcon(name: string): React.ComponentProps<typeof Ionicons>["name"] {
  const lower = name.toLowerCase();
  if (lower.includes("twitter") || lower.includes("x")) return "logo-twitter";
  if (lower.includes("instagram")) return "logo-instagram";
  if (lower.includes("facebook")) return "logo-facebook";
  if (lower.includes("tiktok")) return "logo-tiktok";
  if (lower.includes("youtube")) return "logo-youtube";
  if (lower.includes("linkedin")) return "logo-linkedin";
  return "globe-outline";
}

// ── Main Component ─────────────────────────────────────

export default function DiagnosticoScreen() {
  const [dirigentes, setDirigentes] = useState<Dirigente[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [data, setData] = useState<Diagnostico | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pickerVisible, setPickerVisible] = useState(false);

  // Fetch dirigentes list on mount
  useEffect(() => {
    (async () => {
      try {
        const list = await api.get<Dirigente[]>("/api/v1/dirigentes/");
        setDirigentes(list);
        if (list.length > 0 && selectedId === null) {
          setSelectedId(list[0].id);
        }
      } catch {
        // Non-fatal; user can still see diagnostico if they have an ID
      }
    })();
  }, []);

  // Fetch diagnostico when selectedId changes
  const fetchDiagnostico = useCallback(async () => {
    if (selectedId === null) {
      setLoading(false);
      return;
    }
    try {
      const res = await api.get<Diagnostico>(
        `/api/v1/dirigentes/${selectedId}/diagnostico`
      );
      setData(res);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Error al cargar diagnostico"
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedId]);

  useEffect(() => {
    setLoading(true);
    fetchDiagnostico();
  }, [fetchDiagnostico]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDiagnostico();
  }, [fetchDiagnostico]);

  const selectedDirigente = dirigentes.find((d) => d.id === selectedId);

  // Loading
  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  // No dirigentes
  if (dirigentes.length === 0 && !data) {
    return (
      <View style={styles.center}>
        <Ionicons name="person-outline" size={48} color={Colors.gray300} />
        <Text style={styles.emptyText}>Sin dirigentes asignados</Text>
      </View>
    );
  }

  // Error
  if (error && !data) {
    return (
      <View style={styles.center}>
        <Ionicons name="alert-circle-outline" size={48} color={Colors.error} />
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Dirigente picker */}
        {dirigentes.length > 1 && (
          <TouchableOpacity
            style={styles.picker}
            onPress={() => setPickerVisible(true)}
            accessibilityRole="button"
            accessibilityLabel="Seleccionar dirigente"
          >
            <View style={{ flex: 1 }}>
              <Text style={styles.pickerLabel}>Dirigente</Text>
              <Text style={styles.pickerValue}>
                {selectedDirigente
                  ? `${selectedDirigente.nombre}${selectedDirigente.apellido ? ` ${selectedDirigente.apellido}` : ""}`
                  : "Seleccionar..."}
              </Text>
            </View>
            <Ionicons name="chevron-down" size={20} color={Colors.gray400} />
          </TouchableOpacity>
        )}

        {data && (
          <>
            {/* Hero card with IPD score */}
            <View style={styles.heroCard}>
              {data.dirigente_nombre && (
                <Text style={styles.heroName}>{data.dirigente_nombre}</Text>
              )}
              <Text style={styles.heroTitle}>
                Indice de Penetracion Digital
              </Text>
              <IPDGauge score={data.ipd_score} max={data.ipd_max ?? 10} />
              {data.ultima_actualizacion && (
                <Text style={styles.heroUpdated}>
                  Actualizado:{" "}
                  {new Date(data.ultima_actualizacion).toLocaleDateString(
                    "es-MX",
                    { day: "numeric", month: "short", year: "numeric" }
                  )}
                </Text>
              )}
            </View>

            {/* Metricas por plataforma */}
            {data.metricas && data.metricas.length > 0 && (
              <>
                <Text style={styles.sectionTitle}>
                  Metricas por Plataforma
                </Text>
                {data.metricas.map((m, i) => (
                  <View key={i} style={styles.metricCard}>
                    <View style={styles.metricHeader}>
                      <Ionicons
                        name={platformIcon(m.plataforma)}
                        size={20}
                        color={Colors.primary}
                      />
                      <Text style={styles.metricPlatform}>{m.plataforma}</Text>
                      {m.score != null && (
                        <Text style={styles.metricScore}>
                          {m.score.toFixed(1)}
                        </Text>
                      )}
                    </View>
                    <View style={styles.metricRow}>
                      {m.seguidores != null && (
                        <View style={styles.metricItem}>
                          <Text style={styles.metricLabel}>Seguidores</Text>
                          <Text style={styles.metricValue}>
                            {m.seguidores.toLocaleString()}
                          </Text>
                        </View>
                      )}
                      {m.engagement != null && (
                        <View style={styles.metricItem}>
                          <Text style={styles.metricLabel}>Engagement</Text>
                          <Text style={styles.metricValue}>
                            {(m.engagement * 100).toFixed(1)}%
                          </Text>
                        </View>
                      )}
                    </View>
                  </View>
                ))}
              </>
            )}

            {/* Recomendaciones */}
            {data.recomendaciones && data.recomendaciones.length > 0 && (
              <>
                <Text style={styles.sectionTitle}>Recomendaciones</Text>
                {data.recomendaciones.map((rec, i) => (
                  <View key={i} style={styles.recCard}>
                    <View style={styles.recNumber}>
                      <Text style={styles.recNumberText}>{i + 1}</Text>
                    </View>
                    <Text style={styles.recText}>{rec}</Text>
                  </View>
                ))}
              </>
            )}
          </>
        )}

        <View style={{ height: Spacing.xxl }} />
      </ScrollView>

      {/* Dirigente picker modal */}
      <Modal
        visible={pickerVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setPickerVisible(false)}
      >
        <View style={modalStyles.overlay}>
          <View style={modalStyles.sheet}>
            <View style={modalStyles.header}>
              <Text style={modalStyles.title}>Seleccionar Dirigente</Text>
              <TouchableOpacity
                onPress={() => setPickerVisible(false)}
                hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
                accessibilityLabel="Cerrar selector"
              >
                <Ionicons name="close" size={24} color={Colors.gray600} />
              </TouchableOpacity>
            </View>
            <FlatList
              data={dirigentes}
              keyExtractor={(item) => item.id.toString()}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    modalStyles.option,
                    item.id === selectedId && modalStyles.optionActive,
                  ]}
                  onPress={() => {
                    setSelectedId(item.id);
                    setPickerVisible(false);
                  }}
                  accessibilityLabel={`Seleccionar ${item.nombre}`}
                >
                  <Text
                    style={[
                      modalStyles.optionText,
                      item.id === selectedId && modalStyles.optionTextActive,
                    ]}
                  >
                    {item.nombre}
                    {item.apellido ? ` ${item.apellido}` : ""}
                  </Text>
                  {item.cargo && (
                    <Text style={modalStyles.optionMeta}>{item.cargo}</Text>
                  )}
                  {item.id === selectedId && (
                    <Ionicons
                      name="checkmark"
                      size={20}
                      color={Colors.primary}
                    />
                  )}
                </TouchableOpacity>
              )}
              style={{ maxHeight: 400 }}
            />
          </View>
        </View>
      </Modal>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.gray50,
  },
  content: {
    padding: Spacing.base,
    paddingBottom: Spacing.xxl,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  emptyText: {
    fontSize: FontSize.lg,
    fontWeight: "600",
    color: Colors.gray500,
    marginTop: Spacing.base,
  },
  errorText: {
    color: Colors.error,
    textAlign: "center",
    padding: Spacing.lg,
    fontSize: FontSize.base,
    marginTop: Spacing.md,
  },
  picker: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.md,
    padding: Spacing.base,
    marginBottom: Spacing.base,
    borderWidth: 1,
    borderColor: Colors.gray200,
  },
  pickerLabel: {
    fontSize: FontSize.xs,
    color: Colors.gray500,
    fontWeight: "500",
  },
  pickerValue: {
    fontSize: FontSize.base,
    fontWeight: "700",
    color: Colors.gray800,
    marginTop: 2,
  },
  heroCard: {
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.xl,
    padding: Spacing.lg,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
    marginBottom: Spacing.lg,
  },
  heroName: {
    fontSize: FontSize.lg,
    fontWeight: "700",
    color: Colors.primary,
    textAlign: "center",
  },
  heroTitle: {
    fontSize: FontSize.sm,
    color: Colors.gray500,
    textAlign: "center",
    marginTop: Spacing.xs,
  },
  heroUpdated: {
    fontSize: FontSize.xs,
    color: Colors.gray400,
    textAlign: "center",
    marginTop: Spacing.md,
  },
  sectionTitle: {
    fontSize: FontSize.base,
    fontWeight: "700",
    color: Colors.gray700,
    marginBottom: Spacing.md,
  },
  metricCard: {
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    padding: Spacing.base,
    marginBottom: Spacing.sm,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 2,
    elevation: 1,
  },
  metricHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
    marginBottom: Spacing.sm,
  },
  metricPlatform: {
    fontSize: FontSize.base,
    fontWeight: "600",
    color: Colors.gray800,
    flex: 1,
  },
  metricScore: {
    fontSize: FontSize.lg,
    fontWeight: "800",
    color: Colors.accent,
  },
  metricRow: {
    flexDirection: "row",
    gap: Spacing.xl,
  },
  metricItem: {},
  metricLabel: {
    fontSize: FontSize.xs,
    color: Colors.gray500,
  },
  metricValue: {
    fontSize: FontSize.base,
    fontWeight: "600",
    color: Colors.gray800,
    marginTop: 2,
  },
  recCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.md,
    padding: Spacing.base,
    marginBottom: Spacing.sm,
    gap: Spacing.md,
  },
  recNumber: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  recNumberText: {
    fontSize: FontSize.sm,
    fontWeight: "700",
    color: Colors.accent,
  },
  recText: {
    flex: 1,
    fontSize: FontSize.sm,
    color: Colors.gray700,
    lineHeight: 20,
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
    paddingBottom: Spacing.xxl,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: Spacing.base,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  title: {
    fontSize: FontSize.lg,
    fontWeight: "800",
    color: Colors.primary,
  },
  option: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.base,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray100,
    minHeight: 56,
  },
  optionActive: {
    backgroundColor: Colors.gray50,
  },
  optionText: {
    fontSize: FontSize.base,
    fontWeight: "500",
    color: Colors.gray800,
    flex: 1,
  },
  optionTextActive: {
    fontWeight: "700",
    color: Colors.primary,
  },
  optionMeta: {
    fontSize: FontSize.xs,
    color: Colors.gray400,
    marginRight: Spacing.sm,
  },
});
