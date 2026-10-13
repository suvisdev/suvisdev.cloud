/** Suvisdev 소개·연락 페이지용 프로필 (필요 시 이 파일만 수정). */

export const CONTACT_PROFILE = {
  brand: "Suvisdev",
  role: "풀스택 · AI 애플리케이션 개발",
  taglineKo: "복잡함은 걷어내고, 확장은 자유롭게.",
  taglineEn: "Simplify Complexity, Scale Without Limits.",
  summary:
    "웹·백엔드·AI를 아우르며, 확장 가능한 설계와 단순한 구현 사이의 균형을 맞춥니다. " +
    "도메인별 AI 앱을 만들고, 지속 가능한 시스템을 구축합니다.",
  email: "ssuvisdev@gmail.com",
  instagram: "suvisdev",
  x: "suvisdev",
  inquiryHours: "평일 10:00 – 18:00 (KST, 답변은 순차 처리)",
  location: "대한민국 · 원격 협업",
  focusAreas: [
    "Next.js(App Router) 웹 · Flutter 모바일 앱",
    "FastAPI · Clean Architecture + Hexagonal · 스타 토폴로지 모듈러 모놀리식",
    "PostgreSQL · pgvector · Redis — 집 서버 k3s로 직접 운영",
    "EXAONE LoRA 파인튜닝 · llama.cpp/Ollama 자체 서빙 · RAG(bge-m3) · Gemini 폴백",
  ],
  projects: [
    { name: "Mova", href: "/mova", description: "AI 영화 추천 — 파인튜닝한 EXAONE이 도구를 골라 답하는 채팅" },
    { name: "Gildle", href: "/gildle", description: "반려견 산책 경로 — 시간대별 그늘·푸른 길 추천 앱" },
    { name: "Apps", href: "/apps", description: "개인·팀 프로젝트 모음" },
  ],
} as const
