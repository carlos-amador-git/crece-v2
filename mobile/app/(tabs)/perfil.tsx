/**
 * Perfil tab — user info, role, logout button, sync status placeholder.
 */

import { View, Text, TouchableOpacity, StyleSheet, Alert } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/lib/auth";
import { Colors, Spacing, FontSize, BorderRadius } from "@/constants/theme";

const ROLE_LABELS: Record<string, string> = {
  admin: "Administrador",
  analyst: "Analista",
  field_operator: "Operador de Campo",
  viewer: "Visor",
};

export default function PerfilScreen() {
  const { user, logout } = useAuth();

  async function handleLogout() {
    Alert.alert("Cerrar sesion", "Estas seguro que deseas salir?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Cerrar sesion",
        style: "destructive",
        onPress: async () => {
          await logout();
        },
      },
    ]);
  }

  if (!user) return null;

  return (
    <View style={styles.container}>
      {/* Avatar + name */}
      <View style={styles.profileSection}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {user.full_name
              .split(" ")
              .slice(0, 2)
              .map((w) => w[0])
              .join("")
              .toUpperCase()}
          </Text>
        </View>
        <Text style={styles.name}>{user.full_name}</Text>
        <Text style={styles.role}>
          {ROLE_LABELS[user.role] ?? user.role}
        </Text>
      </View>

      {/* Info cards */}
      <View style={styles.infoSection}>
        <InfoRow
          icon="mail-outline"
          label="Correo"
          value={user.email}
        />
        <InfoRow
          icon="shield-checkmark-outline"
          label="Estado"
          value={user.is_active ? "Activo" : "Inactivo"}
        />
        <InfoRow
          icon="calendar-outline"
          label="Miembro desde"
          value={new Date(user.created_at).toLocaleDateString("es-MX", {
            year: "numeric",
            month: "long",
          })}
        />
      </View>

      {/* Sync status */}
      <View style={styles.syncCard}>
        <Ionicons
          name="cloud-done-outline"
          size={20}
          color={Colors.emerald}
        />
        <Text style={styles.syncText}>Datos sincronizados</Text>
      </View>

      {/* Logout */}
      <TouchableOpacity
        style={styles.logoutBtn}
        onPress={handleLogout}
        accessibilityRole="button"
        accessibilityLabel="Cerrar sesion"
      >
        <Ionicons name="log-out-outline" size={20} color={Colors.error} />
        <Text style={styles.logoutText}>Cerrar sesion</Text>
      </TouchableOpacity>

      <Text style={styles.version}>CRECE Campo v1.0.0</Text>
    </View>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ComponentProps<typeof Ionicons>["name"];
  label: string;
  value: string;
}) {
  return (
    <View style={styles.infoRow}>
      <Ionicons name={icon} size={20} color={Colors.gray400} />
      <View style={styles.infoContent}>
        <Text style={styles.infoLabel}>{label}</Text>
        <Text style={styles.infoValue}>{value}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.gray50,
    paddingHorizontal: Spacing.base,
  },
  profileSection: {
    alignItems: "center",
    paddingTop: Spacing.xl,
    paddingBottom: Spacing.lg,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: Spacing.md,
  },
  avatarText: {
    fontSize: FontSize.xxl,
    fontWeight: "800",
    color: Colors.accent,
  },
  name: {
    fontSize: FontSize.xl,
    fontWeight: "800",
    color: Colors.gray900,
  },
  role: {
    fontSize: FontSize.sm,
    color: Colors.gray500,
    fontWeight: "500",
    marginTop: Spacing.xs,
  },
  infoSection: {
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    padding: Spacing.base,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
    marginBottom: Spacing.base,
  },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray100,
  },
  infoContent: {
    marginLeft: Spacing.md,
    flex: 1,
  },
  infoLabel: {
    fontSize: FontSize.xs,
    color: Colors.gray400,
    fontWeight: "500",
  },
  infoValue: {
    fontSize: FontSize.base,
    color: Colors.gray800,
    fontWeight: "600",
    marginTop: 2,
  },
  syncCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.emeraldLight,
    borderRadius: BorderRadius.md,
    padding: Spacing.base,
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  syncText: {
    fontSize: FontSize.sm,
    fontWeight: "600",
    color: Colors.emerald,
  },
  logoutBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.sm,
    paddingVertical: Spacing.base,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.error,
    backgroundColor: Colors.errorLight,
    minHeight: 52,
  },
  logoutText: {
    fontSize: FontSize.base,
    fontWeight: "700",
    color: Colors.error,
  },
  version: {
    textAlign: "center",
    fontSize: FontSize.xs,
    color: Colors.gray400,
    marginTop: Spacing.xl,
  },
});
