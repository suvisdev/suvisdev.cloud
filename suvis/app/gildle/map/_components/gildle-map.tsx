"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Tooltip,
  useMap,
} from "react-leaflet"
import "leaflet/dist/leaflet.css"

type ScoredEdge = {
  from_node: string
  to_node: string
  base_distance_m: number
  midpoint_lat: number
  midpoint_lng: number
  road_name: string | null
  tree_score: number
  hazard_score: number
  dog_friendly_score: number
}

type ScoreLayer = "tree" | "hazard" | "dog_friendly"

const YEOUIDO_CENTER: [number, number] = [37.528, 126.933]

const LAYER_CONFIG: Record<
  ScoreLayer,
  { label: string; color: (v: number) => string; key: keyof ScoredEdge }
> = {
  tree: {
    label: "나무 그늘",
    color: (v) => {
      if (v === 0) return "#6b7280"
      if (v < 0.3) return "#86efac"
      if (v < 0.6) return "#22c55e"
      return "#15803d"
    },
    key: "tree_score",
  },
  hazard: {
    label: "결빙 위험",
    color: (v) => {
      if (v === 0) return "#6b7280"
      if (v < 0.3) return "#fca5a5"
      if (v < 0.6) return "#ef4444"
      return "#b91c1c"
    },
    key: "hazard_score",
  },
  dog_friendly: {
    label: "반려견 친화",
    color: (v) => {
      if (v <= 0.3) return "#6b7280"
      if (v < 0.5) return "#93c5fd"
      if (v < 0.7) return "#3b82f6"
      return "#1d4ed8"
    },
    key: "dog_friendly_score",
  },
}

function FitBounds({ edges }: { edges: ScoredEdge[] }) {
  const map = useMap()
  useEffect(() => {
    if (edges.length === 0) return
    const lats = edges.map((e) => e.midpoint_lat)
    const lngs = edges.map((e) => e.midpoint_lng)
    map.fitBounds([
      [Math.min(...lats), Math.min(...lngs)],
      [Math.max(...lats), Math.max(...lngs)],
    ])
  }, [edges, map])
  return null
}

export default function GildleMap() {
  const [edges, setEdges] = useState<ScoredEdge[]>([])
  const [layer, setLayer] = useState<ScoreLayer>("tree")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch("/api/gildle/graph-edges")
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`)
        return res.json()
      })
      .then((data: ScoredEdge[]) => {
        setEdges(data)
        setLoading(false)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "불러오기 실패")
        setLoading(false)
      })
  }, [])

  const cfg = LAYER_CONFIG[layer]
  const nonZero = edges.filter((e) => (e[cfg.key] as number) > 0).length

  return (
    <div className="relative flex h-screen flex-col bg-[#0a0d0a]">
      <header className="z-[1000] flex h-11 shrink-0 items-center justify-between border-b border-white/10 bg-[#0a0d0a]/90 px-4 backdrop-blur">
        <Link
          href="/gildle"
          className="text-xs text-gray-400 transition-colors hover:text-white"
        >
          ← Gildle
        </Link>
        <h1 className="text-sm font-semibold text-emerald-400">
          여의도 보행 그래프
        </h1>
        <span className="text-xs text-gray-500">
          {edges.length > 0 ? `${edges.length} edges` : ""}
        </span>
      </header>

      <div className="z-[1000] flex shrink-0 items-center gap-2 border-b border-white/10 bg-[#0a0d0a]/90 px-4 py-2 backdrop-blur">
        {(Object.entries(LAYER_CONFIG) as [ScoreLayer, (typeof LAYER_CONFIG)[ScoreLayer]][]).map(
          ([key, val]) => (
            <button
              key={key}
              onClick={() => setLayer(key)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                layer === key
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {val.label}
            </button>
          ),
        )}
        <span className="ml-auto text-xs text-gray-500">
          {nonZero > 0 ? `점수 > 0: ${nonZero}개` : ""}
        </span>
      </div>

      {loading && (
        <div className="flex flex-1 items-center justify-center text-gray-400">
          데이터 로딩 중…
        </div>
      )}

      {error && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-red-400">
          <p>데이터 로드 실패: {error}</p>
          <p className="text-xs text-gray-500">
            백엔드 실행 여부 확인: uvicorn main:app --reload
          </p>
        </div>
      )}

      {!loading && !error && (
        <MapContainer
          center={YEOUIDO_CENTER}
          zoom={15}
          className="z-0 flex-1"
          style={{ background: "#1a1a2e" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          <FitBounds edges={edges} />
          {edges.map((edge) => {
            const score = edge[cfg.key] as number
            const color = cfg.color(score)
            const radius = score > 0 ? 3 + score * 4 : 2
            const opacity = score > 0 ? 0.85 : 0.2
            return (
              <CircleMarker
                key={`${edge.from_node}-${edge.to_node}`}
                center={[edge.midpoint_lat, edge.midpoint_lng]}
                radius={radius}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: opacity,
                  weight: 0,
                }}
              >
                <Tooltip>
                  <div className="text-xs">
                    <p className="font-semibold">
                      {edge.road_name ?? "이름 없는 도로"}
                    </p>
                    <p>거리: {edge.base_distance_m.toFixed(0)}m</p>
                    <p>🌳 tree: {edge.tree_score.toFixed(2)}</p>
                    <p>⚠️ hazard: {edge.hazard_score.toFixed(2)}</p>
                    <p>🐕 dog: {edge.dog_friendly_score.toFixed(2)}</p>
                  </div>
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>
      )}

      <div className="z-[1000] flex items-center justify-center gap-4 border-t border-white/10 bg-[#0a0d0a]/90 px-4 py-2 text-[10px] text-gray-500">
        {[
          { color: "#6b7280", label: "0" },
          { color: cfg.color(0.2), label: "~0.3" },
          { color: cfg.color(0.5), label: "~0.6" },
          { color: cfg.color(0.8), label: "~1.0" },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
