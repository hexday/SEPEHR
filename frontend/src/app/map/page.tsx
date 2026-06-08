// SEPEHR Frontend — Crisis Map Page

"use client";

import { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { BottomNav } from "@/components/layout/BottomNav";
import { get } from "@/lib/api";
import type { MapPoint, MapPointType } from "@/types";

// Leaflet must be loaded client-side only
const MapView = dynamic(() => import("@/components/map/MapView"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 bg-bg-surface flex items-center justify-center">
      <div className="text-center space-y-2">
        <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-primary-subtle">بارگذاری نقشه...</p>
      </div>
    </div>
  ),
});

const POINT_TYPE_LABELS: Record<MapPointType, string> = {
  hospital: "بیمارستان",
  shelter: "پناهگاه",
  aid_center: "مرکز امداد",
  safe_route: "مسیر امن",
  danger_zone: "منطقه خطر",
  checkpoint: "ایست بازرسی",
  water: "آب",
  food: "غذا",
};

const POINT_TYPE_ICONS: Record<MapPointType, string> = {
  hospital: "🏥",
  shelter: "🏠",
  aid_center: "🤝",
  safe_route: "✅",
  danger_zone: "⚠️",
  checkpoint: "🚧",
  water: "💧",
  food: "🍱",
};

const FILTER_TYPES: { type: MapPointType | "all"; label: string; icon: string }[] = [
  { type: "all", label: "همه", icon: "🗺️" },
  { type: "hospital", label: "بیمارستان", icon: "🏥" },
  { type: "shelter", label: "پناهگاه", icon: "🏠" },
  { type: "aid_center", label: "امداد", icon: "🤝" },
  { type: "danger_zone", label: "خطر", icon: "⚠️" },
  { type: "safe_route", label: "مسیر امن", icon: "✅" },
];

export default function MapPage() {
  const [activeFilter, setActiveFilter] = useState<MapPointType | "all">("all");
  const [selectedPoint, setSelectedPoint] = useState<MapPoint | null>(null);

  const { data: allPoints } = useQuery({
    queryKey: ["map-points"],
    queryFn: () => get<MapPoint[]>("/api/v1/map/points"),
    staleTime: 5 * 60 * 1000,
  });

  const filteredPoints =
    activeFilter === "all"
      ? allPoints || []
      : (allPoints || []).filter((p) => p.type === activeFilter);

  return (
    <div className="flex flex-col h-screen bg-bg">
      {/* Header */}
      <div className="px-4 pt-14 pb-3 bg-bg/80 backdrop-blur-xl border-b border-border z-20">
        <h1 className="text-xl font-semibold mb-3">نقشه بحران</h1>

        {/* Filter tabs */}
        <div className="flex gap-2 overflow-x-auto scrollbar-hide -mx-4 px-4 pb-1">
          {FILTER_TYPES.map((f) => (
            <button
              key={f.type}
              onClick={() => setActiveFilter(f.type)}
              className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                activeFilter === f.type
                  ? "bg-accent text-white"
                  : "bg-bg-card text-primary-subtle border border-border"
              }`}
            >
              <span>{f.icon}</span>
              <span>{f.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        <MapView
          points={filteredPoints}
          onPointSelect={setSelectedPoint}
        />

        {/* Point count badge */}
        <div className="absolute top-3 right-3 z-[1000]">
          <div className="glass-card px-3 py-1.5 flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            <span className="text-xs font-medium">{filteredPoints.length} مکان</span>
          </div>
        </div>

        {/* Offline indicator */}
        <div className="absolute top-3 left-3 z-[1000]">
          <div className="glass-card px-3 py-1.5">
            <span className="text-xs text-primary-subtle">آفلاین موجود</span>
          </div>
        </div>
      </div>

      {/* Selected point sheet */}
      {selectedPoint && (
        <div className="absolute bottom-20 left-0 right-0 z-[1001] px-4 animate-slide-up">
          <div className="glass-card p-4">
            <div className="flex items-start gap-3">
              <span className="text-2xl flex-shrink-0">
                {POINT_TYPE_ICONS[selectedPoint.type]}
              </span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{selectedPoint.name}</h3>
                  <span className="text-xs bg-bg-elevated px-2 py-0.5 rounded-full text-primary-subtle">
                    {POINT_TYPE_LABELS[selectedPoint.type]}
                  </span>
                </div>
                {selectedPoint.address && (
                  <p className="text-sm text-primary-subtle mt-1">{selectedPoint.address}</p>
                )}
                {selectedPoint.description && (
                  <p className="text-sm text-primary-subtle mt-1">{selectedPoint.description}</p>
                )}
                {selectedPoint.contact && (
                  <p className="text-sm text-accent mt-1">📞 {selectedPoint.contact}</p>
                )}
              </div>
              <button
                onClick={() => setSelectedPoint(null)}
                className="w-7 h-7 rounded-full bg-bg-elevated flex items-center justify-center flex-shrink-0 text-primary-subtle"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
}
