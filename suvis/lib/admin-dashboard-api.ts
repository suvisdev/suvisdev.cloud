import { safeApiErrorMessage } from "@/lib/user-facing-error"

export type ActivityItem = {
  id: string
  label: string
  time: string
  kind: "agent" | "crawl"
}

/** TODO: harvester 실행 이력 API 연동 전까지 mock. */
export async function getTodayCrawlCount(): Promise<number> {
  return 12
}

/** TODO: viewer users 카운트 API 연동 전까지 mock. */
export async function getActiveUserCount(): Promise<number> {
  return 4
}

/** TODO: 에이전트 invoke 로그 + harvester 실행 로그를 합쳐서 보여줄 API 연동 전까지 mock. */
export async function getRecentActivity(): Promise<ActivityItem[]> {
  return [
    { id: "1", label: "포스터 장르 분류기 테스트 호출", time: "10분 전", kind: "agent" },
    { id: "2", label: "KOBIS 일간 박스오피스 수집 완료", time: "1시간 전", kind: "crawl" },
    { id: "3", label: "TMDB top_rated 20편 반영", time: "3시간 전", kind: "crawl" },
    { id: "4", label: "포스터 장르 분류기 ON 전환", time: "어제", kind: "agent" },
  ]
}

export type ChatbotRoute = {
  chatbot: string
  step: string
  target: string
}

export type ServingServer = {
  node: string
  machine: string
  chatbots: ChatbotRoute[]
}

/** 이 요청을 받은 backend 파드의 노드(노트북/집컴)와, 챗봇별로 지금 답하는 LLM 위치. */
export async function getServingServer(): Promise<ServingServer> {
  const res = await fetch("/api/backend/viewer/admin/server")
  const data = (await res.json()) as ServingServer & { detail?: unknown }
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, "서버 정보를 불러오지 못했습니다.", res.status))
  }
  return data
}
