import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "개인정보처리방침 — Mova",
  description: "Mova 개인정보처리방침",
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

const SERVICE_DATA_ITEMS = [
  "리뷰·평점·코멘트: 회원이 작성한 텍스트, 평점, 스포일러 여부, 작성 시각",
  "관심 콘텐츠: 보고싶어요·봤어요·관심없음 등 watchlist 상태",
  "취향: 회원이 선택한 선호 장르, AI 채팅 대화 이력 및 mood 태그",
  "미니게임 랭킹: 게임 종류, 점수, 플레이 시각",
  "프로필: 닉네임, 프로필 이미지",
]

const AUTO_DATA_ITEMS = [
  "접속 로그, 접속 IP 주소, 쿠키, User-Agent",
  "서비스 이용 이력(방문 페이지, 검색어, 클릭한 콘텐츠)",
  "기기 정보(모델명, OS 정보, 브라우저 정보)",
]

export default function MovaPrivacyPage() {
  const sections: Section[] = [
    {
      title: "1. 개인정보의 처리 목적",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          Suvisdev(이하 &quot;회사&quot;)는 Mova(이하 &quot;서비스&quot;)에서 회원 식별 및 로그인,
          서비스 부정이용 방지, 문의 응대, 맞춤형 서비스(영화·시리즈 추천, 취향 분석, 미니게임 랭킹
          제공 등) 제공을 목적으로 개인정보를 처리합니다. 목적이 변경되는 경우 「개인정보 보호법」
          제18조에 따라 별도의 동의를 받는 등 필요한 조치를 이행합니다.
        </p>
      ),
    },
    {
      title: "2. 처리하는 개인정보의 항목",
      body: (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-semibold text-mova-text">아이디/비밀번호 직접 가입</p>
            <p className="mt-1 text-sm text-mova-muted">아이디, 비밀번호, 닉네임, 이메일</p>
          </div>
          <p className="text-sm font-semibold text-mova-text">
            OAuth 로그인(Google · 카카오 · 네이버)
          </p>
          <div className="space-y-3">
            {OAUTH_PROVIDERS.map((provider) => (
              <div key={provider.name} className="rounded-xl border border-mova-border bg-mova-surface p-4">
                <p className="text-sm font-semibold text-mova-text">{provider.name}</p>
                <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-sm text-mova-muted">
                  {provider.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <p className="mt-2 text-xs leading-relaxed text-neutral-500">{provider.note}</p>
              </div>
            ))}
          </div>
          <div>
            <p className="text-sm font-semibold text-mova-text">서비스 이용 과정에서 생성되는 정보</p>
            <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-sm text-mova-muted">
              {SERVICE_DATA_ITEMS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold text-mova-text">자동으로 수집되는 정보</p>
            <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-sm text-mova-muted">
              {AUTO_DATA_ITEMS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="mt-2 text-xs leading-relaxed text-neutral-500">
              자동 수집 정보는 개인을 식별할 수 없는 형태이며, 회사는 이를 활용하여 개인을 식별하기
              위한 활동을 하지 않습니다.
            </p>
          </div>
        </div>
      ),
    },
    {
      title: "3. 개인정보의 처리 및 보유 기간",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          회원 탈퇴 시까지 보유하며, 탈퇴 시 지체 없이 파기합니다. 다만 관계 법령에서 별도로 보관
          기간을 정한 경우(웹사이트 방문기록 3개월 등) 그 기간 동안 보관합니다. 로그인 세션은 아래
          4항의 기간 동안만 보유합니다.
        </p>
      ),
    },
    {
      title: "4. 로그인 세션(자동 수집 장치) 관리",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          로그인 완료 시 회사가 자체 발급하는 세션 토큰(JWT)을 최대 7일간 보관하며, 로그아웃 또는
          만료 시 자동 삭제됩니다. OAuth 인증 진행 중 위조 방지(CSRF 방지)를 위한 임시 쿠키(state)를
          최대 10분간 사용하며, 인증 완료 즉시 삭제됩니다.
        </p>
      ),
    },
    {
      title: "5. 개인정보의 파기 절차 및 방법",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          전자적 파일 형태로 저장된 개인정보는 복구·재생이 불가능한 방법으로 영구 삭제합니다. 회원이
          작성한 리뷰·평점 등의 게시물은 회원 탈퇴 시 함께 삭제됩니다. 다만, 관계 법령을 위반한
          회원의 경우 관계 법령이 허용하는 한도에서 회원 정보를 보관할 수 있습니다.
        </p>
      ),
    },
    {
      title: "6. 개인정보의 제3자 제공",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          회사는 회원의 개인정보를 원칙적으로 외부에 제공하지 않습니다. OAuth 프로바이더(Google·
          카카오·네이버)로부터 정보를 &quot;제공받는&quot; 것이며, 회사가 이들에게 회원 정보를 다시
          제공하지 않습니다. 법령에 근거하거나 수사기관의 적법한 요청이 있는 경우는 예외로 합니다.
        </p>
      ),
    },
    {
      title: "7. 개인정보 처리의 위탁 및 국외 이전",
      body: (
        <div className="space-y-3">
          <p className="text-sm leading-relaxed text-mova-muted">
            회사는 서비스 운영을 위해 다음과 같은 외부 서비스를 이용할 수 있으며, 이 경우 처리 위탁
            및 국외 이전이 수반될 수 있습니다.
          </p>
          <ul className="list-inside list-disc space-y-1 text-sm text-mova-muted">
            <li>
              <span className="font-semibold text-mova-text">Amazon Web Services (AWS, 서울 리전)</span>
              {" — "}데이터베이스 및 서버 호스팅
            </li>
            <li>
              <span className="font-semibold text-mova-text">Google LLC (Google OAuth · Gemini API)</span>
              {" — "}로그인 인증 및 AI 채팅 응답 생성(사용자의 채팅 입력이 Gemini API로 전송될 수 있음)
            </li>
            <li>
              <span className="font-semibold text-mova-text">Kakao · Naver</span>
              {" — "}로그인 인증
            </li>
          </ul>
          <p className="text-xs leading-relaxed text-neutral-500">
            위탁·이전 대상자가 변경되는 경우 이 방침을 통해 공개합니다.
          </p>
        </div>
      ),
    },
    {
      title: "8. 외부 데이터 소스",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          서비스가 표시하는 영화 메타데이터(포스터, 줄거리, 출연진, 개봉일, 평점 등)의 상당수는{" "}
          <a
            href="https://www.themoviedb.org"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-mova-text"
          >
            The Movie Database (TMDB)
          </a>{" "}
          및 영화진흥위원회(KOFIC) 등 공개 데이터 소스로부터 제공받아 표시됩니다. 이는 회원의
          개인정보에 해당하지 않으며, 회사는 해당 외부 데이터에 회원의 개인정보를 결합하지 않습니다.
          본 서비스는 TMDB API를 사용하나 TMDB에 의해 승인되거나 인증되지 않습니다.
        </p>
      ),
    },
    {
      title: "9. 광고 및 맞춤형 광고",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          본 서비스는 현재 광고를 표시하지 않으며, 광고 목적의 행태정보를 수집하거나 제3자에게
          제공하지 않습니다. 향후 광고를 도입하는 경우 별도의 고지 및 동의 절차를 거칩니다.
        </p>
      ),
    },
    {
      title: "10. 개인정보의 안전성 확보 조치",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          비밀번호는 복호화 불가능한 방식으로 암호화하여 저장하며, 세션 토큰은 서명 검증을 거쳐
          위·변조를 방지합니다. 개인정보에 대한 접근은 최소 권한 원칙에 따라 제한하며, 저장소는 접근
          통제된 클라우드 인프라(AWS 서울 리전) 위에서 운영합니다.
        </p>
      ),
    },
    {
      title: "11. 만 14세 미만 아동의 개인정보",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          회사는 만 14세 미만 아동의 회원가입을 원칙적으로 받지 않으며, 별도의 확인 없이 아동임이
          확인된 경우 해당 계정 및 개인정보는 즉시 파기됩니다.
        </p>
      ),
    },
    {
      title: "12. 정보주체의 권리·의무 및 행사 방법",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          회원은 언제든지 자신의 개인정보를 열람·정정·삭제하거나 처리 정지를 요구할 수 있으며, 회원
          탈퇴를 통해 동의를 철회할 수 있습니다. 권리 행사는 마이페이지 또는 이메일(
          <a href="mailto:ssuvisdev@gmail.com" className="underline underline-offset-2 hover:text-mova-text">
            ssuvisdev@gmail.com
          </a>
          )을 통해 진행할 수 있습니다.
        </p>
      ),
    },
    {
      title: "13. 개인정보 보호책임자",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          개인정보 관련 문의·불만처리·피해구제 등을 위해 이메일(
          <a href="mailto:ssuvisdev@gmail.com" className="underline underline-offset-2 hover:text-mova-text">
            ssuvisdev@gmail.com
          </a>
          )로 개인정보 보호책임자에게 연락할 수 있습니다.
        </p>
      ),
    },
    {
      title: "14. 권익침해에 대한 구제 방법",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          개인정보 침해에 대한 신고나 상담이 필요한 경우 아래 기관에 문의할 수 있습니다.
          개인정보보호위원회(privacy.go.kr / 국번없이 182), 개인정보 침해신고센터
          (privacy.go.kr / 국번없이 182), 대검찰청 사이버범죄수사단(spo.go.kr / 국번없이 1301),
          경찰청 사이버수사국(ecrm.police.go.kr / 국번없이 182).
        </p>
      ),
    },
    {
      title: "15. 개인정보처리방침의 변경",
      body: (
        <p className="text-sm leading-relaxed text-mova-muted">
          이 방침은 법령·정책 변경에 따라 개정될 수 있으며, 개정 시 시행일자 및 변경 사항을 이
          페이지를 통해 공지합니다.
        </p>
      ),
    },
  ]

  return (
    <>
      <main className="mx-auto max-w-3xl px-4 py-10 md:px-6 md:py-14">
        <h1 className="text-2xl font-bold tracking-tight text-mova-text">개인정보처리방침</h1>
        <p className="mt-2 text-sm text-mova-muted">본 방침은 2026년 8월 14일부터 적용됩니다.</p>

        <div className="mt-8 space-y-8">
          {sections.map((section) => (
            <section key={section.title}>
              <h2 className="text-base font-semibold text-mova-text">{section.title}</h2>
              <div className="mt-2">{section.body}</div>
            </section>
          ))}
        </div>
      </main>
    </>
  )
}
