"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import Script from "next/script"
import { Eraser, Loader2, LocateFixed, Repeat, Search } from "lucide-react"
import { cn } from "@/lib/utils"
import { getSuvisSession } from "@/lib/suvis-session"
import {
  createWalk,
  getRouteOptions,
  getRouteVia,
  planWalk,
  type PetPlaceItem,
  type RouteOption,
  type RouteOptionKind,
  type SeasonMode,
  type WalkPlanResult,
  type WalkPreference,
  type WalkStopCategory,
} from "@/lib/gildle-api"

/**
 * gildle 웹 지도 — Flutter 앱 지도 화면(gildle_map_screen.dart)과 같은 구성(2026-09-28 사용자 결정
 * "웹도 앱이랑 동일하게"): 네이버 지도, 지도 탭으로 출발→도착→경로, 계절 모드 3종, 현재 위치·루프·
 * 지우기 버튼, 하단 결과 카드, 산책 시작(추적·저장). 앱에 없는 장소 검색만 데스크톱용으로 남겼다.
 * 그래프 시각화(레이어 토글·화면 간선)는 없앴다.
 *
 * 루프 버튼은 "시간·거리로 추천"(2026-09-28): "40분 동안 3키로 편하게" 같은 말이나 시간·거리·
 * 선호(편한 길·언덕길·그늘·푸른 길·빠른 길)·들를 곳을 받아, 출발지로 돌아오는 코스를 추천한다.
 * 말은 서버에서 7.8B가 이해하고 규칙이 검증한다(mova 오케스트레이터와 같은 구조).
 */

const NAVER_CLIENT_ID = process.env.NEXT_PUBLIC_NAVER_MAP_CLIENT_ID ?? ""
const SEOUL_CITY_HALL = { lat: 37.5665, lng: 126.978 }
const WALK_SPEED_MPS = 1.2 // 앱과 동일
const TRACK_MIN_STEP_M = 5 // 앱 distanceFilter와 동일
const MAX_WALK_POINTS = 5000 // WalkCreateSchema path 상한
const COLOR_ACCENT = "#34d399" // --gildle-accent (그늘)
const COLOR_WARM = "#d4a574" // --gildle-warm (햇빛)
const COLOR_MUTED = "#9ca3af"
// 경로 후보 색 — 빠른 길(파랑)·그늘(초록 accent)·푸른 길(연두)·편한 길(하늘)·언덕길(주황)·들렀다 가기(분홍)
const KIND_COLOR: Record<RouteOptionKind, string> = {
  fast: "#60a5fa",
  shade: COLOR_ACCENT,
  green: "#a3e635",
  flat: "#67e8f9",
  hilly: "#fb923c",
  via: "#f472b6",
}
const PREF_LABEL: Record<WalkPreference, string> = {
  flat: "편한 길",
  hilly: "언덕길",
  shade: "그늘 많은 길",
  green: "푸른 길",
  fast: "빠른 길",
}
const PREF_ORDER: WalkPreference[] = ["flat", "hilly", "shade", "green", "fast"]
const STOP_ORDER: WalkStopCategory[] = ["동물병원", "펫샵", "용품점", "애견카페"]
const SOURCE_LABEL: Record<WalkPlanResult["understood"]["source"], string> = {
  llm: "AI가 이해",
  rules: "문장에서 읽음",
  form: "직접 선택",
}
const ROUTE_NOTICE = "업데이트가 안된 경우에는 길이 조금 다를 수 있는 점 양해 부탁드리겠습니다."

const SEASON_LABEL: Record<SeasonMode, string> = {
  spring_autumn: "봄·가을",
  summer_shade: "그늘 모드",
  winter_safety: "겨울 안전",
}
const SEASON_ORDER: SeasonMode[] = ["spring_autumn", "summer_shade", "winter_safety"]

type Point = { lat: number; lng: number }
type WalkStatus = "idle" | "tracking" | "saving" | "saved"
type WalkState = {
  status: WalkStatus
  startedAt: number | null
  points: Point[]
  distanceM: number
  elapsedS: number
  savedId: number | null
}

const WALK_IDLE: WalkState = {
  status: "idle",
  startedAt: null,
  points: [],
  distanceM: 0,
  elapsedS: 0,
  savedId: null,
}

type NaverGlobal = typeof naver
function getNaver(): NaverGlobal | null {
  if (typeof window === "undefined") return null
  return (window as unknown as { naver?: NaverGlobal }).naver ?? null
}

function haversineM(a: Point, b: Point): number {
  const r = 6371000
  const dLat = ((b.lat - a.lat) * Math.PI) / 180
  const dLng = ((b.lng - a.lng) * Math.PI) / 180
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  return 2 * r * Math.asin(Math.sqrt(s))
}

function km(m: number): string {
  return `${(m / 1000).toFixed(1)} km`
}

function minutes(m: number): number {
  return Math.max(1, Math.round(m / WALK_SPEED_MPS / 60))
}

function downsample(points: Point[]): [number, number][] {
  const step = Math.ceil(points.length / MAX_WALK_POINTS)
  return points.filter((_, i) => i % step === 0).map((p) => [p.lat, p.lng])
}

type NominatimResult = { place_id: number; display_name: string; lat: string; lon: string }

/** 장소·주소 검색(Nominatim) — 앱엔 없지만 데스크톱은 GPS가 없어 남긴다. 고르면 탭과 같은 순서로 찍힌다. */
function PlaceSearch({ onSelect }: { onSelect: (p: Point) => void }) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<NominatimResult[]>([])
  const [searching, setSearching] = useState(false)
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null)

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleOutside)
    return () => document.removeEventListener("mousedown", handleOutside)
  }, [])

  const search = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setResults([])
      return
    }
    setSearching(true)
    try {
      const base = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=5&accept-language=ko`
      let data = (await (
        await fetch(`${base}&viewbox=126.76,37.70,127.18,37.43&bounded=1`)
      ).json()) as NominatimResult[]
      if (data.length === 0)
        data = (await (await fetch(`${base}&countrycodes=kr`)).json()) as NominatimResult[]
      setResults(data)
      setOpen(data.length > 0)
    } catch {
      setResults([])
    }
    setSearching(false)
  }, [])

  return (
    <div ref={wrapperRef} className="relative">
      <Search className="text-gildle-muted pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2" />
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          if (timerRef.current) clearTimeout(timerRef.current)
          timerRef.current = setTimeout(() => void search(e.target.value), 400)
        }}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder="장소·주소 검색 (예: 여의도공원)"
        className="border-gildle-border bg-gildle-surface/95 text-gildle-text placeholder:text-gildle-muted focus:border-gildle-accent/60 w-full rounded-lg border py-2 pr-16 pl-8 text-xs shadow-md focus:outline-none"
      />
      {searching && (
        <span className="text-gildle-muted absolute top-1/2 right-2.5 -translate-y-1/2 text-[10px]">
          검색 중…
        </span>
      )}
      {open && results.length > 0 && (
        <ul className="border-gildle-border bg-gildle-surface absolute top-full z-30 mt-1 w-full rounded-lg border shadow-xl">
          {results.map((r) => (
            <li key={r.place_id}>
              <button
                type="button"
                onClick={() => {
                  onSelect({ lat: parseFloat(r.lat), lng: parseFloat(r.lon) })
                  setQuery(r.display_name.split(",")[0])
                  setOpen(false)
                }}
                className="text-gildle-text hover:bg-gildle-surface-2 w-full px-3 py-2 text-left text-xs"
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

function Fab({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className="border-gildle-border bg-gildle-surface/95 text-gildle-text hover:bg-gildle-surface-2 flex h-10 w-10 items-center justify-center rounded-full border shadow-md transition-colors disabled:opacity-40"
    >
      {children}
    </button>
  )
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gildle-surface-2 min-w-[4.5rem] rounded-lg px-3 py-1.5">
      <p className="text-gildle-muted text-[10px]">{label}</p>
      <p className="text-gildle-text text-sm font-semibold">{value}</p>
    </div>
  )
}

export default function GildleMap() {
  const mapEl = useRef<HTMLDivElement>(null)
  const mapRef = useRef<naver.maps.Map | null>(null)
  const startMarkerRef = useRef<naver.maps.Marker | null>(null)
  const endMarkerRef = useRef<naver.maps.Marker | null>(null)
  const routeOverlaysRef = useRef<naver.maps.Polyline[]>([])
  const walkOverlaysRef = useRef<naver.maps.Polyline[]>([])
  const watchIdRef = useRef<number | null>(null)

  const [sdkReady, setSdkReady] = useState(false)
  const [authFailed, setAuthFailed] = useState(false)
  const [mode, setMode] = useState<SeasonMode>("spring_autumn")
  const [start, setStart] = useState<Point | null>(null)
  const [end, setEnd] = useState<Point | null>(null)
  const [options, setOptions] = useState<RouteOption[]>([])
  const [selectedOpt, setSelectedOpt] = useState(0)
  const [night, setNight] = useState(false)
  const [viaLoading, setViaLoading] = useState<string | null>(null)
  // 시간·거리로 추천한 루프면 목표 정보(이때 options는 출발지로 돌아오는 코스들)
  const [plan, setPlan] = useState<WalkPlanResult | null>(null)
  const [loopSheet, setLoopSheet] = useState(false)
  const [planText, setPlanText] = useState("")
  const [planMinutes, setPlanMinutes] = useState("")
  const [planKm, setPlanKm] = useState("")
  const [planPref, setPlanPref] = useState<WalkPreference | null>(null)
  const [planStops, setPlanStops] = useState<WalkStopCategory[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [walk, setWalk] = useState<WalkState>(WALK_IDLE)

  const option: RouteOption | null = options[selectedOpt] ?? null
  const isLoop = plan !== null
  // 후보 좌표 앞뒤에 탭한 지점을 붙인다(루프는 출발지로 돌아온다).
  const withEnds = useCallback(
    (o: RouteOption): Point[] => {
      const tail = isLoop ? start : end
      if (!start || !tail) return []
      return [start, ...o.coordinates.map(([lat, lng]) => ({ lat, lng })), tail]
    },
    [isLoop, start, end]
  )
  const routeCoords = useMemo<Point[]>(() => (option ? withEnds(option) : []), [option, withEnds])
  const lengthM = option?.length_m ?? null
  const shadeRatio = option?.shade_ratio ?? null

  // --- 지도 초기화 (앱과 동일: 서울시청, zoom 13, minZoom 10, 로고 오른쪽 위) ---
  useEffect(() => {
    const nv = getNaver()
    if (!sdkReady || !nv || !mapEl.current || mapRef.current) return
    const map = new nv.maps.Map(mapEl.current, {
      center: new nv.maps.LatLng(SEOUL_CITY_HALL.lat, SEOUL_CITY_HALL.lng),
      zoom: 13,
      minZoom: 10,
      logoControlOptions: { position: nv.maps.Position.TOP_RIGHT },
      mapDataControl: false,
      scaleControl: false,
    })
    mapRef.current = map
    return () => {
      map.destroy()
      mapRef.current = null
    }
  }, [sdkReady])

  // 지도 탭: 1번째 출발, 2번째 도착(경로 계산), 3번째 다시 출발 — 앱과 동일.
  const stateRef = useRef({ start, end, mode, walkStatus: walk.status })
  stateRef.current = { start, end, mode, walkStatus: walk.status }

  // 경로 후보(빠른·그늘·푸른 길) — 이유와 경로 곁 반려동물 장소를 함께 받는다(2026-09-28).
  const computeRoute = useCallback(async (s: Point, e: Point, m: SeasonMode) => {
    setLoading(true)
    setError(null)
    setPlan(null)
    try {
      const result = await getRouteOptions({
        start_lat: s.lat,
        start_lng: s.lng,
        end_lat: e.lat,
        end_lng: e.lng,
        mode: m,
      })
      setOptions(result.options)
      setNight(result.night)
      setSelectedOpt(
        Math.max(
          0,
          result.options.findIndex((o) => o.recommended)
        )
      )
      if (result.options.length === 0) setError("두 지점을 잇는 보행 경로를 찾지 못했어요.")
    } catch (err) {
      setOptions([])
      setError(err instanceof Error ? err.message : "경로를 계산하지 못했어요.")
    }
    setLoading(false)
  }, [])

  // 고른 장소에 들렀다 가는 경로 — 지금 고른 후보와 같은 성격으로 계산해 후보 목록에 붙인다.
  const viaPlace = async (place: PetPlaceItem) => {
    if (!start || !end || !option || isLoop) return
    setViaLoading(place.id)
    setError(null)
    try {
      const base = option.kind === "via" ? "fast" : option.kind
      const { option: via } = await getRouteVia({
        start_lat: start.lat,
        start_lng: start.lng,
        end_lat: end.lat,
        end_lng: end.lng,
        mode,
        via_lat: place.lat,
        via_lng: place.lng,
        via_name: place.name,
        base_kind: base,
      })
      const rest = options.filter((o) => o.kind !== "via")
      setOptions([...rest, via])
      setSelectedOpt(rest.length)
    } catch (err) {
      setError(err instanceof Error ? err.message : "들렀다 가는 길을 만들지 못했어요.")
    }
    setViaLoading(null)
  }

  const placePoint = useCallback(
    (p: Point) => {
      const { start: s, end: e, mode: m, walkStatus } = stateRef.current
      if (walkStatus === "tracking" || walkStatus === "saving") return
      if (!s || (s && e)) {
        setStart(p)
        setEnd(null)
        setOptions([])
        setPlan(null)
        setError(null)
        return
      }
      setEnd(p)
      void computeRoute(s, p, m)
    },
    [computeRoute]
  )

  useEffect(() => {
    const nv = getNaver()
    const map = mapRef.current
    if (!sdkReady || !nv || !map) return
    const listener = nv.maps.Event.addListener(map, "click", (e: naver.maps.PointerEvent) => {
      placePoint({ lat: e.coord.y, lng: e.coord.x })
    })
    return () => nv.maps.Event.removeListener(listener)
  }, [sdkReady, placePoint])

  // --- 마커 ---
  useEffect(() => {
    const nv = getNaver()
    const map = mapRef.current
    if (!nv || !map) return
    const draw = (
      ref: React.RefObject<naver.maps.Marker | null>,
      p: Point | null,
      caption: string,
      color: string
    ) => {
      ref.current?.setMap(null)
      ref.current = null
      if (!p) return
      ref.current = new nv.maps.Marker({
        map,
        position: new nv.maps.LatLng(p.lat, p.lng),
        icon: {
          content: `<div style="display:flex;flex-direction:column;align-items:center;transform:translateY(-4px)"><span style="font-size:11px;font-weight:600;color:#f0fdf4;background:rgba(10,13,10,.85);padding:1px 6px;border-radius:6px;margin-bottom:2px">${caption}</span><span style="width:16px;height:16px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 0 2px rgba(0,0,0,.35)"></span></div>`,
          anchor: new nv.maps.Point(8, 30),
        },
      })
    }
    draw(startMarkerRef, start, "출발", COLOR_ACCENT)
    draw(endMarkerRef, end, "도착", COLOR_WARM)
  }, [start, end, sdkReady])

  // --- 경로 폴리라인: 후보를 모두 그리고(고른 것 굵게, 나머지는 옅게·클릭하면 선택) 흰 외곽선.
  //     루프를 고른 경우엔 루프만. 고른 후보 곁 반려동물 장소는 🐾 마커. ---
  const placeMarkersRef = useRef<naver.maps.Marker[]>([])
  useEffect(() => {
    const nv = getNaver()
    const map = mapRef.current
    if (!nv || !map) return
    routeOverlaysRef.current.forEach((o) => o.setMap(null))
    routeOverlaysRef.current = []
    placeMarkersRef.current.forEach((m) => m.setMap(null))
    placeMarkersRef.current = []
    if (routeCoords.length < 2) return
    const toPath = (pts: Point[]) => pts.map((p) => new nv.maps.LatLng(p.lat, p.lng))
    const overlays: naver.maps.Polyline[] = []
    const listeners: naver.maps.MapEventListener[] = []
    const allPts: Point[] = [...routeCoords]
    options.forEach((o, i) => {
      if (i === selectedOpt) return
      const pts = withEnds(o)
      if (pts.length < 2) return
      allPts.push(...pts)
      const line = new nv.maps.Polyline({
        map,
        path: toPath(pts),
        strokeColor: KIND_COLOR[o.kind],
        strokeOpacity: 0.45,
        strokeWeight: 6,
        clickable: true,
      })
      listeners.push(nv.maps.Event.addListener(line, "click", () => setSelectedOpt(i)))
      overlays.push(line)
    })
    const color = option ? KIND_COLOR[option.kind] : COLOR_ACCENT
    const path = toPath(routeCoords)
    overlays.push(
      new nv.maps.Polyline({
        map,
        path,
        strokeColor: "#ffffff",
        strokeOpacity: 0.85,
        strokeWeight: 12,
      }),
      new nv.maps.Polyline({ map, path, strokeColor: color, strokeOpacity: 1, strokeWeight: 8 })
    )
    routeOverlaysRef.current = overlays
    if (option) {
      placeMarkersRef.current = option.places.map(
        (pl) =>
          new nv.maps.Marker({
            map,
            position: new nv.maps.LatLng(pl.lat, pl.lng),
            title: `${pl.category} · ${pl.name}`,
            icon: {
              content: `<div style="font-size:18px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,.6))">🐾</div>`,
              anchor: new nv.maps.Point(9, 9),
            },
          })
      )
    }
    const lats = allPts.map((p) => p.lat)
    const lngs = allPts.map((p) => p.lng)
    map.fitBounds(
      new nv.maps.LatLngBounds(
        new nv.maps.LatLng(Math.min(...lats), Math.min(...lngs)),
        new nv.maps.LatLng(Math.max(...lats), Math.max(...lngs))
      ),
      { top: 60, right: 60, bottom: 260, left: 60 }
    )
    return () => nv.maps.Event.removeListener(listeners)
  }, [routeCoords, options, selectedOpt, option, withEnds, sdkReady])

  // --- 산책 추적 오버레이: 계획 경로는 회색 점선, 걸은 길은 accent 실선(앱 WalkScreen과 동일) ---
  useEffect(() => {
    const nv = getNaver()
    const map = mapRef.current
    if (!nv || !map) return
    walkOverlaysRef.current.forEach((o) => o.setMap(null))
    walkOverlaysRef.current = []
    if (walk.status !== "tracking" && walk.status !== "saving") return
    const overlays: naver.maps.Polyline[] = []
    if (routeCoords.length >= 2) {
      overlays.push(
        new nv.maps.Polyline({
          map,
          path: routeCoords.map((p) => new nv.maps.LatLng(p.lat, p.lng)),
          strokeColor: COLOR_MUTED,
          strokeOpacity: 0.7,
          strokeWeight: 5,
          strokeStyle: "shortdash",
        })
      )
    }
    if (walk.points.length >= 2) {
      overlays.push(
        new nv.maps.Polyline({
          map,
          path: walk.points.map((p) => new nv.maps.LatLng(p.lat, p.lng)),
          strokeColor: COLOR_ACCENT,
          strokeOpacity: 1,
          strokeWeight: 7,
        })
      )
    }
    walkOverlaysRef.current = overlays
    const last = walk.points[walk.points.length - 1]
    if (last) map.setCenter(new nv.maps.LatLng(last.lat, last.lng))
  }, [walk.status, walk.points, routeCoords, sdkReady])

  // 추적 중엔 경로 오버레이를 숨긴다(점선 계획 경로가 대신 보인다).
  useEffect(() => {
    const hide = walk.status === "tracking" || walk.status === "saving"
    routeOverlaysRef.current.forEach((o) => o.setVisible(!hide))
  }, [walk.status, routeCoords])

  // --- 산책 타이머 ---
  useEffect(() => {
    if (walk.status !== "tracking") return
    const id = window.setInterval(() => {
      setWalk((w) =>
        w.startedAt ? { ...w, elapsedS: Math.round((Date.now() - w.startedAt) / 1000) } : w
      )
    }, 1000)
    return () => window.clearInterval(id)
  }, [walk.status])

  useEffect(() => {
    return () => {
      if (watchIdRef.current !== null) navigator.geolocation?.clearWatch(watchIdRef.current)
    }
  }, [])

  // --- 버튼 동작 ---
  const changeMode = (m: SeasonMode) => {
    setMode(m)
    if (start && end && !isLoop) void computeRoute(start, end, m)
  }

  const locateMe = () => {
    if (!navigator.geolocation) {
      setError("이 브라우저는 위치 정보를 지원하지 않아요.")
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const p = { lat: pos.coords.latitude, lng: pos.coords.longitude }
        const nv = getNaver()
        mapRef.current?.morph(new nv!.maps.LatLng(p.lat, p.lng), 16)
        setStart(p)
        setPlan(null)
        setError(null)
        if (end) void computeRoute(p, end, mode)
        else setOptions([])
      },
      () => setError("현재 위치를 가져오지 못했어요. 브라우저 위치 권한을 확인해 주세요.")
    )
  }

  const makeLoops = async () => {
    if (!start) {
      setError("먼저 출발지를 정해 주세요.")
      setLoopSheet(false)
      return
    }
    const minutesNum = parseFloat(planMinutes)
    const kmNum = parseFloat(planKm)
    setLoopSheet(false)
    setLoading(true)
    setError(null)
    try {
      const result = await planWalk({
        lat: start.lat,
        lng: start.lng,
        ...(planText.trim() ? { text: planText.trim() } : {}),
        ...(minutesNum > 0 ? { minutes: Math.round(minutesNum) } : {}),
        ...(kmNum > 0 ? { distance_km: kmNum } : {}),
        ...(planPref ? { preference: planPref } : {}),
        ...(planStops.length > 0 ? { stops: planStops } : {}),
      })
      const dest = result.destination_place
      setEnd(dest ? { lat: dest.lat, lng: dest.lng } : null)
      setPlan(result)
      setOptions(result.options)
      setNight(result.night)
      setSelectedOpt(
        Math.max(
          0,
          result.options.findIndex((o) => o.recommended)
        )
      )
      if (result.options.length === 0)
        setError(
          result.understood.destination
            ? dest
              ? `${dest.name}까지 가는 길을 찾지 못했어요.`
              : `근처 3km 안에서 ${result.understood.destination}을(를) 찾지 못했어요.`
            : "돌아오는 코스를 찾지 못했어요. 시간이나 거리를 바꿔 보세요."
        )
    } catch (err) {
      setError(err instanceof Error ? err.message : "코스를 만들지 못했어요.")
    }
    setLoading(false)
  }

  const toggleStop = (c: WalkStopCategory) =>
    setPlanStops((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]))

  const clearAll = () => {
    setStart(null)
    setEnd(null)
    setOptions([])
    setPlan(null)
    setError(null)
    setWalk(WALK_IDLE)
  }

  const startWalk = () => {
    if (!getSuvisSession()) {
      setError("산책 기록은 로그인 후 저장할 수 있어요.")
      return
    }
    if (!navigator.geolocation) {
      setError("이 브라우저는 위치 정보를 지원하지 않아요.")
      return
    }
    setError(null)
    setWalk({ ...WALK_IDLE, status: "tracking", startedAt: Date.now() })
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const p = { lat: pos.coords.latitude, lng: pos.coords.longitude }
        setWalk((w) => {
          const last = w.points[w.points.length - 1]
          if (last && haversineM(last, p) < TRACK_MIN_STEP_M) return w
          return {
            ...w,
            points: [...w.points, p],
            distanceM: w.distanceM + (last ? haversineM(last, p) : 0),
          }
        })
      },
      () => setError("위치를 받지 못하고 있어요. 위치 권한을 확인해 주세요."),
      { enableHighAccuracy: true, maximumAge: 2000 }
    )
  }

  const finishWalk = async () => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current)
      watchIdRef.current = null
    }
    const startedAt = walk.startedAt ?? Date.now()
    setWalk((w) => ({ ...w, status: "saving" }))
    try {
      const saved = await createWalk({
        started_at: new Date(startedAt).toISOString(),
        ended_at: new Date().toISOString(),
        distance_m: Math.round(walk.distanceM),
        duration_s: Math.round((Date.now() - startedAt) / 1000),
        path: downsample(walk.points),
        season_mode: mode,
        ...(mode === "summer_shade" && shadeRatio !== null ? { avg_shade_score: shadeRatio } : {}),
      })
      setWalk((w) => ({ ...w, status: "saved", savedId: saved.id }))
    } catch (err) {
      setError(err instanceof Error ? err.message : "산책을 저장하지 못했어요.")
      setWalk((w) => ({ ...w, status: "idle" }))
    }
  }

  // --- 결과 카드 문구(앱과 동일) ---
  const hint = !start
    ? "지도를 눌러 출발지를 정하세요"
    : !end && !isLoop
      ? "도착지를 누르거나 루프 버튼으로 시간·거리에 맞춰 돌아오는 길을 추천받으세요"
      : null
  const tracking = walk.status === "tracking" || walk.status === "saving"
  const scriptSrc = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${NAVER_CLIENT_ID}`

  return (
    <div className="bg-gildle-bg text-gildle-text relative flex h-[calc(100dvh-4rem)] min-h-[480px] flex-col">
      {NAVER_CLIENT_ID && (
        <Script
          src={scriptSrc}
          strategy="afterInteractive"
          onLoad={() => setSdkReady(true)}
          onError={() => setAuthFailed(true)}
        />
      )}
      <Script id="navermap-auth-failure" strategy="beforeInteractive">
        {`window.navermap_authFailure = function () { window.dispatchEvent(new Event("navermap-auth-failure")) }`}
      </Script>
      <AuthFailureListener onFail={() => setAuthFailed(true)} />

      <header className="border-gildle-border bg-gildle-surface/80 z-20 flex shrink-0 flex-wrap items-center gap-2 border-b px-3 py-2 backdrop-blur sm:px-4">
        <Link href="/gildle" className="text-gildle-muted hover:text-gildle-text text-xs">
          ← Gildle
        </Link>
        <h1 className="text-gildle-text ml-1 text-sm font-semibold">길들</h1>
        <Link
          href="/gildle/walks"
          className="text-gildle-muted hover:text-gildle-text ml-2 text-xs"
        >
          내 산책 기록
        </Link>
        <div className="border-gildle-border ml-auto flex overflow-hidden rounded-lg border">
          {SEASON_ORDER.map((m) => (
            <button
              key={m}
              type="button"
              disabled={tracking}
              onClick={() => changeMode(m)}
              className={cn(
                "px-3 py-1.5 text-xs transition-colors disabled:opacity-50",
                mode === m
                  ? "bg-gildle-accent font-semibold text-[#0a0d0a]"
                  : "text-gildle-muted hover:text-gildle-text"
              )}
            >
              {SEASON_LABEL[m]}
            </button>
          ))}
        </div>
      </header>

      <div className="relative min-h-0 flex-1">
        {/* 네이버 SDK가 컨테이너에 position:relative를 인라인으로 강제하므로 absolute inset-0은
            무효(높이 0, 2026-09-28 프로덕션 실측). 부모 높이를 그대로 받는 h-full로 둔다. */}
        <div ref={mapEl} className="h-full w-full" />

        {!NAVER_CLIENT_ID && (
          <p className="text-gildle-muted absolute inset-0 flex items-center justify-center px-6 text-center text-sm">
            네이버 지도 키(NEXT_PUBLIC_NAVER_MAP_CLIENT_ID)가 설정되지 않았어요.
          </p>
        )}
        {authFailed && (
          <p className="absolute inset-x-0 top-0 z-20 bg-red-950/80 px-4 py-2 text-center text-xs text-red-200">
            네이버 지도 인증에 실패했어요. NCP 콘솔의 Web 서비스 URL에 이 도메인이 등록됐는지 확인해
            주세요.
          </p>
        )}

        <div className="absolute top-3 left-3 z-10 w-[min(20rem,calc(100%-5rem))]">
          <PlaceSearch
            onSelect={(p) => {
              const nv = getNaver()
              if (nv && mapRef.current) mapRef.current.morph(new nv.maps.LatLng(p.lat, p.lng), 15)
              placePoint(p)
            }}
          />
        </div>

        <div className="absolute top-3 right-3 z-10 flex flex-col gap-2">
          <Fab label="현재 위치를 출발지로" onClick={locateMe} disabled={tracking}>
            <LocateFixed className="h-4 w-4" />
          </Fab>
          <Fab
            label="시간·거리로 돌아오는 산책 추천"
            onClick={() => setLoopSheet(true)}
            disabled={tracking || loading}
          >
            <Repeat className="h-4 w-4" />
          </Fab>
          <Fab label="지우기" onClick={clearAll} disabled={tracking}>
            <Eraser className="h-4 w-4" />
          </Fab>
        </div>

        {loading && (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
            <Loader2 className="text-gildle-accent h-8 w-8 animate-spin" />
          </div>
        )}

        {loopSheet && (
          <div className="absolute inset-x-0 bottom-0 z-30 flex justify-center px-3 pb-3">
            <div className="border-gildle-border bg-gildle-surface max-h-[80%] w-full max-w-md overflow-y-auto rounded-2xl border p-4 shadow-2xl">
              <p className="text-sm font-semibold">시간·거리로 돌아오는 산책 추천</p>
              <p className="text-gildle-muted mt-1 text-xs">
                출발지에서 시작해 다시 출발지로 돌아오는 코스를 찾아요. 말로 적거나 직접 골라
                주세요.
              </p>
              <textarea
                value={planText}
                onChange={(e) => setPlanText(e.target.value)}
                maxLength={300}
                rows={2}
                placeholder="예: 오늘은 40분 동안 3키로 정도 편하게 걷고, 가는 길에 사료 사고 싶어 · 동물병원으로 가는 최단 경로"
                className="border-gildle-border bg-gildle-bg text-gildle-text placeholder:text-gildle-muted focus:border-gildle-accent mt-3 w-full resize-none rounded-lg border px-3 py-2 text-xs outline-none"
              />
              <div className="mt-2 grid grid-cols-2 gap-2">
                <label className="text-gildle-muted text-[11px]">
                  시간(분)
                  <input
                    type="number"
                    min={5}
                    max={180}
                    inputMode="numeric"
                    value={planMinutes}
                    onChange={(e) => setPlanMinutes(e.target.value)}
                    placeholder="예: 30"
                    className="border-gildle-border bg-gildle-bg text-gildle-text focus:border-gildle-accent mt-1 w-full rounded-lg border px-2 py-1.5 text-xs outline-none"
                  />
                </label>
                <label className="text-gildle-muted text-[11px]">
                  거리(km)
                  <input
                    type="number"
                    min={0.3}
                    max={15}
                    step={0.1}
                    inputMode="decimal"
                    value={planKm}
                    onChange={(e) => setPlanKm(e.target.value)}
                    placeholder="예: 2"
                    className="border-gildle-border bg-gildle-bg text-gildle-text focus:border-gildle-accent mt-1 w-full rounded-lg border px-2 py-1.5 text-xs outline-none"
                  />
                </label>
              </div>
              <p className="text-gildle-muted mt-3 text-[11px]">
                어떤 길로? (안 고르면 말한 대로, 없으면 편한 길)
              </p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {PREF_ORDER.map((k) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => setPlanPref((prev) => (prev === k ? null : k))}
                    className={cn(
                      "rounded-full border px-2.5 py-1 text-[11px] transition-colors",
                      planPref === k
                        ? "border-gildle-accent bg-gildle-accent-soft text-gildle-text"
                        : "border-gildle-border text-gildle-muted hover:text-gildle-text"
                    )}
                  >
                    {PREF_LABEL[k]}
                  </button>
                ))}
              </div>
              <p className="text-gildle-muted mt-3 text-[11px]">🐾 가는 길에 들를 곳</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {STOP_ORDER.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => toggleStop(c)}
                    className={cn(
                      "rounded-full border px-2.5 py-1 text-[11px] transition-colors",
                      planStops.includes(c)
                        ? "border-gildle-accent bg-gildle-accent-soft text-gildle-text"
                        : "border-gildle-border text-gildle-muted hover:text-gildle-text"
                    )}
                  >
                    {c}
                  </button>
                ))}
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setLoopSheet(false)}
                  className="text-gildle-muted hover:text-gildle-text rounded-lg px-3 py-1.5 text-xs"
                >
                  취소
                </button>
                <button
                  type="button"
                  onClick={() => void makeLoops()}
                  className="bg-gildle-accent rounded-lg px-3 py-1.5 text-xs font-semibold text-[#0a0d0a]"
                >
                  코스 추천받기
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex justify-center px-3 pb-3">
          <div className="border-gildle-border bg-gildle-surface/95 pointer-events-auto w-full max-w-2xl rounded-2xl border p-3 shadow-xl backdrop-blur">
            {error && <p className="mb-2 text-xs text-red-300">{error}</p>}
            {walk.status === "idle" && hint && <p className="text-gildle-muted text-xs">{hint}</p>}

            {walk.status === "idle" && options.length > 0 && (
              <div className="mb-2 flex max-h-[42vh] flex-col gap-1.5 overflow-y-auto">
                {plan && <PlanSummary plan={plan} />}
                {night && (
                  <p className="text-gildle-muted text-[11px]">밤이라 그늘 길은 빼고 보여드려요.</p>
                )}
                {options.map((o, i) => (
                  <button
                    key={`${o.kind}-${i}`}
                    type="button"
                    onClick={() => setSelectedOpt(i)}
                    className={cn(
                      "rounded-xl border px-3 py-2 text-left transition-colors",
                      i === selectedOpt
                        ? "border-gildle-accent bg-gildle-surface-2"
                        : "border-gildle-border hover:bg-gildle-surface-2"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ background: KIND_COLOR[o.kind] }}
                      />
                      <span className="text-sm font-semibold">{o.label}</span>
                      {o.recommended && (
                        <span className="bg-gildle-accent-soft text-gildle-accent rounded-full px-1.5 py-0.5 text-[10px]">
                          추천
                        </span>
                      )}
                      <span className="text-gildle-muted ml-auto text-[11px]">
                        {o.highlights.join(" · ")}
                      </span>
                    </div>
                    <p
                      className={cn(
                        "text-gildle-muted mt-1 text-xs leading-relaxed",
                        i !== selectedOpt && "line-clamp-1"
                      )}
                    >
                      {o.reason}
                    </p>
                  </button>
                ))}
                {option && option.places.length > 0 && isLoop && (
                  <p className="text-gildle-muted mt-1 text-[11px]">
                    🐾 이 코스 곁:{" "}
                    {option.places.map((pl) => `${pl.category} ${pl.name}`).join(" · ")}
                  </p>
                )}
                {option && option.places.length > 0 && !isLoop && (
                  <div className="mt-1">
                    <p className="text-gildle-muted mb-1 text-[11px]">
                      🐾 이 길 곁 반려동물 장소 — 누르면 들렀다 가는 길을 만들어요
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {option.places.map((pl) => (
                        <button
                          key={pl.id}
                          type="button"
                          disabled={viaLoading !== null}
                          onClick={() => void viaPlace(pl)}
                          title={pl.address}
                          className="border-gildle-border text-gildle-text hover:border-gildle-accent rounded-full border px-2.5 py-1 text-[11px] disabled:opacity-50"
                        >
                          {viaLoading === pl.id ? "계산 중…" : `${pl.category} · ${pl.name}`}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <p className="text-gildle-muted text-[10px]">{ROUTE_NOTICE}</p>
              </div>
            )}

            {walk.status === "idle" && lengthM !== null && (
              <div className="flex flex-wrap items-center gap-2">
                <StatTile label="거리" value={km(lengthM)} />
                <StatTile label="예상" value={`약 ${minutes(lengthM)}분`} />
                {shadeRatio !== null && (
                  <StatTile label="그늘" value={`${Math.round(shadeRatio * 100)}%`} />
                )}
                <button
                  type="button"
                  onClick={startWalk}
                  className="bg-gildle-accent ml-auto rounded-lg px-3 py-2 text-xs font-semibold text-[#0a0d0a]"
                >
                  {option && !isLoop && option.kind !== "via"
                    ? `${option.label}로 산책 시작`
                    : "이 길로 산책 시작"}
                </button>
              </div>
            )}

            {tracking && (
              <div className="flex flex-wrap items-center gap-2">
                <StatTile label="걸은 거리" value={km(walk.distanceM)} />
                <StatTile
                  label="시간"
                  value={`${Math.floor(walk.elapsedS / 60)}:${String(walk.elapsedS % 60).padStart(2, "0")}`}
                />
                <p className="text-gildle-muted text-[11px]">위치를 5m마다 기록 중</p>
                <button
                  type="button"
                  disabled={walk.status === "saving"}
                  onClick={() => void finishWalk()}
                  className="bg-gildle-warm ml-auto rounded-lg px-3 py-2 text-xs font-semibold text-[#0a0d0a] disabled:opacity-60"
                >
                  {walk.status === "saving" ? "저장 중…" : "산책 끝내기"}
                </button>
              </div>
            )}

            {walk.status === "saved" && (
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs">
                  산책 기록 #{walk.savedId} 저장됨 · {km(walk.distanceM)} ·{" "}
                  {Math.round(walk.elapsedS / 60)}분
                </p>
                <Link
                  href="/gildle/walks"
                  className="text-gildle-accent ml-auto rounded-lg px-3 py-1.5 text-xs hover:underline"
                >
                  기록 보기
                </Link>
                <button
                  type="button"
                  onClick={clearAll}
                  className="text-gildle-muted hover:text-gildle-text rounded-lg px-3 py-1.5 text-xs"
                >
                  새 산책
                </button>
              </div>
            )}

            <p className="text-gildle-muted mt-2 text-[10px]">
              © OpenStreetMap contributors · 보행 그래프 · 네이버 지도
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function AuthFailureListener({ onFail }: { onFail: () => void }) {
  useEffect(() => {
    window.addEventListener("navermap-auth-failure", onFail)
    return () => window.removeEventListener("navermap-auth-failure", onFail)
  }, [onFail])
  return null
}

function PlanSummary({ plan }: { plan: WalkPlanResult }) {
  const u = plan.understood
  const parts = [
    plan.destination_place ? `가장 가까운 ${plan.destination_place.name}까지` : null,
    u.minutes ? `${u.minutes}분 안에` : null,
    u.distance_km ? `${u.distance_km}km` : null,
    `목표 ${km(plan.target_m)}`,
    PREF_LABEL[u.preference],
    u.stops.length > 0 ? `${u.stops.join("·")} 들르기` : null,
  ].filter((x): x is string => x !== null)
  return (
    <p className="text-gildle-muted text-[11px]">
      {parts.join(" · ")} <span className="opacity-70">({SOURCE_LABEL[u.source]})</span>
    </p>
  )
}
