import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "개인정보처리방침 — 길들",
  description: "길들(gildle) 개인정보처리방침 — 위치정보 처리 고지 포함",
}

type Section = { title: string; body: React.ReactNode }

// 2026-09-22 작성. 지금 gildle은 좌표를 계산에만 쓰고 저장하지 않는다
// (route_requests·route_results 테이블 0행). 앱 출시로 산책 기록 기능이 들어가면
// §2·§3을 반드시 갱신할 것 — 실제와 다른 방침은 그 자체로 위반이다.
export default function GildlePrivacyPage() {
  const sections: Section[] = [
    {
      title: "1. 개인정보의 처리 목적",
      body: (
        <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-gildle-muted">
          <li>보행 경로 계산 및 안내 — 출발지·도착지를 기준으로 그늘·안전 점수를 반영한 경로 제공</li>
          <li>회원 식별 및 로그인 유지(소셜 로그인 이용 시)</li>
          <li>서비스 오류 진단 및 품질 개선</li>
        </ul>
      ),
    },
    {
      title: "2. 처리하는 개인정보의 항목",
      body: (
        <div className="space-y-3 text-sm leading-relaxed text-gildle-muted">
          <p className="font-medium text-gildle-text">위치정보</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <span className="text-gildle-text">출발지·도착지 좌표</span> — 경로를 계산하는
              동안에만 사용하며, <span className="text-gildle-text">서버에 저장하지 않습니다.</span>
            </li>
            <li>
              앱에서 현재 위치를 사용하는 경우, 위치 권한은 앱이 화면에 표시된 상태에서만
              사용합니다(백그라운드 위치 수집 없음).
            </li>
          </ul>
          <p className="font-medium text-gildle-text">회원 정보(소셜 로그인 시)</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>이메일 주소, 닉네임, 소셜 계정 고유 식별자</li>
          </ul>
          <p className="font-medium text-gildle-text">자동 수집 항목</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>접속 로그, IP 주소, User-Agent, 기기 정보(OS·모델)</li>
          </ul>
        </div>
      ),
    },
    {
      title: "3. 보유 및 이용 기간",
      body: (
        <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-gildle-muted">
          <li>좌표: 저장하지 않으므로 보유 기간이 없습니다(요청 처리 후 즉시 소멸).</li>
          <li>회원 정보: 회원 탈퇴 시까지. 탈퇴 즉시 파기합니다.</li>
          <li>접속 로그: 수집일로부터 3개월.</li>
          <li>
            관계 법령에 따라 보존이 필요한 경우 해당 법령이 정한 기간 동안 보관합니다.
          </li>
        </ul>
      ),
    },
    {
      title: "4. 개인정보의 파기",
      body: (
        <p className="text-sm leading-relaxed text-gildle-muted">
          보유 기간이 지나거나 처리 목적이 달성되면 지체 없이 파기합니다. 전자적 파일은
          복구할 수 없는 방법으로 삭제하고, 출력물은 분쇄하거나 소각합니다.
        </p>
      ),
    },
    {
      title: "5. 제3자 제공 및 처리 위탁",
      body: (
        <div className="space-y-2 text-sm leading-relaxed text-gildle-muted">
          <p>개인정보를 제3자에게 제공하지 않습니다. 다만 아래 서비스를 이용합니다.</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <span className="text-gildle-text">OpenStreetMap</span> — 지도 타일 제공.
              지도를 표시하는 과정에서 이용자의 IP와 조회 영역이 해당 서버에 전달됩니다.
            </li>
            <li>
              <span className="text-gildle-text">카카오</span> — 소셜 로그인 및 주소↔좌표 변환.
            </li>
          </ul>
        </div>
      ),
    },
    {
      title: "6. 정보주체의 권리와 행사 방법",
      body: (
        <p className="text-sm leading-relaxed text-gildle-muted">
          이용자는 언제든지 자신의 개인정보에 대한 열람·정정·삭제·처리정지를 요청할 수
          있습니다. 아래 연락처로 요청하시면 지체 없이 조치합니다. 위치정보는 저장하지
          않으므로 별도의 삭제 요청 대상이 없습니다.
        </p>
      ),
    },
    {
      title: "7. 안전성 확보 조치",
      body: (
        <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-gildle-muted">
          <li>모든 통신 구간 HTTPS 암호화</li>
          <li>접근 권한 최소화 및 인증 토큰 기반 접근 통제</li>
          <li>개인정보 처리 시스템 접근 기록 보관</li>
        </ul>
      ),
    },
    {
      title: "8. 개인정보 보호책임자",
      body: (
        <p className="text-sm leading-relaxed text-gildle-muted">
          문의:{" "}
          <a className="underline underline-offset-2 hover:text-gildle-text" href="mailto:ssuvisdev@gmail.com">
            ssuvisdev@gmail.com
          </a>
        </p>
      ),
    },
    {
      title: "9. 방침의 변경",
      body: (
        <p className="text-sm leading-relaxed text-gildle-muted">
          법령·서비스 변경에 따라 방침이 바뀔 수 있으며, 변경 시 본 페이지에 공지합니다.
          산책 기록 저장 등 위치정보를 보관하는 기능이 추가되면 시행 전에 본 방침을
          갱신하고 별도로 안내합니다.
        </p>
      ),
    },
  ]

  return (
    <main className="gildle-nature-bg min-h-screen">
      <div className="mx-auto max-w-3xl px-4 py-10 md:px-6 md:py-14">
        <Link href="/gildle" className="text-xs text-gildle-muted hover:text-gildle-text">
          ← 길들
        </Link>
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-gildle-text">
          개인정보처리방침
        </h1>
        <p className="mt-2 text-sm text-gildle-muted">본 방침은 2026년 9월 22일부터 적용됩니다.</p>

        <div className="mt-8 space-y-8">
          {sections.map((section) => (
            <section key={section.title}>
              <h2 className="text-base font-semibold text-gildle-text">{section.title}</h2>
              <div className="mt-2">{section.body}</div>
            </section>
          ))}
        </div>
      </div>
    </main>
  )
}
