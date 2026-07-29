export type DevLogEntry = {
  id: string
  title: string
  /** 왜 그렇게 설계했는지 · 어떤 트레이드오프를 택했는지 한 줄 */
  intent: string
  /** 상단에 먼저 노출할 핵심 항목 */
  highlighted: boolean
}

/**
 * 공개용 개발 기록. 내부 작업 일지를 그대로 옮기지 않고, 외부에 공개해도
 * 안전한 항목만 골라 "무엇을 만들었나 + 왜 그렇게 설계했나" 수준으로 다시
 * 쓴 것이다.
 *
 * 항목을 추가할 때는 파일 경로·클래스명·수치·인프라 세부·미해결 이슈를 넣지
 * 않는다. 판단 기준: 외부인이 이걸 보고 시스템 내부 구조를 파악하는 데
 * 도움이 되는가 — 그렇다면 넣지 않는다.
 */
export const DEV_LOG: DevLogEntry[] = [
  {
    id: "local-cloud-swap",
    title: "로컬 AI ↔ 클라우드 AI 전환 구조",
    intent:
      "같은 기능을 환경에 따라 자체 모델로도, 클라우드 AI로도 돌릴 수 있게 했다. AI 제공자를 갈아끼워도 나머지 코드는 바뀌지 않도록 경계를 나눴다.",
    highlighted: true,
  },
  {
    id: "model-selection-under-constraints",
    title: "제한된 자원에서의 모델 선택",
    intent:
      "성능 수치보다 \"이 하드웨어에서 실제로 끝까지 도는가\"를 우선 기준으로 두고, 후보를 직접 재본 뒤 가장 가벼운 쪽을 골랐다.",
    highlighted: true,
  },
  {
    id: "env-aware-startup",
    title: "환경별 자동 작업 제어",
    intent:
      "환경마다 코드를 분기하거나 브랜치를 나누는 대신 설정 하나로 끄고 켜게 해, 두 환경을 하나의 코드로 유지하는 비용을 낮췄다.",
    highlighted: true,
  },
  {
    id: "discontinued-with-reasons",
    title: "접기로 한 기능의 기록",
    intent:
      "데이터를 실제로 확인해 목표 달성이 불가능하다고 판단한 기능은 접었다. 대신 왜 접었는지를 남겨 같은 검토를 반복하지 않게 했다.",
    highlighted: true,
  },
  {
    id: "movie-recommendation",
    title: "영화 추천 AI 서비스",
    intent:
      "추천 결과만 던지지 않고 왜 골랐는지를 함께 보여줘, 사용자가 납득하고 방향을 조정할 수 있게 했다.",
    highlighted: false,
  },
  {
    id: "image-review",
    title: "업로드 이미지 자동 검수",
    intent:
      "판정이 틀릴 수 있는 항목은 차단이 아니라 경고로 처리해, 오탐이 사용자 흐름을 막지 않도록 분리했다.",
    highlighted: false,
  },
  {
    id: "sentiment-analysis",
    title: "한국어 리뷰 감정 분석",
    intent:
      "범용 모델을 그대로 쓰지 않고, 실제 서비스에 들어오는 한국어 문장으로 다시 학습시켜 맞췄다.",
    highlighted: false,
  },
  {
    id: "poster-genre",
    title: "포스터 장르 분류",
    intent:
      "텍스트 정보 없이 이미지만으로 분류해, 설명이 부실한 자료도 처리할 수 있게 했다.",
    highlighted: false,
  },
  {
    id: "document-summary",
    title: "문서 업로드 → 자동 요약",
    intent:
      "업로드부터 요약까지를 한 흐름으로 묶되 단계를 분리해, 추출 방식과 요약 방식을 각각 교체할 수 있게 했다.",
    highlighted: false,
  },
  {
    id: "question-routing",
    title: "대화형 AI 질문 라우팅",
    intent:
      "모든 질문을 같은 방식으로 처리하지 않고 성격을 먼저 판별해, 단순한 조회에 무거운 추론을 쓰지 않도록 했다.",
    highlighted: false,
  },
  {
    id: "domain-test-baseline",
    title: "도메인 모델 테스트 기준선",
    intent:
      "핵심 데이터 구조의 테스트를 다시 세워, 이후 기능들이 따라갈 기준 형태로 삼았다.",
    highlighted: false,
  },
  {
    id: "admin-dashboard",
    title: "관리자 대시보드",
    intent:
      "사용자·앱·통계를 한 화면에 모아, 운영 중 화면을 옮겨 다니며 생기는 맥락 전환 비용을 줄였다.",
    highlighted: false,
  },
]
