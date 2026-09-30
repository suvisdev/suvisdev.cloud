"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import Script from "next/script"
import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { getSuvisSession } from "@/lib/suvis-session"
import { formatDate, formatDuration, formatKm, SEASON_LABEL } from "@/lib/gildle-format"
import {
  deleteWalk,
  getWalk,
  listWalks,
  walkStats,
  type WalkDetail,
  type WalkStats,
  type WalkSummary,
} from "@/lib/gildle-api"

/**
 * 길들 산책 기록 — 앱의 기록·상세 탭과 같은 내용(2026-09-28, 웹·앱 동일화). 목록(날짜·거리·시간·
 * 계절·그늘)과 누적 통계, 선택한 산책의 경로를 네이버 지도에 그린다. 기록 API는 로그인 필요.
 */

const NAVER_CLIENT_ID = process.env.NEXT_PUBLIC_NAVER_MAP_CLIENT_ID ?? ""
const PAGE = 50 // 앱 기록 목록과 같은 크기
const COLOR_ACCENT = "#34d399"

type NaverGlobal = typeof naver
function getNaver(): NaverGlobal | null {
  if (typeof window === "undefined") return null
  return (window as unknown as { naver?: NaverGlobal }).naver ?? null
}

function seasonLabel(mode: string): string {
  return SEASON_LABEL[mode] ?? mode
}

function WalkMap({ walk, sdkReady }: { walk: WalkDetail | null; sdkReady: boolean }) {
  const el = useRef<HTMLDivElement>(null)
  const mapRef = useRef<naver.maps.Map | null>(null)
  const overlaysRef = useRef<(naver.maps.Polyline | naver.maps.Marker)[]>([])

  useEffect(() => {
    const nv = getNaver()
    if (!sdkReady || !nv || !el.current || mapRef.current) return
    mapRef.current = new nv.maps.Map(el.current, {
      center: new nv.maps.LatLng(37.5665, 126.978),
      zoom: 13,
      logoControlOptions: { position: nv.maps.Position.TOP_RIGHT },
      mapDataControl: false,
    })
    return () => {
      mapRef.current?.destroy()
      mapRef.current = null
    }
  }, [sdkReady])

  useEffect(() => {
    const nv = getNaver()
    const map = mapRef.current
    if (!nv || !map) return
    overlaysRef.current.forEach((o) => o.setMap(null))
    overlaysRef.current = []
    const pts = walk?.path ?? []
    if (pts.length < 2) return
    const path = pts.map(([lat, lng]) => new nv.maps.LatLng(lat, lng))
    const dot = (color: string) => ({
      content: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 0 2px rgba(0,0,0,.35)"></span>`,
      anchor: new nv.maps.Point(7, 7),
    })
    overlaysRef.current = [
      new nv.maps.Polyline({
        map,
        path,
        strokeColor: "#ffffff",
        strokeOpacity: 0.8,
        strokeWeight: 10,
      }),
      new nv.maps.Polyline({
        map,
        path,
        strokeColor: COLOR_ACCENT,
        strokeOpacity: 1,
        strokeWeight: 6,
      }),
      new nv.maps.Marker({ map, position: path[0], icon: dot(COLOR_ACCENT) }),
      new nv.maps.Marker({ map, position: path[path.length - 1], icon: dot("#d4a574") }),
    ]
    const lats = pts.map((p) => p[0])
    const lngs = pts.map((p) => p[1])
    map.fitBounds(
      new nv.maps.LatLngBounds(
        new nv.maps.LatLng(Math.min(...lats), Math.min(...lngs)),
        new nv.maps.LatLng(Math.max(...lats), Math.max(...lngs))
      ),
      { top: 40, right: 40, bottom: 40, left: 40 }
    )
  }, [walk, sdkReady])

  return (
    <div className="border-gildle-border relative h-full min-h-[320px] w-full overflow-hidden rounded-2xl border">
      <div ref={el} className="h-full w-full" />
      {walk && (walk.path?.length ?? 0) < 2 && (
        <p className="text-gildle-muted absolute inset-0 flex items-center justify-center text-sm">
          이 산책엔 저장된 경로가 없어요.
        </p>
      )}
      {!walk && (
        <p className="text-gildle-muted absolute inset-0 flex items-center justify-center text-sm">
          왼쪽에서 산책을 고르면 경로가 보여요.
        </p>
      )}
    </div>
  )
}

export default function WalkHistory() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null)
  const [sdkReady, setSdkReady] = useState(false)
  const [walks, setWalks] = useState<WalkSummary[]>([])
  const [stats, setStats] = useState<WalkStats | null>(null)
  const [selected, setSelected] = useState<WalkDetail | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const loadPage = useCallback(async (offset: number) => {
    setLoading(true)
    setError(null)
    try {
      const page = await listWalks(PAGE, offset)
      setWalks((prev) => (offset === 0 ? page : [...prev, ...page]))
      setHasMore(page.length === PAGE)
    } catch (e) {
      setError(e instanceof Error ? e.message : "산책 기록을 불러오지 못했어요.")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const ok = getSuvisSession() !== null
    setLoggedIn(ok)
    if (!ok) return
    void loadPage(0)
    walkStats()
      .then(setStats)
      .catch(() => setStats(null))
  }, [loadPage])

  const select = async (id: number) => {
    setError(null)
    setConfirmDelete(false)
    try {
      setSelected(await getWalk(id))
    } catch (e) {
      setError(e instanceof Error ? e.message : "산책 상세를 불러오지 못했어요.")
    }
  }

  // 기록 삭제 — 앱 상세 화면의 삭제와 같다. 지운 뒤 목록·통계를 다시 맞춘다.
  const removeSelected = async () => {
    if (!selected) return
    setDeleting(true)
    setError(null)
    try {
      await deleteWalk(selected.id)
      setWalks((prev) => prev.filter((w) => w.id !== selected.id))
      setSelected(null)
      walkStats()
        .then(setStats)
        .catch(() => setStats(null))
    } catch (e) {
      setError(e instanceof Error ? e.message : "기록을 삭제하지 못했어요.")
    }
    setDeleting(false)
    setConfirmDelete(false)
  }

  return (
    <div className="bg-gildle-bg text-gildle-text min-h-[calc(100dvh-4rem)] px-4 py-6 md:px-6">
      {NAVER_CLIENT_ID && (
        <Script
          src={`https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${NAVER_CLIENT_ID}`}
          strategy="afterInteractive"
          onLoad={() => setSdkReady(true)}
        />
      )}
      <div className="mx-auto max-w-6xl">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <Link href="/gildle/map" className="text-gildle-muted hover:text-gildle-text text-xs">
            ← 지도
          </Link>
          <h1 className="text-lg font-semibold">내 산책 기록</h1>
        </div>

        {loggedIn === false && (
          <div className="border-gildle-border bg-gildle-surface rounded-2xl border p-6 text-sm">
            로그인하면 산책 기록을 저장하고 다시 볼 수 있어요.{" "}
            <Link href="/login" className="text-gildle-accent underline">
              로그인하기
            </Link>
          </div>
        )}

        {loggedIn && (
          <>
            {stats && (
              <div className="mb-5 grid grid-cols-3 gap-3">
                {[
                  ["산책", `${stats.total_count}회`],
                  ["누적 거리", formatKm(stats.total_distance_m)],
                  ["누적 시간", formatDuration(stats.total_duration_s)],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="border-gildle-border bg-gildle-surface rounded-xl border px-4 py-3"
                  >
                    <p className="text-gildle-muted text-[11px]">{label}</p>
                    <p className="text-base font-semibold">{value}</p>
                  </div>
                ))}
              </div>
            )}
            {error && <p className="mb-3 text-xs text-red-300">{error}</p>}

            <div className="grid gap-4 md:grid-cols-[minmax(0,22rem)_1fr]">
              <div className="flex flex-col gap-2">
                {walks.length === 0 && !loading && (
                  <p className="text-gildle-muted border-gildle-border rounded-xl border p-4 text-sm">
                    아직 산책 기록이 없습니다. 지도에서 산책을 시작해 보세요.
                  </p>
                )}
                {walks.map((w) => (
                  <button
                    key={w.id}
                    type="button"
                    onClick={() => void select(w.id)}
                    className={cn(
                      "border-gildle-border bg-gildle-surface hover:bg-gildle-surface-2 rounded-xl border px-4 py-3 text-left transition-colors",
                      selected?.id === w.id && "border-gildle-accent"
                    )}
                  >
                    <p className="text-sm font-medium">
                      {formatKm(w.distance_m)} · {formatDuration(w.duration_s)}
                    </p>
                    <p className="text-gildle-muted mt-0.5 text-xs">
                      {formatDate(w.started_at)} · {seasonLabel(w.season_mode)}
                      {w.avg_shade_score !== null &&
                        ` · 그늘 ${Math.round(w.avg_shade_score * 100)}%`}
                    </p>
                  </button>
                ))}
                {loading && (
                  <Loader2 className="text-gildle-accent mx-auto my-2 h-5 w-5 animate-spin" />
                )}
                {hasMore && !loading && (
                  <button
                    type="button"
                    onClick={() => void loadPage(walks.length)}
                    className="text-gildle-muted hover:text-gildle-text py-2 text-xs"
                  >
                    더 보기
                  </button>
                )}
              </div>
              <div className="flex flex-col gap-3">
                {selected && (
                  <div className="border-gildle-border bg-gildle-surface flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border px-4 py-3">
                    <p className="text-gildle-muted w-full text-xs">
                      {formatDate(selected.started_at)}
                    </p>
                    {[
                      ["거리", formatKm(selected.distance_m)],
                      ["시간", formatDuration(selected.duration_s)],
                      ["모드", seasonLabel(selected.season_mode)],
                      ...(selected.avg_shade_score !== null
                        ? [["그늘", `${Math.round(selected.avg_shade_score * 100)}%`]]
                        : []),
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="text-gildle-muted text-[10px]">{label}</p>
                        <p className="text-sm font-semibold">{value}</p>
                      </div>
                    ))}
                    <div className="ml-auto flex items-center gap-2 text-xs">
                      {confirmDelete ? (
                        <>
                          <span>이 기록을 삭제할까요?</span>
                          <button
                            type="button"
                            onClick={() => setConfirmDelete(false)}
                            className="text-gildle-muted hover:text-gildle-text rounded-lg px-2 py-1.5"
                          >
                            취소
                          </button>
                          <button
                            type="button"
                            disabled={deleting}
                            onClick={() => void removeSelected()}
                            className="rounded-lg bg-red-500/90 px-3 py-1.5 font-semibold text-white disabled:opacity-60"
                          >
                            {deleting ? "삭제 중…" : "삭제"}
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmDelete(true)}
                          className="text-gildle-muted rounded-lg px-2 py-1.5 hover:text-red-300"
                        >
                          삭제
                        </button>
                      )}
                    </div>
                  </div>
                )}
                <div className="h-[60vh] md:h-auto md:min-h-[480px] md:flex-1">
                  <WalkMap walk={selected} sdkReady={sdkReady} />
                </div>
              </div>
            </div>
          </>
        )}

        {/* 앱 '내 정보' 탭 아래와 같은 안내 링크 */}
        <nav className="text-gildle-muted mt-8 flex justify-center gap-4 text-xs">
          <Link href="/gildle/privacy" className="hover:text-gildle-text">
            개인정보처리방침
          </Link>
          <Link href="/gildle/account-deletion" className="hover:text-gildle-text">
            계정 삭제 안내
          </Link>
        </nav>
      </div>
    </div>
  )
}
