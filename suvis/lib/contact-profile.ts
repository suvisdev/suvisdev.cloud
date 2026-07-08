/** Suvisdev 소개·연락 페이지용 프로필 (필요 시 이 파일만 수정). */

export const CONTACT_PROFILE = {
  brand: "Suvisdev",
  role: "풀스택 · AI 애플리케이션 개발",
  taglineKo: "복잡함은 걷어내고, 확장은 자유롭게.",
  taglineEn: "Simplify Complexity, Scale Without Limits.",
  summary:
    "웹·백엔드·AI를 아우르며, 확장 가능한 설계와 단순한 구현 사이의 균형을 맞춥니다. " +
    "도메인별 AI 앱을 만들고, 지속 가능한 시스템을 구축합니다.",
  email: "suvisdev@gmail.com",
  instagram: "suvisdev",
  x: "suvisdev",
  inquiryHours: "평일 10:00 – 18:00 (KST, 답변은 순차 처리)",
  location: "대한민국 · 원격 협업",
  focusAreas: [
    "Next.js · React 기반 웹 UI",
    "FastAPI · Hexagonal 아키텍처 백엔드",
    "PostgreSQL · Neon · 도메인별 데이터 모델",
    "Gemini · RAG · 영화 추천(Mova) 등 AI 기능",
  ],
  projects: [
    { name: "Mova", href: "/mova", description: "AI 영화 추천·검색·랭킹" },
    { name: "Titanic", href: "/titanic", description: "승객 데이터 수집·분석 데모" },
    { name: "Apps", href: "/apps", description: "실험 앱 모음" },
  ],
} as const
