"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapLegend } from "./map-legend";

const STYLE_URL =
  process.env.NEXT_PUBLIC_MAPLIBRE_STYLE ??
  "https://demotiles.maplibre.org/style.json";

// ── Color schemes ──────────────────────────────────────────

const ESTRATO_COLORS: Record<string, string> = {
  "MUY BAJO": "#ef4444",
  BAJO: "#f97316",
  "MEDIO BAJO": "#eab308",
  MEDIO: "#22c55e",
  "MEDIO ALTO/ALTO": "#3b82f6",
};

const PARTICIPACION_COLORS: Record<string, string> = {
  "1": "#ef4444",
  "2": "#eab308",
  "3": "#22c55e",
};

const ESTRATO_LEGEND = [
  { color: "#3b82f6", label: "Medio Alto / Alto" },
  { color: "#22c55e", label: "Medio" },
  { color: "#eab308", label: "Medio Bajo" },
  { color: "#f97316", label: "Bajo" },
  { color: "#ef4444", label: "Muy Bajo" },
];

const PARTICIPACION_LEGEND = [
  { color: "#22c55e", label: "Alto (3)" },
  { color: "#eab308", label: "Medio (2)" },
  { color: "#ef4444", label: "Bajo (1)" },
  { color: "#94a3b8", label: "Sin dato" },
];

// ── Types ──────────────────────────────────────────────────

type ColorMode = "estrato" | "participacion";

interface CanvassingGeoMapProps {
  data: GeoJSON.FeatureCollection | null;
  colorMode?: ColorMode;
  className?: string;
  onFeatureClick?: (properties: Record<string, unknown>) => void;
}

// ── Component ──────────────────────────────────────────────

export function CanvassingGeoMap({
  data,
  colorMode = "estrato",
  className,
  onFeatureClick,
}: CanvassingGeoMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  const buildColorExpression = useCallback(
    (mode: ColorMode): maplibregl.ExpressionSpecification => {
      if (mode === "participacion") {
        return [
          "match",
          ["get", "nivel_participacion"],
          "3", PARTICIPACION_COLORS["3"],
          "2", PARTICIPACION_COLORS["2"],
          "1", PARTICIPACION_COLORS["1"],
          "#94a3b8",
        ];
      }
      return [
        "match",
        ["get", "estrato"],
        "MEDIO ALTO/ALTO", ESTRATO_COLORS["MEDIO ALTO/ALTO"],
        "MEDIO", ESTRATO_COLORS["MEDIO"],
        "MEDIO BAJO", ESTRATO_COLORS["MEDIO BAJO"],
        "BAJO", ESTRATO_COLORS["BAJO"],
        "MUY BAJO", ESTRATO_COLORS["MUY BAJO"],
        "#94a3b8",
      ];
    },
    []
  );

  // Initialize map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const m = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center: [-99.155, 19.42],
      zoom: 11.5,
      minZoom: 9,
      maxZoom: 18,
      attributionControl: false,
    });

    m.addControl(new maplibregl.NavigationControl(), "top-right");
    m.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right"
    );

    m.on("load", () => {
      // Empty source — will be updated when data arrives
      m.addSource("ciudadanos", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      });

      // Cluster circles
      m.addLayer({
        id: "clusters",
        type: "circle",
        source: "ciudadanos",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": [
            "step",
            ["get", "point_count"],
            "#94a3b8",
            20, "#64748b",
            100, "#475569",
            500, "#334155",
          ],
          "circle-radius": [
            "step",
            ["get", "point_count"],
            15,
            20, 20,
            100, 25,
            500, 35,
          ],
          "circle-stroke-width": 2,
          "circle-stroke-color": "hsl(215, 20%, 95%)",
        },
      });

      // Cluster count labels
      m.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "ciudadanos",
        filter: ["has", "point_count"],
        layout: {
          "text-field": "{point_count_abbreviated}",
          "text-size": 12,
        },
        paint: {
          "text-color": "#ffffff",
        },
      });

      // Individual points
      m.addLayer({
        id: "unclustered-point",
        type: "circle",
        source: "ciudadanos",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": buildColorExpression(colorMode),
          "circle-radius": 6,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "hsl(215, 20%, 95%)",
        },
      });

      // Click on cluster to zoom
      m.on("click", "clusters", async (e) => {
        const features = m.queryRenderedFeatures(e.point, {
          layers: ["clusters"],
        });
        if (!features.length) return;
        const clusterId = features[0].properties?.cluster_id;
        const source = m.getSource("ciudadanos") as maplibregl.GeoJSONSource;
        const zoom = await source.getClusterExpansionZoom(clusterId);
        m.easeTo({
          center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
          zoom,
        });
      });

      // Click on point for popup
      m.on("click", "unclustered-point", (e) => {
        if (!e.features || e.features.length === 0) return;
        const props = e.features[0].properties ?? {};
        const coords = (e.features[0].geometry as GeoJSON.Point).coordinates;

        if (popupRef.current) popupRef.current.remove();

        const contactBadge = props.contactado === "SI"
          ? '<span style="color:#22c55e;font-weight:600;">Contactado</span>'
          : props.contactado === "NO"
          ? '<span style="color:#ef4444;">No contactado</span>'
          : '<span style="color:#94a3b8;">Sin info</span>';

        popupRef.current = new maplibregl.Popup({
          closeButton: true,
          maxWidth: "260px",
        })
          .setLngLat(coords as [number, number])
          .setHTML(
            `<div style="font-size:13px;line-height:1.5;">
              <strong>${props.nombre_completo || props.nombre}</strong>
              <div style="color:#64748b;font-size:11px;margin-top:2px;">
                Secc. ${props.seccion || "—"} · ${props.colonia || "—"}
              </div>
              <div style="margin-top:6px;display:grid;grid-template-columns:1fr 1fr;gap:4px;">
                <div><span style="font-size:11px;color:#94a3b8;">Estrato</span><br/><strong>${props.estrato || "—"}</strong></div>
                <div><span style="font-size:11px;color:#94a3b8;">Volatilidad</span><br/><strong>${props.volatilidad ?? "—"}</strong></div>
                <div><span style="font-size:11px;color:#94a3b8;">Edad</span><br/><strong>${props.edad || "—"}</strong></div>
                <div><span style="font-size:11px;color:#94a3b8;">Partic.</span><br/><strong>${props.nivel_participacion || "—"}</strong></div>
              </div>
              <div style="margin-top:6px;text-align:center;">${contactBadge}</div>
            </div>`
          )
          .addTo(m);

        onFeatureClick?.(props);
      });

      // Cursor
      m.on("mouseenter", "clusters", () => {
        m.getCanvas().style.cursor = "pointer";
      });
      m.on("mouseleave", "clusters", () => {
        m.getCanvas().style.cursor = "";
      });
      m.on("mouseenter", "unclustered-point", () => {
        m.getCanvas().style.cursor = "pointer";
      });
      m.on("mouseleave", "unclustered-point", () => {
        m.getCanvas().style.cursor = "";
      });

      setMapLoaded(true);
    });

    mapRef.current = m;

    return () => {
      m.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update data when it changes or map finishes loading
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !mapLoaded) return;
    const source = m.getSource("ciudadanos") as maplibregl.GeoJSONSource | undefined;
    if (!source) return;
    source.setData(data ?? { type: "FeatureCollection", features: [] });
  }, [data, mapLoaded]);

  // Update color mode
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !mapLoaded) return;
    if (!m.getLayer("unclustered-point")) return;
    m.setPaintProperty(
      "unclustered-point",
      "circle-color",
      buildColorExpression(colorMode)
    );
  }, [colorMode, mapLoaded, buildColorExpression]);

  const legend =
    colorMode === "participacion" ? PARTICIPACION_LEGEND : ESTRATO_LEGEND;
  const legendTitle =
    colorMode === "participacion" ? "Nivel Participación" : "Estrato Socioeconómico";

  return (
    <div className={`relative ${className ?? ""}`}>
      <div ref={containerRef} className="h-full w-full rounded-lg" />
      <div className="absolute bottom-4 left-4 z-10">
        <MapLegend title={legendTitle} items={legend} />
      </div>
    </div>
  );
}
