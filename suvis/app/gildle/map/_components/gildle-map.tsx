"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import {
  MapContainer,
  TileLayer,
  Marker,
  Polyline,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

type ScoredEdge = {
  from_node: string
  to_node: string
  base_distance_m: number
  midpoint_lat: number
  midpoint_lng: number
  from_lat: number
  from_lng: number
  to_lat: number
  to_lng: number
  road_name: string | null
  tree_score: number
  hazard_score: number
  dog_friendly_score: number
}

type RouteSegment = {
  from: [number, number]
  to: [number, number]
  edge: ScoredEdge | null
  shade: number | null
}

type ScoreLayer = "tree" | "hazard" | "dog_friendly"
type SeasonMode = "spring_autumn" | "winter_safety" | "summer_shade"

const SEOUL_CENTER: [number, number] = [37.5665, 126.978]

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

const SEASON_CONFIG: Record<SeasonMode, { label: string }> = {
  spring_autumn: { label: "봄/가을 (가로수길)" },
  summer_shade: { label: "여름 (그늘 우선)" },
  winter_safety: { label: "겨울 (결빙 회피)" },
}

function makeIcon(color: string, size: number) {
  return L.divIcon({
    className: "",
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 0 6px rgba(0,0,0,0.5)"></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

const START_ICON = makeIcon("#22c55e", 18)
const END_ICON = makeIcon("#ef4444", 18)

type NominatimResult = {
  place_id: number
  display_name: string
  lat: string
  lon: string
}

function PlaceSearch({
  edges,
  onSelect,
}: {
  edges: ScoredEdge[]
  onSelect: (lat: number, lng: number) => void
}) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<NominatimResult[]>([])
  const [searching, setSearching] = useState(false)
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null)

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node))
        setOpen(false)
    }
    document.addEventListener("mousedown", handleOutside)
    return () => document.removeEventListener("mousedown", handleOutside)
  }, [])

  const search = useCallback(
    (q: string) => {
      if (q.trim().length < 2) {
        setResults([])
        return
      }
      setSearching(true)
      fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&viewbox=126.76,37.70,127.18,37.43&bounded=1&limit=5&accept-language=ko`,
      )
        .then((res) => res.json())
        .then((data: NominatimResult[]) => {
          if (data.length === 0) {
            return fetch(
              `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&countrycodes=kr&limit=5&accept-language=ko`,
            ).then((r) => r.json())
          }
          return data
        })
        .then((data: NominatimResult[]) => {
          setResults(data)
          setOpen(data.length > 0)
          setSearching(false)
        })
        .catch(() => setSearching(false))
    },
    [],
  )

  const handleInput = (value: string) => {
    setQuery(value)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => search(value), 400)
  }

  const handleSelect = (r: NominatimResult) => {
    const lat = parseFloat(r.lat)
    const lng = parseFloat(r.lon)
    const nearest = findNearestNode(lat, lng, edges)
    if (nearest) onSelect(nearest.lat, nearest.lng)
    else onSelect(lat, lng)
    setQuery(r.display_name.split(",")[0])
    setOpen(false)
  }

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => handleInput(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder="장소·주소 검색 (예: 여의도공원)"
        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-gray-200 placeholder:text-gray-500 focus:border-emerald-500/50 focus:outline-none"
      />
      {searching && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-gray-500">
          검색 중…
        </span>
      )}
      {open && results.length > 0 && (
        <ul className="absolute top-full z-[2000] mt-1 w-full rounded-lg border border-white/10 bg-[#151815] shadow-xl">
          {results.map((r) => (
            <li key={r.place_id}>
              <button
                type="button"
                onClick={() => handleSelect(r)}
                className="w-full px-3 py-2 text-left text-xs text-gray-300 hover:bg-white/5"
              >
                {r.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function PanTo({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap()
  useEffect(() => {
    map.setView([lat, lng], Math.max(map.getZoom(), 16))
  }, [lat, lng, map])
  return null
}

function findNearestNode(
  lat: number,
  lng: number,
  edges: ScoredEdge[],
): { nodeId: string; lat: number; lng: number } | null {
  if (edges.length === 0) return null
  let bestDist = Infinity
  let bestNode = ""
  let bestLat = 0
  let bestLng = 0
  for (const e of edges) {
    const dFrom =
      (e.from_lat - lat) ** 2 + (e.from_lng - lng) ** 2
    if (dFrom < bestDist) {
      bestDist = dFrom
      bestNode = e.from_node
      bestLat = e.from_lat
      bestLng = e.from_lng
    }
    const dTo = (e.to_lat - lat) ** 2 + (e.to_lng - lng) ** 2
    if (dTo < bestDist) {
      bestDist = dTo
      bestNode = e.to_node
      bestLat = e.to_lat
      bestLng = e.to_lng
    }
  }
  return { nodeId: bestNode, lat: bestLat, lng: bestLng }
}

function ViewportLoader({
  onMapClick,
  onEdgesLoaded,
  onLoadingChange,
  onError,
}: {
  onMapClick: (lat: number, lng: number) => void
  onEdgesLoaded: (edges: ScoredEdge[]) => void
  onLoadingChange: (loading: boolean) => void
  onError: (msg: string | null) => void
}) {
  const map = useMap()
  const abortRef = useRef<AbortController | null>(null)
  const lastBboxRef = useRef("")

  const loadEdges = useCallback(() => {
    const bounds = map.getBounds()
    const bbox = `${bounds.getSouth().toFixed(4)},${bounds.getWest().toFixed(4)},${bounds.getNorth().toFixed(4)},${bounds.getEast().toFixed(4)},z${map.getZoom()}`
    if (bbox === lastBboxRef.current) return
    lastBboxRef.current = bbox

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    onLoadingChange(true)
    const params = new URLSearchParams({
      south: bounds.getSouth().toFixed(6),
      west: bounds.getWest().toFixed(6),
      north: bounds.getNorth().toFixed(6),
      east: bounds.getEast().toFixed(6),
      zoom: String(map.getZoom()),
    })
    fetch(`/api/gildle/graph-edges?${params}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`)
        return res.json()
      })
      .then((data: ScoredEdge[]) => {
        onEdgesLoaded(data)
        onError(null)
        onLoadingChange(false)
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return
        onError(e instanceof Error ? e.message : "불러오기 실패")
        onLoadingChange(false)
      })
  }, [map, onEdgesLoaded, onLoadingChange, onError])

  useEffect(() => {
    loadEdges()
  }, [loadEdges])

  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng)
    },
    moveend() {
      loadEdges()
    },
    zoomend() {
      loadEdges()
    },
  })
  return null
}

export default function GildleMap() {
  const [edges, setEdges] = useState<ScoredEdge[]>([])
  const [layer, setLayer] = useState<ScoreLayer>("tree")
  const [season, setSeason] = useState<SeasonMode>("spring_autumn")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [startPoint, setStartPoint] = useState<{
    nodeId: string
    lat: number
    lng: number
  } | null>(null)
  const [endPoint, setEndPoint] = useState<{
    nodeId: string
    lat: number
    lng: number
  } | null>(null)
  const [routeSegments, setRouteSegments] = useState<RouteSegment[]>([])
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeError, setRouteError] = useState<string | null>(null)
  const [departureTime, setDepartureTime] = useState<string>(() => {
    const now = new Date()
    return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`
  })
  const [routeShade, setRouteShade] = useState<{
    ratio: number | null
    night: boolean
  } | null>(null)
  const [panTarget, setPanTarget] = useState<{ lat: number; lng: number } | null>(
    null,
  )

  const handleEdgesLoaded = useCallback((data: ScoredEdge[]) => {
    setEdges(data)
  }, [])

  const handleLoadingChange = useCallback((val: boolean) => {
    setLoading(val)
  }, [])

  const handleError = useCallback((msg: string | null) => {
    setError(msg)
  }, [])

  const handleMapClick = useCallback(
    (lat: number, lng: number) => {
      const nearest = findNearestNode(lat, lng, edges)
      if (!nearest) return

      if (!startPoint) {
        setStartPoint(nearest)
        setRouteSegments([])
        setRouteError(null)
      } else if (!endPoint) {
        setEndPoint(nearest)
      } else {
        setStartPoint(nearest)
        setEndPoint(null)
        setRouteSegments([])
        setRouteError(null)
      }
    },
    [edges, startPoint, endPoint],
  )

  const edgeLookup = useMemo(() => {
    const map = new Map<string, ScoredEdge>()
    for (const e of edges) {
      map.set(`${e.from_node}-${e.to_node}`, e)
      map.set(`${e.to_node}-${e.from_node}`, e)
    }
    return map
  }, [edges])

  useEffect(() => {
    if (!startPoint || !endPoint) return
    if (startPoint.nodeId === endPoint.nodeId) return

    setRouteLoading(true)
    setRouteError(null)

    fetch("/api/gildle/navigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start_node: startPoint.nodeId,
        end_node: endPoint.nodeId,
        mode: season,
        ...(season === "summer_shade" ? { departure_time: departureTime } : {}),
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`)
        return res.json()
      })
      .then(
        (data: {
          path: string[]
          coordinates: number[][]
          shade_ratio?: number | null
          edge_shades?: number[] | null
          night?: boolean
        }) => {
        if (data.path.length === 0) {
          setRouteError("경로를 찾을 수 없습니다")
          setRouteSegments([])
        } else {
          const coords: [number, number][] = [
            [startPoint.lat, startPoint.lng],
            ...data.coordinates.map(
              (c) => [c[0], c[1]] as [number, number],
            ),
            [endPoint.lat, endPoint.lng],
          ]
          const numEdges = data.path.length - 1
          const segments: RouteSegment[] = []
          for (let i = 0; i < coords.length - 1; i++) {
            const edgeIdx = Math.min(i, numEdges - 1)
            const key = `${data.path[edgeIdx]}-${data.path[edgeIdx + 1]}`
            segments.push({
              from: coords[i],
              to: coords[i + 1],
              edge: edgeLookup.get(key) ?? null,
              shade: data.edge_shades?.[edgeIdx] ?? null,
            })
          }
          setRouteSegments(segments)
          setRouteShade(
            season === "summer_shade"
              ? { ratio: data.shade_ratio ?? null, night: data.night ?? false }
              : null,
          )
        }
        setRouteLoading(false)
      })
      .catch((e: unknown) => {
        setRouteError(e instanceof Error ? e.message : "경로 조회 실패")
        setRouteLoading(false)
      })
  }, [startPoint, endPoint, season, departureTime, edgeLookup])

  const handleSearchSelect = useCallback(
    (lat: number, lng: number) => {
      setPanTarget({ lat, lng })
      handleMapClick(lat, lng)
    },
    [handleMapClick],
  )

  const handleClear = () => {
    setStartPoint(null)
    setEndPoint(null)
    setRouteSegments([])
    setRouteError(null)
    setRouteShade(null)
  }

  const handleLocate = useCallback(() => {
    if (!("geolocation" in navigator)) {
      setRouteError("이 브라우저에서 위치 서비스를 사용할 수 없습니다")
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords
        setPanTarget({ lat: latitude, lng: longitude })
        const nearest = findNearestNode(latitude, longitude, edges)
        if (nearest) {
          setStartPoint(nearest)
          setEndPoint(null)
          setRouteSegments([])
          setRouteError(null)
        }
      },
      () => {
        setRouteError("위치 권한이 거부되었습니다")
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }, [edges])

  const cfg = LAYER_CONFIG[layer]
  const nonZero = edges.filter((e) => (e[cfg.key] as number) > 0).length

  const routeDistance = useMemo(() => {
    if (routeSegments.length === 0) return 0
    let total = 0
    for (const seg of routeSegments) {
      const [lat1, lng1] = seg.from
      const [lat2, lng2] = seg.to
      const R = 6371000
      const dLat = ((lat2 - lat1) * Math.PI) / 180
      const dLng = ((lng2 - lng1) * Math.PI) / 180
      const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos((lat1 * Math.PI) / 180) *
          Math.cos((lat2 * Math.PI) / 180) *
          Math.sin(dLng / 2) ** 2
      total += R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    }
    return total
  }, [routeSegments])

  const routeSummary = useMemo(() => {
    const withEdge = routeSegments.filter((s) => s.edge !== null)
    if (withEdge.length === 0) return null
    const n = withEdge.length
    return {
      tree: withEdge.reduce((s, seg) => s + seg.edge!.tree_score, 0) / n,
      hazard: withEdge.reduce((s, seg) => s + seg.edge!.hazard_score, 0) / n,
      dog: withEdge.reduce((s, seg) => s + seg.edge!.dog_friendly_score, 0) / n,
    }
  }, [routeSegments])

  const routeDetails = useMemo(() => {
    const withEdge = routeSegments.filter((s) => s.edge !== null)
    if (withEdge.length === 0) return null

    const warnings = withEdge
      .filter((s) => s.edge!.hazard_score >= 0.6)
      .map((s) => s.edge!.road_name ?? "이름 없는 도로")
    const goodShade = withEdge
      .filter((s) => s.edge!.tree_score >= 0.5)
      .map((s) => s.edge!.road_name ?? "이름 없는 도로")

    const roads = withEdge
      .map((s) => s.edge!.road_name)
      .filter((n): n is string => n !== null)
    const uniqueRoads: string[] = []
    for (const r of roads) {
      if (uniqueRoads.at(-1) !== r) uniqueRoads.push(r)
    }

    return {
      hazardRoads: [...new Set(warnings)],
      shadeRoads: [...new Set(goodShade)],
      roadNames: uniqueRoads,
    }
  }, [routeSegments])

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
          서울 보행 그래프
        </h1>
        <span className="text-xs text-gray-500">
          {edges.length > 0 ? `${edges.length} edges` : ""}
        </span>
      </header>

      <div className="z-[1000] flex shrink-0 flex-wrap items-center gap-x-2 gap-y-1.5 border-b border-white/10 bg-[#0a0d0a]/90 px-4 py-2 backdrop-blur">
        <div className="flex w-full items-center gap-1.5 sm:w-auto">
          <div className="flex-1 sm:w-48 sm:flex-none">
            <PlaceSearch edges={edges} onSelect={handleSearchSelect} />
          </div>
          <button
            type="button"
            onClick={handleLocate}
            title="현재 위치"
            className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-gray-400 transition-colors hover:border-emerald-500/50 hover:text-emerald-400"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="4" />
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="2" y1="12" x2="6" y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
            </svg>
          </button>
        </div>

        <div className="flex items-center gap-1">
          {(
            Object.entries(LAYER_CONFIG) as [
              ScoreLayer,
              (typeof LAYER_CONFIG)[ScoreLayer],
            ][]
          ).map(([key, val]) => (
            <button
              key={key}
              onClick={() => setLayer(key)}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors sm:px-3 sm:text-xs ${
                layer === key
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {val.label}
            </button>
          ))}

          <span className="mx-1 h-4 w-px bg-white/10" />

          {(Object.entries(SEASON_CONFIG) as [SeasonMode, { label: string }][]).map(
            ([key, val]) => (
              <button
                key={key}
                onClick={() => setSeason(key)}
                className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors sm:px-3 sm:text-xs ${
                  season === key
                    ? "bg-amber-500/20 text-amber-400"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {val.label}
              </button>
            ),
          )}

          {season === "summer_shade" && (
            <input
              type="time"
              value={departureTime}
              onChange={(e) => setDepartureTime(e.target.value)}
              aria-label="출발 시각"
              className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-amber-300 outline-none sm:text-xs"
            />
          )}
        </div>

        <span className="ml-auto hidden text-xs text-gray-500 sm:inline">
          {nonZero > 0 ? `점수 > 0: ${nonZero}개` : ""}
        </span>
      </div>

      {(startPoint || routeLoading || routeError || routeSegments.length > 0) && (
        <div className="z-[1000] flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 border-b border-white/10 bg-[#0a0d0a]/90 px-4 py-2 backdrop-blur">
          <div className="flex items-center gap-2 text-xs">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: startPoint ? "#22c55e" : "#6b7280" }}
            />
            <span className={startPoint ? "text-green-400" : "text-gray-500"}>
              {startPoint ? "출발" : "지도 클릭"}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: endPoint ? "#ef4444" : "#6b7280" }}
            />
            <span className={endPoint ? "text-red-400" : "text-gray-500"}>
              {endPoint ? "도착" : "지도 클릭"}
            </span>
          </div>

          {routeLoading && (
            <span className="text-xs text-amber-400">경로 계산 중…</span>
          )}
          {routeError && (
            <span className="text-xs text-red-400">{routeError}</span>
          )}
          {routeSegments.length > 0 && (
            <span className="text-xs font-medium text-emerald-400">
              {routeDistance >= 1000
                ? `${(routeDistance / 1000).toFixed(1)}km`
                : `${Math.round(routeDistance)}m`}{" "}
              · {Math.ceil(routeDistance / 67)}분
            </span>
          )}
          {routeShade && !routeShade.night && routeShade.ratio !== null && (
            <span className="text-xs font-medium text-amber-400">
              ☀ 그늘 비율 {Math.round(routeShade.ratio * 100)}%
            </span>
          )}
          {routeShade?.night && (
            <span className="text-xs text-indigo-300">
              🌙 밤 시간대 — 최단 경로로 안내
            </span>
          )}
          {routeSummary && (
            <>
              <span className="hidden h-4 w-px bg-white/10 sm:inline-block" />
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-green-400">
                  나무 {routeSummary.tree.toFixed(2)}
                </span>
                <span className="text-red-400">
                  결빙 {routeSummary.hazard.toFixed(2)}
                </span>
                <span className="text-blue-400">
                  반려견 {routeSummary.dog.toFixed(2)}
                </span>
              </div>
            </>
          )}

          <button
            onClick={handleClear}
            className="ml-auto rounded-full px-3 py-1 text-xs text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
          >
            초기화
          </button>
        </div>
      )}

      {routeDetails && routeSegments.length > 0 && (
        <div className="z-[1000] flex shrink-0 flex-wrap gap-x-4 gap-y-1 border-b border-white/10 bg-[#0a0d0a]/90 px-4 py-1.5 backdrop-blur">
          {routeDetails.roadNames.length > 0 && (
            <p className="w-full text-[11px] text-gray-400">
              <span className="text-gray-500">경유: </span>
              {routeDetails.roadNames.join(" → ")}
            </p>
          )}
          {routeDetails.hazardRoads.length > 0 && (
            <p className="text-[11px] text-red-400/80">
              ⚠ 결빙 주의: {routeDetails.hazardRoads.join(", ")}
            </p>
          )}
          {routeDetails.shadeRoads.length > 0 && (
            <p className="text-[11px] text-green-400/80">
              🌳 그늘 양호: {routeDetails.shadeRoads.join(", ")}
            </p>
          )}
        </div>
      )}

      <div className="relative flex-1">
        {loading && (
          <div className="absolute left-1/2 top-3 z-[1001] -translate-x-1/2 rounded-full bg-[#0a0d0a]/90 px-4 py-1.5 text-xs text-amber-400 backdrop-blur">
            엣지 로딩 중…
          </div>
        )}
        {error && (
          <div className="absolute left-1/2 top-3 z-[1001] -translate-x-1/2 rounded-lg bg-red-950/90 px-4 py-2 text-xs text-red-400 backdrop-blur">
            {error}
          </div>
        )}
        <MapContainer
          center={SEOUL_CENTER}
          zoom={12}
          className="z-0 h-full"
          style={{ background: "#1a1a2e" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          <ViewportLoader
            onMapClick={handleMapClick}
            onEdgesLoaded={handleEdgesLoaded}
            onLoadingChange={handleLoadingChange}
            onError={handleError}
          />
          {panTarget && <PanTo lat={panTarget.lat} lng={panTarget.lng} />}

          {edges.map((edge) => {
            const score = edge[cfg.key] as number
            const color = cfg.color(score)
            const weight = score > 0 ? 2 + score * 3 : 1.5
            const opacity = score > 0 ? 0.8 : 0.15
            return (
              <Polyline
                key={`edge-${edge.from_node}-${edge.to_node}`}
                positions={[
                  [edge.from_lat, edge.from_lng],
                  [edge.to_lat, edge.to_lng],
                ]}
                bubblingMouseEvents
                pathOptions={{ color, weight, opacity }}
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
              </Polyline>
            )
          })}

          {routeSegments.length > 0 && (
            <Polyline
              positions={[
                routeSegments[0].from,
                ...routeSegments.map((s) => s.to),
              ]}
              pathOptions={{ color: "#000", weight: 8, opacity: 0.35 }}
            />
          )}
          {routeSegments.map((seg, i) => {
            // 여름 그늘 모드: 그늘 구간은 초록, 햇빛 구간은 주황으로 구분.
            if (season === "summer_shade" && seg.shade !== null) {
              const color = seg.shade >= 0.6 ? "#22c55e" : "#f59e0b"
              return (
                <Polyline
                  key={`route-${i}`}
                  positions={[seg.from, seg.to]}
                  pathOptions={{ color, weight: 5, opacity: 0.95 }}
                />
              )
            }
            const score = seg.edge
              ? (seg.edge[cfg.key] as number)
              : 0
            const color = score > 0 ? cfg.color(score) : "#facc15"
            return (
              <Polyline
                key={`route-${i}`}
                positions={[seg.from, seg.to]}
                pathOptions={{ color, weight: 5, opacity: 0.95 }}
              />
            )
          })}

          {startPoint && (
            <Marker position={[startPoint.lat, startPoint.lng]} icon={START_ICON}>
              <Tooltip permanent direction="top" offset={[0, -12]}>
                <span className="text-xs font-semibold">출발</span>
              </Tooltip>
            </Marker>
          )}
          {endPoint && (
            <Marker position={[endPoint.lat, endPoint.lng]} icon={END_ICON}>
              <Tooltip permanent direction="top" offset={[0, -12]}>
                <span className="text-xs font-semibold">도착</span>
              </Tooltip>
            </Marker>
          )}
        </MapContainer>
      </div>

      {!routeSegments.length && (
        <div className="z-[1000] flex items-center justify-center border-t border-white/10 bg-[#0a0d0a]/90 px-4 py-2 text-xs text-amber-400/80 backdrop-blur">
          {!startPoint
            ? "지도를 클릭하거나 장소를 검색하여 출발지를 선택하세요"
            : "도착지를 클릭하거나 검색하세요"}
        </div>
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
