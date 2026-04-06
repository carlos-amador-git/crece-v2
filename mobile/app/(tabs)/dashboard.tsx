/**
 * Dashboard tab — KPIs overview from /dashboard/overview endpoint.
 * Pull-to-refresh, loading skeleton, error/empty states.
 */

import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Colors, Spacing, FontSize, BorderRadius } from "@/constants/theme";

// ── Types ──────────────────────────────────────────────

interface KPI {
  label: string;
  value: number | string;
  trend?: "up" | "down" | "stable";
  unit?: string;
}

interface DashboardOverview {
  kpis?: KPI[];
  total_dirigentes?: number;
  alertas_activas?: number;
  ipd_promedio?: number;
  menciones_hoy?: number;
  encuestas_semana?: number;
  rutas_activas?: number;
  [key: string]: unknown;
}

// ── KPI Card ───────────────────────────────────────────

function KPICard({
  label,
  value,
  color,
  icon,
}: {
  label: string;
  value: string | number;
  color: string;
  icon: React.ComponentProps<typeof Ionicons>["name"];
}) {
  return (
    <View style={styles.kpiCard}>
      <View style={[styles.kpiIconWrap, { backgroundColor: color + "15" }]}>
        <Ionicons name={icon} size={22} color={color} />
      </View>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={[styles.kpiValue, { color }]}>{value}</Text>
    </View>
  );
}

// ── Trend indicator ────────────────────────────────────

function TrendBadge({ trend }: { trend: "up" | "down" | "stable" }) {
  const config = {
    up: { icon: "trending-up" as const, color: Colors.emerald, bg: Colors.emeraldLight },
    down: { icon: "trending-down" as const, color: Colors.error, bg: Colors.errorLight },
    stable: { icon: "remove-outline" as const, color: Colors.gray500, bg: Colors.gray100 },
  };
  const c = config[trend];
  return (
    <View style={[styles.trendBadge, { backgroundColor: c.bg }]}>
      <Ionicons name={c.icon} size={14} color={c.color} />
    </View>
  );
}

// ── Main Component ─────────────────────────────────────

export default function DashboardScreen() {
  const { user, logout } = useAuth();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.get<DashboardOverview>("/api/v1/dashboard/overview");
      setData(res);
      setError(null);
    } catch (err) {
      if (err instanceof Error && "status" in err && (err as any).status === 401) {
        await logout();
        return;
      }
      setError(err instanceof Error ? err.message : "Error al cargar datos");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [logout]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, [fetchData]);

  // Loading state
  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Cargando panel...</Text>
      </View>
    );
  }

  // Error state
  if (error) {
    return (
      <View style={styles.center}>
        <Ionicons name="cloud-offline-outline" size={48} color={Colors.gray300} />
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* Greeting */}
      <Text style={styles.greeting}>
        Hola, {user?.full_name?.split(" ")[0] ?? "Operador"}
      </Text>
      <Text style={styles.date}>
        {new Date().toLocaleDateString("es-MX", {
          weekday: "long",
          day: "numeric",
          month: "long",
        })}
      </Text>

      {/* Primary KPIs */}
      <View style={styles.kpiGrid}>
        <KPICard
          label="Dirigentes"
          value={data?.total_dirigentes ?? "--"}
          color={Colors.primary}
          icon="people-outline"
        />
        <KPICard
          label="Alertas"
          value={data?.alertas_activas ?? "--"}
          color={Colors.error}
          icon="warning-outline"
        />
        <KPICard
          label="IPD Promedio"
          value={
            data?.ipd_promedio != null
              ? `${Number(data.ipd_promedio).toFixed(1)}`
              : "--"
          }
          color={Colors.accent}
          icon="analytics-outline"
        />
        <KPICard
          label="Menciones"
          value={data?.menciones_hoy ?? "--"}
          color={Colors.emerald}
          icon="chatbubbles-outline"
        />
      </View>

      {/* Field KPIs */}
      <Text style={styles.sectionTitle}>Actividad de Campo</Text>
      <View style={styles.kpiGrid}>
        <KPICard
          label="Encuestas/Semana"
          value={data?.encuestas_semana ?? "--"}
          color="#6366f1"
          icon="clipboard-outline"
        />
        <KPICard
          label="Rutas Activas"
          value={data?.rutas_activas ?? "--"}
          color="#ec4899"
          icon="map-outline"
        />
      </View>

      {/* Dynamic KPIs array if the backend sends them */}
      {data?.kpis && data.kpis.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>Metricas Detalladas</Text>
          {data.kpis.map((kpi, i) => (
            <View key={i} style={styles.listCard}>
              <View style={{ flex: 1 }}>
                <Text style={styles.listLabel}>{kpi.label}</Text>
              </View>
              <View style={styles.listRight}>
                <Text style={styles.listValue}>
                  {kpi.value}
                  {kpi.unit ? ` ${kpi.unit}` : ""}
                </Text>
                {kpi.trend && <TrendBadge trend={kpi.trend} />}
              </View>
            </View>
          ))}
        </>
      )}

      <View style={{ height: Spacing.xxl }} />
    </ScrollView>
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
  loadingText: {
    marginTop: Spacing.md,
    color: Colors.gray500,
    fontSize: FontSize.sm,
  },
  errorText: {
    color: Colors.error,
    textAlign: "center",
    padding: Spacing.lg,
    fontSize: FontSize.base,
    marginTop: Spacing.md,
  },
  greeting: {
    fontSize: FontSize.xl,
    fontWeight: "800",
    color: Colors.gray900,
  },
  date: {
    fontSize: FontSize.sm,
    color: Colors.gray500,
    marginTop: Spacing.xs,
    marginBottom: Spacing.lg,
    textTransform: "capitalize",
  },
  sectionTitle: {
    fontSize: FontSize.base,
    fontWeight: "700",
    color: Colors.gray700,
    marginTop: Spacing.lg,
    marginBottom: Spacing.md,
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: Spacing.md,
  },
  kpiCard: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    padding: Spacing.base,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  kpiIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: Spacing.sm,
  },
  kpiLabel: {
    fontSize: FontSize.xs,
    color: Colors.gray500,
    fontWeight: "500",
    marginBottom: Spacing.xs,
  },
  kpiValue: {
    fontSize: FontSize.xxl,
    fontWeight: "800",
  },
  listCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.md,
    padding: Spacing.base,
    marginBottom: Spacing.sm,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 2,
    elevation: 1,
  },
  listLabel: {
    fontSize: FontSize.base,
    color: Colors.gray700,
    fontWeight: "500",
  },
  listRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
  },
  listValue: {
    fontSize: FontSize.base,
    fontWeight: "700",
    color: Colors.gray900,
  },
  trendBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
  },
});
