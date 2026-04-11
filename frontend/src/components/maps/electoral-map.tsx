"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useElectoralMapStore } from "@/lib/store";
import { MapLegend, INTENTION_LEGEND } from "./map-legend";

const STYLE_URL =
  process.env.NEXT_PUBLIC_MAPLIBRE_STYLE ??
  "https://demotiles.maplibre.org/style.json";

const MVT_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002/api/v1";

interface ElectoralMapProps {
  className?: string;
}

export function ElectoralMap({ className }: ElectoralMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [loaded, setLoaded] = useState(false);
  const { activeLayer, setSelectedSeccion } = useElectoralMapStore();

  useEffect(() => {
    if (!mapContainer.current) return;

    const m = new maplibregl.Map({
      container: mapContainer.current,
      style: STYLE_URL,
      center: [-99.133, 19.432],
      zoom: 5,
      minZoom: 4,
      maxZoom: 16,
      attributionControl: false,
    });

    m.addControl(new maplibregl.NavigationControl(), "top-right");
    m.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right"
    );

    m.on("load", () => {
      m.addSource("electoral-tiles", {
        type: "vector",
        tiles: [`${MVT_BASE}/electoral/mapa/mvt/{z}/{x}/{y}.pbf`],
        minzoom: 4,
        maxzoom: 14,
      });

      m.addLayer({
        id: "secciones-fill",
        type: "fill",
        source: "electoral-tiles",
        "source-layer": "secciones",
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "a_favor"],
            0, "#ef4444",
            30, "#f97316",
            45, "#eab308",
            55, "#84cc16",
            70, "#22c55e",
            100, "#16a34a",
          ],
          "fill-opacity": 0.6,
        },
      });

      m.addLayer({
        id: "secciones-outline",
        type: "line",
        source: "electoral-tiles",
        "source-layer": "secciones",
        paint: {
          "line-color": "hsl(215, 30%, 18%)",
          "line-width": 0.5,
        },
      });

      setLoaded(true);
    });

    m.on("click", "secciones-fill", (e) => {
      if (!e.features || e.features.length === 0) return;
      const feature = e.features[0];
      const props = feature.properties;

      setSelectedSeccion(props?.seccion_id ?? null);

      new maplibregl.Popup({ closeButton: true, maxWidth: "280px" })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="font-family: var(--font-body); font-size: 13px;">
            <strong style="font-family: var(--font-heading);">Seccion ${props?.seccion_id ?? "N/A"}</strong>
            <div style="margin-top: 6px; color: #64748b;">${props?.municipio ?? ""}, ${props?.estado ?? ""}</div>
            <div style="margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; text-align: center;">
              <div>
                <div style="font-weight: 600; color: #22c55e;">${props?.a_favor ?? 0}%</div>
                <div style="font-size: 11px; color: #94a3b8;">A favor</div>
              </div>
              <div>
                <div style="font-weight: 600; color: #eab308;">${props?.indeciso ?? 0}%</div>
                <div style="font-size: 11px; color: #94a3b8;">Indeciso</div>
              </div>
              <div>
                <div style="font-weight: 600; color: #ef4444;">${props?.en_contra ?? 0}%</div>
                <div style="font-size: 11px; color: #94a3b8;">En contra</div>
              </div>
            </div>
          </div>`
        )
        .addTo(m);
    });

    m.on("mouseenter", "secciones-fill", () => {
      m.getCanvas().style.cursor = "pointer";
    });
    m.on("mouseleave", "secciones-fill", () => {
      m.getCanvas().style.cursor = "";
    });

    map.current = m;

    return () => {
      m.remove();
    };
  }, [setSelectedSeccion]);

  useEffect(() => {
    if (!map.current || !loaded) return;
    const m = map.current;

    if (activeLayer === "coverage") {
      m.setPaintProperty("secciones-fill", "fill-color", [
        "interpolate",
        ["linear"],
        ["get", "dirigente_coverage"],
        0, "#1e293b",
        50, "#0ea5e9",
        100, "#06b6d4",
      ]);
    } else if (activeLayer === "penetration") {
      m.setPaintProperty("secciones-fill", "fill-color", [
        "interpolate",
        ["linear"],
        ["get", "social_penetration"],
        0, "#1e293b",
        50, "#8b5cf6",
        100, "#a78bfa",
      ]);
    } else {
      m.setPaintProperty("secciones-fill", "fill-color", [
        "interpolate",
        ["linear"],
        ["get", "a_favor"],
        0, "#ef4444",
        30, "#f97316",
        45, "#eab308",
        55, "#84cc16",
        70, "#22c55e",
        100, "#16a34a",
      ]);
    }
  }, [activeLayer, loaded]);

  return (
    <div className={`relative ${className ?? ""}`}>
      <div ref={mapContainer} className="h-full w-full rounded-lg" />
      <div className="absolute bottom-4 left-4 z-10">
        <MapLegend title="Intencion de Voto" items={INTENTION_LEGEND} />
      </div>
    </div>
  );
}
