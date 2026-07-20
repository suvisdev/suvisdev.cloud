import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "개인정보처리방침 — Suvisdev",
  description: "Suvisdev 개인정보처리방침",
}

const OAUTH_PROVIDERS: { name: string; items: string[]; note: string }[] = [
  {
    name: "Google",
    items: ["이메일 주소", "이름", "Google 계정 고유 식별자(sub)"],
    note: "Google OAuth(OIDC) id_token에서 scope=openid email profile로 제공받는 항목만 수집합니다.",
  },
  {
    name: "카카오",
    items: ["이메일 주소(카카오 동의항목에 포함된 경우)", "닉네임", "카카오 계정 고유 식별자(sub)"],
    note: "카카오 OAuth(OIDC) id_token에서 scope=openid로 제공받는 항목만 수집합니다.",
  },
  {
    name: "네이버",
    items: ["이메일 주소", "이름/닉네임", "네이버 계정 고유 식별자(id)"],
    note: "네이버는 OIDC id_token을 제공하지 않아 네이버 프로필 API(/v1/nid/me) 응답에서 위 항목만 읽습니다. 실제 제공 항목은 네이버 개발자센터에 등록된 이 서비스의 동의항목 설정에 따라 달라질 수 있습니다.",
  },
]

type Section = { title: string; body: React.ReactNode }

export default function PrivacyPage() {
  const sections: Section[] = [
    {
      title: "1. 개인정보의 처리 목적",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          Suvisdev(이하 &quot;회사&quot;)는 회원 식별 및 로그인, 서비스 부정이용 방지, 문의 응대,
          맞춤형 서비스(콘텐츠 추천 등) 제공을 목적으로 개인정보를 처리합니다. 목적이 변경되는
          경우 「개인정보 보호법」 제18조에 따라 별도의 동의를 받는 등 필요한 조치를 이행합니다.
        </p>
      ),
    },
    {
      title: "2. 처리하는 개인정보의 항목",
      body: (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-semibold text-neutral-800">아이디/비밀번호 직접 가입</p>
            <p className="mt-1 text-sm text-neutral-600">아이디, 비밀번호, 닉네임, 이메일</p>
          </div>
          <p className="text-sm font-semibold text-neutral-800">
            OAuth 로그인(Google · 카카오 · 네이버)
          </p>
          <div className="space-y-3">
            {OAUTH_PROVIDERS.map((provider) => (
              <div key={provider.name} className="rounded-xl border border-neutral-200 p-4">
                <p className="text-sm font-semibold text-neutral-900">{provider.name}</p>
                <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-sm text-neutral-600">
                  {provider.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <p className="mt-2 text-xs leading-relaxed text-neutral-400">{provider.note}</p>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    {
      title: "3. 개인정보의 처리 및 보유 기간",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          회원 탈퇴 시까지 보유하며, 탈퇴 시 지체 없이 파기합니다. 다만 관계 법령에서 별도로 보관
          기간을 정한 경우 그 기간 동안 보관합니다. 로그인 세션은 아래 4항의 기간 동안만 보유합니다.
        </p>
      ),
    },
    {
      title: "4. 로그인 세션(자동 수집 장치) 관리",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          OAuth 로그인 완료 시 회사가 자체 발급하는 세션 토큰(JWT)을 서버(Redis)에 최대 7일간
          보관하며, 로그아웃 또는 만료 시 자동 삭제됩니다. OAuth 인증 진행 중 위조 방지(CSRF
          방지)를 위한 임시 쿠키(state)를 최대 10분간 사용하며, 인증 완료 즉시 삭제됩니다.
        </p>
      ),
    },
    {
      title: "5. 개인정보의 파기 절차 및 방법",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          전자적 파일 형태로 저장된 개인정보는 복구·재생이 불가능한 방법으로 영구 삭제합니다.
        </p>
      ),
    },
    {
      title: "6. 개인정보의 제3자 제공",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          회사는 회원의 개인정보를 원칙적으로 외부에 제공하지 않습니다. OAuth 프로바이더(Google·
          카카오·네이버)로부터 정보를 &quot;제공받는&quot; 것이며, 회사가 이들에게 회원 정보를 다시
          제공하지 않습니다. 법령에 근거하거나 수사기관의 적법한 요청이 있는 경우는 예외로 합니다.
        </p>
      ),
    },
    {
      title: "7. 개인정보 처리의 위탁 및 국외 이전",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          회사는 서비스 운영을 위해 클라우드 인프라(데이터베이스·서버 호스팅) 및 Google OAuth·
          Gemini API 등 해외 사업자가 제공하는 서비스를 이용할 수 있으며, 이 경우 처리 위탁 및
          국외 이전이 수반될 수 있습니다. 위탁·이전 대상자가 변경되는 경우 이 방침을 통해 공개합니다.
        </p>
      ),
    },
    {
      title: "8. 개인정보의 안전성 확보 조치",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          비밀번호는 복호화 불가능한 방식으로 암호화하여 저장하며, 세션 토큰은 서명 검증을 거쳐
          위·변조를 방지합니다. 개인정보에 대한 접근은 최소 권한 원칙에 따라 제한합니다.
        </p>
      ),
    },
    {
      title: "9. 정보주체의 권리·의무 및 행사 방법",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          회원은 언제든지 자신의 개인정보를 열람·정정·삭제하거나 처리 정지를 요구할 수 있으며,
          회원 탈퇴를 통해 동의를 철회할 수 있습니다. 권리 행사는 서비스 내 기능 또는 아래
          개인정보 보호책임자에게 문의하여 진행할 수 있습니다.
        </p>
      ),
    },
    {
      title: "10. 개인정보 보호책임자",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          개인정보 관련 문의·불만처리·피해구제 등을 위해{" "}
          <a href="/contact" className="underline underline-offset-2">
            연락처 페이지
          </a>
          를 통해 개인정보 보호책임자에게 연락할 수 있습니다.
        </p>
      ),
    },
    {
      title: "11. 권익침해에 대한 구제 방법",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          개인정보 침해에 대한 신고나 상담이 필요한 경우 아래 기관에 문의할 수 있습니다.
          개인정보보호위원회(privacy.go.kr / 국번없이 182), 개인정보 침해신고센터
          (privacy.go.kr / 국번없이 182), 대검찰청 사이버범죄수사단(spo.go.kr / 국번없이 1301),
          경찰청 사이버수사국(ecrm.police.go.kr / 국번없이 182).
        </p>
      ),
    },
    {
      title: "12. 개인정보처리방침의 변경",
      body: (
        <p className="text-sm leading-relaxed text-neutral-600">
          이 방침은 법령·정책 변경에 따라 개정될 수 있으며, 개정 시 시행일자 및 변경 사항을 이
          페이지를 통해 공지합니다.
        </p>
      ),
    },
  ]

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 md:px-6">
      <h1 className="text-2xl font-bold tracking-tight text-neutral-900">개인정보처리방침</h1>
      <p className="mt-2 text-sm text-neutral-500">
        시행일: 2026-07-20 · 개인정보보호위원회 「개인정보 처리방침 작성지침(2025.4.)」의
        필수 기재사항 구조를 참고해 작성했습니다.
      </p>

      <div className="mt-8 space-y-8">
        {sections.map((section) => (
          <section key={section.title}>
            <h2 className="text-base font-semibold text-neutral-900">{section.title}</h2>
            <div className="mt-2">{section.body}</div>
          </section>
        ))}
      </div>
    </div>
  )
}
