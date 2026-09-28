import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "개인정보처리방침 — 길들",
  description: "길들(gildle) 개인정보처리방침 — 위치정보 처리 고지 포함",
}

type Section = { title: string; body: React.ReactNode }

// 2026-09-22 작성, 09-28 개정: 산책 기록(경로 좌표) 저장, 이메일 회원가입, 앱 회원 탈퇴,
// 반려동물 장소 검색(카카오)·지도(네이버)·푸시(FCM)를 반영했다. 기능이 바뀌면 §2·§3·§5를
// 먼저 고칠 것 — 실제와 다른 방침은 그 자체로 위반이고, Play 데이터 보안 양식과도 맞아야 한다.
export default function GildlePrivacyPage() {
  const sections: Section[] = [
    {
      title: "1. 개인정보의 처리 목적",
      body: (
        <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-gildle-muted">
          <li>보행 경로 계산 및 안내 — 출발지·도착지를 기준으로 그늘·안전 점수를 반영한 경로 제공</li>
          <li>경로 곁 반려동물 장소(동물병원·펫샵·용품점·애견카페) 안내</li>
          <li>산책 기록 저장 및 조회(로그인한 이용자가 산책을 저장한 경우)</li>
          <li>회원 식별 및 로그인 유지</li>
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
              <span className="text-gildle-text">출발지·도착지 좌표와 산책 요청 문장</span> — 경로를
              계산하는 동안에만 사용하며,{" "}
              <span className="text-gildle-text">서버에 저장하지 않습니다.</span>
            </li>
            <li>
              <span className="text-gildle-text">산책 기록</span> — 로그인한 이용자가 산책을 시작해
              저장하면 걸은 경로의 좌표, 시작·종료 시각, 거리, 소요 시간, 그늘 비율을 계정에
              연결해 저장합니다.
            </li>
            <li>
              위치 권한은 지도에서 현재 위치를 쓸 때와 산책 기록 중에만 사용합니다. 산책 기록
              중에는 알림을 표시한 상태로 화면이 꺼져도 기록을 이어 가며, 산책을 끝내면 즉시
              수집을 멈춥니다. 그 밖의 백그라운드 위치 수집은 하지 않습니다.
            </li>
          </ul>
          <p className="font-medium text-gildle-text">회원 정보(로그인한 경우에만)</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>이메일로 가입: 이메일 주소, 비밀번호(복원할 수 없는 방식으로 암호화해 저장)</li>
            <li>카카오로 로그인: 카카오 계정 고유 식별자, 이메일 주소, 닉네임(카카오가 제공하는 경우)</li>
            <li>푸시 알림용 기기 토큰(알림을 허용한 경우)</li>
          </ul>
          <p>회원가입 없이도 지도와 경로 추천은 이용할 수 있습니다.</p>
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
          <li>경로 계산 좌표·요청 문장: 저장하지 않으므로 보유 기간이 없습니다.</li>
          <li>산책 기록: 이용자가 기록을 삭제하거나 회원 탈퇴할 때까지. 삭제·탈퇴 즉시 파기합니다.</li>
          <li>회원 정보·기기 토큰: 회원 탈퇴 시까지. 탈퇴 즉시 파기합니다.</li>
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
              <span className="text-gildle-text">네이버 클라우드(지도)</span> — 지도 표시. 지도를
              불러오는 과정에서 이용자의 IP와 조회 영역이 전달됩니다.
            </li>
            <li>
              <span className="text-gildle-text">카카오</span> — 카카오 로그인, 경로 주변 반려동물
              장소 검색. 장소 검색 시 경로 중심 좌표와 검색 반경이 전달됩니다(이용자 식별 정보는
              전달하지 않음).
            </li>
            <li>
              <span className="text-gildle-text">Google Firebase</span> — 푸시 알림 전달(기기 토큰).
            </li>
            <li>
              <span className="text-gildle-text">OpenStreetMap</span> — 보행 경로 데이터의 출처(이용자
              정보는 전달하지 않음).
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
          있습니다. 산책 기록은 앱의 기록 화면에서 직접 삭제할 수 있고, 앱의 내 정보 &gt; 회원
          탈퇴로 계정과 모든 산책 기록을 즉시 삭제할 수 있습니다. 앱을 쓸 수 없다면{" "}
          <Link href="/gildle/account-deletion" className="underline underline-offset-2 hover:text-gildle-text">
            계정 삭제 안내
          </Link>
          의 방법으로 요청해 주세요.
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
          법령·서비스 변경에 따라 방침이 바뀔 수 있으며, 변경 시 시행 전에 본 페이지에
          공지합니다.
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
        <p className="mt-2 text-sm text-gildle-muted">본 방침은 2026년 9월 28일부터 적용됩니다(최초 2026년 9월 22일).</p>

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
