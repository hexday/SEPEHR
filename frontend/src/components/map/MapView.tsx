// SEPEHR Frontend — Leaflet Map Component (client-only)

"use client";

import { useEffect, useRef } from "react";
import type { MapPoint, MapPointType } from "@/types";

interface MapViewProps {
  points: MapPoint[];
  onPointSelect: (point: MapPoint | null) => void;
  center?: [number, number];
  zoom?: number;
}

const POINT_COLORS: Record<MapPointType, string> = {
  hospital: "#34C759",
  shelter: "#4F8CFF",
  aid_center: "#FF8C42",
  safe_route: "#34C759",
  danger_zone: "#FF3B30",
  checkpoint: "#FF8C42",
  water: "#4F8CFF",
  food: "#FF8C42",
};

const POINT_SYMBOLS: Record<MapPointType, string> = {
  hospital: "H",
  shelter: "S",
  aid_center: "A",
  safe_route: "✓",
  danger_zone: "!",
  checkpoint: "C",
  water: "W",
  food: "F",
};

export default function MapView({
  points,
  onPointSelect,
  center = [35.6892, 51.389], // Tehran default
  zoom = 12,
}: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);

  useEffect(() => {
    if (!mapRef.current || leafletMapRef.current) return;

    const initMap = async () => {
      const L = (await import("leaflet")).default;

      // Dark tile layer
      const map = L.map(mapRef.current!, {
        center,
        zoom,
        zoomControl: true,
        attributionControl: false,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "© OpenStreetMap contributors",
      }).addTo(map);

      leafletMapRef.current = map;

      // Click to deselect
      map.on("click", () => onPointSelect(null));
    };

    initMap();

    return () => {
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
      }
    };
  }, []);

  // Update markers when points change
  useEffect(() => {
    const updateMarkers = async () => {
      const map = leafletMapRef.current;
      if (!map) return;

      const L = (await import("leaflet")).default;

      // Remove old markers
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      // Add new markers
      points.forEach((point) => {
        const color = POINT_COLORS[point.type] || "#4F8CFF";
        const symbol = POINT_SYMBOLS[point.type] || "?";

        const icon = L.divIcon({
          html: `
            <div style="
              width: 32px;
              height: 32px;
              border-radius: 50% 50% 50% 0;
              transform: rotate(-45deg);
              background: ${color};
              border: 2px solid rgba(255,255,255,0.3);
              box-shadow: 0 2px 8px rgba(0,0,0,0.4);
              display: flex;
              align-items: center;
              justify-content: center;
            ">
              <span style="
                transform: rotate(45deg);
                color: white;
                font-size: 12px;
                font-weight: bold;
                line-height: 1;
              ">${symbol}</span>
            </div>
          `,
          className: "",
          iconSize: [32, 32],
          iconAnchor: [16, 32],
          popupAnchor: [0, -32],
        });

        const marker = L.marker([point.latitude, point.longitude], { icon }).addTo(map);
        marker.on("click", (e: any) => {
          e.originalEvent.stopPropagation();
          onPointSelect(point);
        });
        markersRef.current.push(marker);
      });
    };

    updateMarkers();
  }, [points]);

  return (
    <div
      ref={mapRef}
      className="w-full h-full"
      style={{ minHeight: "300px" }}
    />
  );
}
