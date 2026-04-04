/**
 * Encuestas tab — list recent surveys + FAB to create new ones.
 * New survey form: ciudadano search, intencion_voto, nivel_certeza,
 * motivacion, problematicas. Auto-captures GPS on submit.
 */

import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Modal,
  ScrollView,
  RefreshControl,
} from "react-native";
import * as Location from "expo-location";
import { Ionicons } from "@expo/vector-icons";
import { api } from "@/lib/api";
import type { Encuesta, EncuestaCreate, Ciudadano } from "@/lib/types";
import {
  IntencionVoto,
  IntencionVotoLabels,
  NivelCerteza,
  NivelCertezaLabels,
  type IntencionVotoType,
  type NivelCertezaType,
} from "@/constants/enums";
import { Colors, Spacing, FontSize, BorderRadius } from "@/constants/theme";

// ── Helpers ─────────────────────────────────────────────

function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// ── Picker Component ────────────────────────────────────

function OptionPicker<T extends string>({
  label,
  value,
  options,
  labels,
  onChange,
}: {
  label: string;
  value: T;
  options: Record<string, T>;
  labels: Record<T, string>;
  onChange: (v: T) => void;
}) {
  return (
    <View style={styles.fieldGroup}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.optionRow}>
          {Object.values(options).map((opt) => (
            <TouchableOpacity
              key={opt}
              style={[
                styles.optionChip,
                value === opt && styles.optionChipActive,
              ]}
              onPress={() => onChange(opt)}
              accessibilityRole="radio"
              accessibilityState={{ selected: value === opt }}
              accessibilityLabel={labels[opt]}
            >
              <Text
                style={[
                  styles.optionChipText,
                  value === opt && styles.optionChipTextActive,
                ]}
              >
                {labels[opt]}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}

// ── Main Component ──────────────────────────────────────

export default function EncuestasScreen() {
  const [encuestas, setEncuestas] = useState<Encuesta[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);

  // Form state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Ciudadano[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedCiudadano, setSelectedCiudadano] = useState<Ciudadano | null>(
    null
  );
  const [intencionVoto, setIntencionVoto] = useState<IntencionVotoType>(
    IntencionVoto.INDECISO
  );
  const [nivelCerteza, setNivelCerteza] = useState<NivelCertezaType>(
    NivelCerteza.MEDIA
  );
  const [motivacion, setMotivacion] = useState("");
  const [problematicas, setProblematicas] = useState("");
  const [notas, setNotas] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // ── Data fetching ───────────────────────────────────

  const fetchEncuestas = useCallback(async () => {
    try {
      const data = await api.get<Encuesta[]>("/api/v1/encuestas/");
      setEncuestas(data);
    } catch (err) {
      console.error("Failed to fetch encuestas:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchEncuestas();
  }, [fetchEncuestas]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchEncuestas();
  }, [fetchEncuestas]);

  // ── Ciudadano search ────────────────────────────────

  async function handleSearch(query: string) {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const results = await api.get<Ciudadano[]>(
        `/api/v1/ciudadanos/?q=${encodeURIComponent(query)}&limit=10`
      );
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  // ── Submit survey ───────────────────────────────────

  async function handleSubmit() {
    if (!selectedCiudadano) {
      Alert.alert("Error", "Selecciona un ciudadano primero.");
      return;
    }

    setSubmitting(true);

    try {
      // Request GPS
      const { status } = await Location.requestForegroundPermissionsAsync();
      let lat: number | undefined;
      let lon: number | undefined;

      if (status === "granted") {
        const loc = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
        });
        lat = loc.coords.latitude;
        lon = loc.coords.longitude;
      }

      const body: EncuestaCreate = {
        ciudadano_id: selectedCiudadano.id,
        intencion_voto: intencionVoto,
        nivel_certeza: nivelCerteza,
        motivacion: motivacion.trim() || null,
        problematicas_detectadas: problematicas.trim()
          ? [{ descripcion: problematicas.trim() }]
          : null,
        latitud: lat ?? null,
        longitud: lon ?? null,
        fecha_encuesta: todayISO(),
        notas: notas.trim() || null,
      };

      await api.post<Encuesta>("/api/v1/encuestas/", body);

      Alert.alert("Encuesta registrada", "Se guardo correctamente.");
      resetForm();
      setModalVisible(false);
      fetchEncuestas();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Error al guardar encuesta";
      Alert.alert("Error", message);
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setSearchQuery("");
    setSearchResults([]);
    setSelectedCiudadano(null);
    setIntencionVoto(IntencionVoto.INDECISO);
    setNivelCerteza(NivelCerteza.MEDIA);
    setMotivacion("");
    setProblematicas("");
    setNotas("");
  }

  // ── Render ──────────────────────────────────────────

  function renderEncuestaItem({ item }: { item: Encuesta }) {
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.cardTitle}>
            Ciudadano #{item.ciudadano_id}
          </Text>
          <View
            style={[
              styles.badge,
              item.intencion_voto === "mc"
                ? styles.badgeMC
                : styles.badgeDefault,
            ]}
          >
            <Text style={styles.badgeText}>
              {IntencionVotoLabels[item.intencion_voto]}
            </Text>
          </View>
        </View>
        <Text style={styles.cardMeta}>
          {formatDate(item.fecha_encuesta)} · Certeza:{" "}
          {NivelCertezaLabels[item.nivel_certeza]}
        </Text>
        {item.motivacion && (
          <Text style={styles.cardDetail} numberOfLines={2}>
            {item.motivacion}
          </Text>
        )}
      </View>
    );
  }

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
        data={encuestas}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderEncuestaItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons
              name="clipboard-outline"
              size={48}
              color={Colors.gray300}
            />
            <Text style={styles.emptyText}>Sin encuestas registradas</Text>
            <Text style={styles.emptySubtext}>
              Toca el boton + para crear una nueva
            </Text>
          </View>
        }
      />

      {/* FAB */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => setModalVisible(true)}
        accessibilityRole="button"
        accessibilityLabel="Crear nueva encuesta"
      >
        <Ionicons name="add" size={28} color={Colors.white} />
      </TouchableOpacity>

      {/* New Survey Modal */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Nueva Encuesta</Text>
            <TouchableOpacity
              onPress={() => {
                resetForm();
                setModalVisible(false);
              }}
              hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
              accessibilityLabel="Cerrar"
            >
              <Ionicons name="close" size={28} color={Colors.gray600} />
            </TouchableOpacity>
          </View>

          <ScrollView
            style={styles.modalBody}
            keyboardShouldPersistTaps="handled"
          >
            {/* Ciudadano search */}
            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Buscar ciudadano *</Text>
              {selectedCiudadano ? (
                <View style={styles.selectedCiudadano}>
                  <Text style={styles.selectedName}>
                    {selectedCiudadano.nombre}{" "}
                    {selectedCiudadano.apellido_paterno}{" "}
                    {selectedCiudadano.apellido_materno ?? ""}
                  </Text>
                  <TouchableOpacity
                    onPress={() => setSelectedCiudadano(null)}
                    accessibilityLabel="Cambiar ciudadano"
                  >
                    <Ionicons
                      name="close-circle"
                      size={24}
                      color={Colors.gray400}
                    />
                  </TouchableOpacity>
                </View>
              ) : (
                <>
                  <TextInput
                    style={styles.input}
                    placeholder="Nombre o apellido..."
                    placeholderTextColor={Colors.gray400}
                    value={searchQuery}
                    onChangeText={handleSearch}
                    accessibilityLabel="Buscar ciudadano por nombre"
                  />
                  {searching && (
                    <ActivityIndicator
                      size="small"
                      color={Colors.primary}
                      style={{ marginTop: Spacing.sm }}
                    />
                  )}
                  {searchResults.map((c) => (
                    <TouchableOpacity
                      key={c.id}
                      style={styles.searchResult}
                      onPress={() => {
                        setSelectedCiudadano(c);
                        setSearchQuery("");
                        setSearchResults([]);
                      }}
                      accessibilityLabel={`Seleccionar ${c.nombre} ${c.apellido_paterno}`}
                    >
                      <Text style={styles.searchResultText}>
                        {c.nombre} {c.apellido_paterno}{" "}
                        {c.apellido_materno ?? ""}
                      </Text>
                      {c.seccion_electoral && (
                        <Text style={styles.searchResultMeta}>
                          Seccion {c.seccion_electoral}
                        </Text>
                      )}
                    </TouchableOpacity>
                  ))}
                </>
              )}
            </View>

            {/* Intencion de voto */}
            <OptionPicker
              label="Intencion de voto *"
              value={intencionVoto}
              options={IntencionVoto}
              labels={IntencionVotoLabels}
              onChange={setIntencionVoto}
            />

            {/* Nivel de certeza */}
            <OptionPicker
              label="Nivel de certeza"
              value={nivelCerteza}
              options={NivelCerteza}
              labels={NivelCertezaLabels}
              onChange={setNivelCerteza}
            />

            {/* Motivacion */}
            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Motivacion</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                placeholder="Por que vota por este partido?"
                placeholderTextColor={Colors.gray400}
                value={motivacion}
                onChangeText={setMotivacion}
                multiline
                numberOfLines={3}
                accessibilityLabel="Motivacion del voto"
              />
            </View>

            {/* Problematicas */}
            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Problematicas detectadas</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                placeholder="Inseguridad, baches, agua..."
                placeholderTextColor={Colors.gray400}
                value={problematicas}
                onChangeText={setProblematicas}
                multiline
                numberOfLines={2}
                accessibilityLabel="Problematicas de la zona"
              />
            </View>

            {/* Notas */}
            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Notas</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                placeholder="Observaciones adicionales..."
                placeholderTextColor={Colors.gray400}
                value={notas}
                onChangeText={setNotas}
                multiline
                numberOfLines={2}
                accessibilityLabel="Notas adicionales"
              />
            </View>

            {/* Submit */}
            <TouchableOpacity
              style={[styles.submitButton, submitting && styles.buttonDisabled]}
              onPress={handleSubmit}
              disabled={submitting}
              accessibilityRole="button"
              accessibilityLabel="Guardar encuesta"
            >
              {submitting ? (
                <ActivityIndicator color={Colors.white} />
              ) : (
                <Text style={styles.submitButtonText}>
                  Guardar Encuesta
                </Text>
              )}
            </TouchableOpacity>

            <View style={{ height: Spacing.xxl }} />
          </ScrollView>
        </View>
      </Modal>
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
    paddingBottom: 80,
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
  },
  badge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.full,
  },
  badgeMC: {
    backgroundColor: "#fef3c7",
  },
  badgeDefault: {
    backgroundColor: Colors.gray100,
  },
  badgeText: {
    fontSize: FontSize.xs,
    fontWeight: "600",
    color: Colors.gray700,
  },
  cardMeta: {
    fontSize: FontSize.sm,
    color: Colors.gray500,
    marginBottom: Spacing.xs,
  },
  cardDetail: {
    fontSize: FontSize.sm,
    color: Colors.gray600,
    fontStyle: "italic",
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
  },
  fab: {
    position: "absolute",
    right: Spacing.lg,
    bottom: Spacing.lg,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.accent,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: Spacing.base,
    paddingTop: Spacing.xl,
    paddingBottom: Spacing.base,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  modalTitle: {
    fontSize: FontSize.xl,
    fontWeight: "800",
    color: Colors.primary,
  },
  modalBody: {
    flex: 1,
    paddingHorizontal: Spacing.base,
  },
  fieldGroup: {
    marginTop: Spacing.base,
  },
  fieldLabel: {
    fontSize: FontSize.sm,
    fontWeight: "600",
    color: Colors.gray700,
    marginBottom: Spacing.sm,
  },
  input: {
    backgroundColor: Colors.gray50,
    borderWidth: 1,
    borderColor: Colors.gray200,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: FontSize.base,
    color: Colors.gray900,
    minHeight: 48,
  },
  textArea: {
    minHeight: 72,
    textAlignVertical: "top",
  },
  optionRow: {
    flexDirection: "row",
    gap: Spacing.sm,
    paddingVertical: Spacing.xs,
  },
  optionChip: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full,
    borderWidth: 1,
    borderColor: Colors.gray300,
    backgroundColor: Colors.white,
    minHeight: 44,
    justifyContent: "center",
  },
  optionChipActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  optionChipText: {
    fontSize: FontSize.sm,
    color: Colors.gray600,
    fontWeight: "500",
  },
  optionChipTextActive: {
    color: Colors.white,
    fontWeight: "700",
  },
  searchResult: {
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray100,
    minHeight: 48,
    justifyContent: "center",
  },
  searchResultText: {
    fontSize: FontSize.base,
    color: Colors.gray800,
  },
  searchResultMeta: {
    fontSize: FontSize.xs,
    color: Colors.gray400,
    marginTop: 2,
  },
  selectedCiudadano: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: Colors.emeraldLight,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    minHeight: 48,
  },
  selectedName: {
    fontSize: FontSize.base,
    fontWeight: "600",
    color: Colors.gray800,
    flex: 1,
  },
  submitButton: {
    backgroundColor: Colors.emerald,
    borderRadius: BorderRadius.md,
    paddingVertical: Spacing.base,
    alignItems: "center",
    marginTop: Spacing.lg,
    minHeight: 52,
    justifyContent: "center",
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  submitButtonText: {
    color: Colors.white,
    fontSize: FontSize.lg,
    fontWeight: "700",
  },
});
