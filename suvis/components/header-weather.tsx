"use client"

import { useCallback, useEffect, useState } from "react"
import { Cloud } from "lucide-react"
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import { patchState } from "@/lib/form-status"
import { cn } from "@/lib/utils"

type WeatherData = {
  city: string
  temp_c: number
  description: string
  icon: string
}

type DailyForecast = {
  date: string
  weekday: string
  temp_min: number
  temp_max: number
  description: string
  icon: string
}

type ForecastData = {
  city: string
  days: DailyForecast[]
}

type WeatherError = {
  status: number
  message: string
  detail?: string
}

const FORECAST_DAYS = 5
const wrapClass = "flex shrink-0 items-center gap-1.5"

function formatError(status: number, detail?: string): WeatherError {
  if (status === 502 && detail?.includes("uvicorn")) {
    return { status, message: "백엔드 미실행", detail }
  }
  if (status === 503) {
    return { status, message: "API 키 설정 필요", detail }
  }
  if (status === 401 || detail?.toLowerCase().includes("invalid api key")) {
    return { status: status || 401, message: "날씨 API 키 오류", detail }
  }
  if (detail && detail.length <= 40) {
    return { status, message: detail, detail }
  }
  if (detail && detail.length > 40) {
    return { status, message: `${detail.slice(0, 37)}…`, detail }
  }
  return { status, message: "날씨를 불러올 수 없음", detail }
}

function formatDayLabel(date: string, weekday: string): string {
  const d = new Date(`${date}T12:00:00`)
  if (Number.isNaN(d.getTime())) return weekday
  return `${d.getMonth() + 1}/${d.getDate()}(${weekday})`
}

function tempTextColor(temp: number): string {
  if (temp >= 28) return "text-amber-700"
  if (temp >= 20) return "text-orange-700"
  if (temp >= 10) return "text-cyan-700"
  return "text-blue-700"
}

function dayCardColors(_icon: string, _tempMax: number): string {
  return "bg-neutral-50 ring-1 ring-neutral-200 hover:bg-neutral-100"
}

function triggerHoverColors(_temp: number): string {
  return "hover:bg-neutral-300/80 data-[state=open]:bg-neutral-300"
}

type CurrentWeatherState = {
  weather: WeatherData | null
  loading: boolean
  error: WeatherError | null
}

type ForecastState = {
  data: ForecastData | null
  loading: boolean
  error: WeatherError | null
  fetched: boolean
}

export function HeaderWeather() {
  const [current, setCurrent] = useState<CurrentWeatherState>({
    weather: null,
    loading: true,
    error: null,
  })
  const [forecast, setForecast] = useState<ForecastState>({
    data: null,
    loading: false,
    error: null,
    fetched: false,
  })
  const patchCurrent = (patch: Partial<CurrentWeatherState>) => patchState(setCurrent, patch)
  const patchForecast = (patch: Partial<ForecastState>) => patchState(setForecast, patch)

  const loadForecast = useCallback(async () => {
    if (forecast.fetched && forecast.data) return
    patchForecast({ loading: true, error: null })
    try {
      const res = await fetch("/api/weather/forecast", { cache: "no-store" })
      const body = (await res.json()) as ForecastData & { detail?: string }
      if (!res.ok) {
        patchForecast({
          data: null,
          error: formatError(res.status, body.detail),
          loading: false,
        })
        return
      }
      patchForecast({
        data: { ...body, days: (body.days ?? []).slice(0, FORECAST_DAYS) },
        fetched: true,
        loading: false,
      })
    } catch {
      patchForecast({
        data: null,
        error: { status: 0, message: "네트워크 오류" },
        loading: false,
      })
    }
  }, [forecast.data, forecast.fetched])

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch("/api/weather", { cache: "no-store" })
        let body: WeatherData & { detail?: string }
        try {
          body = (await res.json()) as WeatherData & { detail?: string }
        } catch {
          if (!cancelled) {
            patchCurrent({
              weather: null,
              error: { status: res.status || 0, message: "응답 형식 오류" },
            })
          }
          return
        }

        if (!res.ok) {
          if (!cancelled) {
            patchCurrent({ weather: null, error: formatError(res.status, body.detail) })
          }
          return
        }

        if (!cancelled) {
          patchCurrent({ weather: body, error: null })
        }
      } catch {
        if (!cancelled) {
          patchCurrent({ weather: null, error: { status: 0, message: "네트워크 오류" } })
        }
      } finally {
        if (!cancelled) patchCurrent({ loading: false })
      }
    }

    void load()
    const id = window.setInterval(() => void load(), 10 * 60 * 1000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  if (current.loading) {
    return (
      <div className={cn(wrapClass, "min-w-[5.5rem]")} aria-hidden>
        <div className="size-7 animate-pulse rounded opacity-40" />
        <div className="h-4 w-10 animate-pulse rounded opacity-40" />
      </div>
    )
  }

  if (!current.weather && current.error) {
    const title = current.error.detail
      ? `[${current.error.status || "—"}] ${current.error.message}\n${current.error.detail}`
      : `[${current.error.status || "—"}] ${current.error.message}`

    return (
      <div
        className={cn(wrapClass, "text-[11px] text-neutral-500")}
        title={title}
      >
        <Cloud className="size-4 shrink-0 text-neutral-400" aria-hidden />
        <span className="shrink-0 font-mono text-[10px] font-semibold tabular-nums text-neutral-600">
          {current.error.status > 0 ? current.error.status : "—"}
        </span>
        <span className="max-w-[5.5rem] truncate">{current.error.message}</span>
      </div>
    )
  }

  if (!current.weather) return null

  const iconUrl = `https://openweathermap.org/img/wn/${current.weather.icon}@2x.png`

  return (
    <HoverCard
      openDelay={150}
      closeDelay={80}
      onOpenChange={(open) => {
        if (open) void loadForecast()
      }}
    >
      <HoverCardTrigger asChild>
        <div
          className={cn(
            wrapClass,
            "cursor-default rounded-full px-2 py-1 transition-all duration-200",
            triggerHoverColors(current.weather.temp_c),
          )}
          title={`${current.weather.city} · ${current.weather.description} (마우스를 올리면 5일 예보)`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={iconUrl}
            alt=""
            width={28}
            height={28}
            className="size-7 shrink-0 object-contain drop-shadow-[0_0_6px_rgba(251,191,36,0.15)]"
          />
          <span
            className={cn(
              "text-sm font-medium tabular-nums transition-colors duration-200",
              tempTextColor(current.weather.temp_c),
            )}
          >
            {Math.round(current.weather.temp_c)}°
          </span>
          <span className="hidden max-w-[4.5rem] truncate text-[11px] text-neutral-600 min-[420px]:inline">
            {current.weather.city}
          </span>
        </div>
      </HoverCardTrigger>

      <HoverCardContent
        align="end"
        side="bottom"
        sideOffset={8}
        className="w-auto border border-neutral-200 bg-white p-3 text-neutral-900 shadow-lg shadow-black/10"
      >
        <p className="mb-2 text-xs font-medium text-neutral-600">
          {forecast.data?.city ?? current.weather.city} · 5일 예보
        </p>

        {forecast.loading && (
          <div className="grid grid-cols-5 gap-2">
            {Array.from({ length: FORECAST_DAYS }).map((_, i) => (
              <div key={i} className="flex w-14 flex-col items-center gap-1">
                <div className="h-3 w-10 animate-pulse rounded bg-neutral-200" />
                <div className="size-8 animate-pulse rounded bg-neutral-200" />
                <div className="h-3 w-8 animate-pulse rounded bg-neutral-200" />
              </div>
            ))}
          </div>
        )}

        {!forecast.loading && forecast.error && (
          <p className="text-xs text-neutral-600">
            <span className="font-mono text-neutral-800">
              {forecast.error.status > 0 ? forecast.error.status : "—"}
            </span>{" "}
            {forecast.error.message}
          </p>
        )}

        {!forecast.loading && forecast.data && forecast.data.days.length > 0 && (
          <>
            <div className="grid grid-cols-5 gap-2">
              {forecast.data.days.map((day) => (
                <div
                  key={day.date}
                  className={cn(
                    "flex w-14 flex-col items-center gap-0.5 rounded-lg px-0.5 py-1.5 text-center transition-colors duration-200",
                    dayCardColors(day.icon, day.temp_max),
                  )}
                  title={day.description}
                >
                  <span className="text-[10px] text-neutral-500">
                    {formatDayLabel(day.date, day.weekday)}
                  </span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`https://openweathermap.org/img/wn/${day.icon}@2x.png`}
                    alt=""
                    width={32}
                    height={32}
                    className="size-8 object-contain"
                  />
                  <span
                    className={cn(
                      "text-[11px] font-medium tabular-nums",
                      tempTextColor(day.temp_max),
                    )}
                  >
                    {Math.round(day.temp_max)}°
                  </span>
                  <span className="text-[10px] tabular-nums text-neutral-500">
                    {Math.round(day.temp_min)}°
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </HoverCardContent>
    </HoverCard>
  )
}
