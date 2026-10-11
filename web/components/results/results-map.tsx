"use client";

import maplibregl, { Map as MLMap, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import { scoreColor } from "@/lib/ranking";

export type MapPin = {
  listingId: string;
  lat: number;
  lng: number;
  rent: number;
  score: number;
};

export type IsochroneBand = {
  place_label: string;
  mode: string;
  minutes: number;
  geojson: GeoJSON.Feature;
};

const OSM_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

export function ResultsMap({
  pins,
  isochrones,
  showIsochrone,
  selectedId,
  onSelect,
}: {
  pins: MapPin[];
  isochrones: IsochroneBand[];
  showIsochrone: boolean;
  selectedId: string | null;
  onSelect: (listingId: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markersRef = useRef<Map<string, Marker>>(new Map());
  const loadedRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: OSM_STYLE,
      center: [-121.99, 37.36],
      zoom: 11,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      loadedRef.current = true;
      map.addSource("isochrones", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "isochrone-fill",
        type: "fill",
        source: "isochrones",
        paint: { "fill-color": "#0F766E", "fill-opacity": 0.12 },
      });
      map.addLayer({
        id: "isochrone-line",
        type: "line",
        source: "isochrones",
        paint: { "line-color": "#0F766E", "line-opacity": 0.5, "line-width": 1.5 },
      });
    });
    mapRef.current = map;
    const markers = markersRef.current;
    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
      markers.clear();
    };
  }, []);

  // Isochrone overlay
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const source = map.getSource("isochrones") as maplibregl.GeoJSONSource | undefined;
      if (!source) return;
      source.setData({
        type: "FeatureCollection",
        features: showIsochrone ? isochrones.map((band) => band.geojson) : [],
      });
    };
    if (loadedRef.current) apply();
    else map.once("load", apply);
  }, [isochrones, showIsochrone]);

  // Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const existing = markersRef.current;
    const nextIds = new Set(pins.map((p) => p.listingId));
    for (const [id, marker] of existing) {
      if (!nextIds.has(id)) {
        marker.remove();
        existing.delete(id);
      }
    }
    for (const pin of pins) {
      let marker = existing.get(pin.listingId);
      if (!marker) {
        const el = document.createElement("button");
        el.type = "button";
        el.className =
          "rounded-full border border-white/70 px-2 py-0.5 text-[11px] font-semibold text-white shadow-md transition-transform hover:scale-110";
        el.addEventListener("click", () => onSelect(pin.listingId));
        marker = new maplibregl.Marker({ element: el })
          .setLngLat([pin.lng, pin.lat])
          .addTo(map);
        existing.set(pin.listingId, marker);
      }
      const el = marker.getElement() as HTMLButtonElement;
      el.textContent = `$${(pin.rent / 1000).toFixed(1)}k`;
      el.style.backgroundColor = scoreColor(pin.score);
      el.style.outline =
        selectedId === pin.listingId ? "3px solid hsl(var(--accent))" : "none";
      el.setAttribute("aria-label", `Listing at $${pin.rent} per month, score ${Math.round(pin.score)}`);
      marker.setLngLat([pin.lng, pin.lat]);
    }
    if (pins.length > 0) {
      const bounds = new maplibregl.LngLatBounds();
      pins.forEach((p) => bounds.extend([p.lng, p.lat]));
      map.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 400 });
    }
  }, [pins, selectedId, onSelect]);

  return <div ref={containerRef} className="h-full min-h-[420px] w-full rounded-lg border" />;
}
