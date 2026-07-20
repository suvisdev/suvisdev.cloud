import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "이용약관 — Suvisdev",
  description: "Suvisdev 서비스 이용약관",
}

type Article = { title: string; body: string[] }
type Chapter = { title: string; articles: Article[] }

const CHAPTERS: Chapter[] = [
  {
    title: "제1장 총칙",
    articles: [
      {
        title: "제1조 (목적)",
        body: [
          "이 약관은 Suvisdev(이하 \"회사\")가 제공하는 웹 서비스(이하 \"서비스\")의 이용조건 및 절차, 회사와 회원 간의 권리·의무 및 책임사항을 정함을 목적으로 합니다.",
        ],
      },
      {
        title: "제2조 (용어의 정의)",
        body: [
          "\"회원\"이란 이 약관에 동의하고 아이디를 부여받아 서비스를 이용하는 자를 말합니다.",
          "\"OAuth 로그인\"이란 Google·카카오·네이버 등 외부 서비스(이하 \"프로바이더\")의 인증을 통해 별도의 아이디·비밀번호 생성 없이 회원가입 및 로그인하는 방식을 말합니다.",
        ],
      },
      {
        title: "제3조 (약관의 효력 및 변경)",
        body: [
          "이 약관은 서비스 화면에 게시하거나 기타의 방법으로 공지함으로써 효력이 발생합니다.",
          "회사는 관계 법령을 위반하지 않는 범위에서 이 약관을 개정할 수 있으며, 개정 시 적용일자 및 개정 사유를 명시하여 사전 공지합니다.",
        ],
      },
      {
        title: "제4조 (약관 외 준칙)",
        body: [
          "이 약관에 명시되지 않은 사항은 개인정보 보호법, 정보통신망 이용촉진 및 정보보호 등에 관한 법률 등 관계 법령 및 회사가 정한 개인정보처리방침에 따릅니다.",
        ],
      },
    ],
  },
  {
    title: "제2장 이용계약의 체결",
    articles: [
      {
        title: "제5조 (이용계약의 성립)",
        body: [
          "이용계약은 이용자가 이 약관에 동의하고 회사가 정한 절차에 따라 아이디·비밀번호를 등록하거나, Google·카카오·네이버 OAuth 로그인을 완료함으로써 성립합니다.",
          "OAuth 로그인으로 처음 가입하는 경우, 프로바이더 인증 완료 후 별도의 약관 동의 화면(이용약관 및 개인정보 수집·이용 동의)을 거쳐야 가입이 최종 완료됩니다. 필수 항목에 동의하지 않으면 가입이 완료되지 않습니다.",
        ],
      },
      {
        title: "제6조 (이용신청의 승낙 제한)",
        body: [
          "회사는 다음 각 호에 해당하는 경우 이용 승낙을 하지 않거나 사후에 이용계약을 해지할 수 있습니다.",
          "1. 타인의 명의를 도용하여 신청한 경우",
          "2. 신청 내용에 허위 사실이 있는 경우",
          "3. 이미 회원으로 등록된 프로바이더 계정으로 중복 가입을 시도하는 경우",
        ],
      },
      {
        title: "제7조 (회원정보의 변경)",
        body: [
          "회원은 서비스 내 기능을 통해 자신의 회원정보(닉네임, 이메일 등)를 열람 및 수정할 수 있습니다.",
        ],
      },
    ],
  },
  {
    title: "제3장 계약당사자의 의무",
    articles: [
      {
        title: "제8조 (회사의 의무)",
        body: [
          "회사는 서비스의 제공에 관한 모든 의무와 책임을 부담합니다. Google·카카오·네이버 등 OAuth 프로바이더는 로그인 인증 기능만 제공할 뿐 서비스 자체의 제공 주체가 아니며, 서비스 이용과 관련한 의무와 책임은 회사에 있습니다.",
          "회사는 회원의 개인정보를 개인정보처리방침에 따라 안전하게 관리합니다.",
        ],
      },
      {
        title: "제9조 (회원의 의무)",
        body: [
          "회원은 관계 법령, 이 약관, 서비스 이용안내 및 공지사항을 준수하여야 합니다.",
          "회원은 타인의 계정을 도용하거나 허위 정보를 등록해서는 안 됩니다.",
          "회원은 자신의 계정 및 인증 정보를 선량한 관리자의 주의로 관리하여야 하며, 제3자에게 양도·대여할 수 없습니다.",
        ],
      },
    ],
  },
  {
    title: "제4장 서비스의 이용",
    articles: [
      {
        title: "제10조 (서비스 이용시간)",
        body: ["서비스는 연중무휴, 1일 24시간 제공함을 원칙으로 합니다. 다만 시스템 점검 등 불가피한 사유가 있는 경우 서비스 제공이 일시 중단될 수 있습니다."],
      },
      {
        title: "제11조 (서비스 제공의 중지)",
        body: [
          "회사는 다음 각 호에 해당하는 경우 서비스 제공을 일시 중지할 수 있습니다.",
          "1. 서비스용 설비의 점검·보수 등 공사가 필요한 경우",
          "2. 회사가 이용하는 외부 인프라(호스팅, OAuth 프로바이더 등)의 장애가 발생한 경우",
          "3. 기타 천재지변 등 불가항력적 사유가 있는 경우",
        ],
      },
    ],
  },
  {
    title: "제5장 계약해지 및 이용제한",
    articles: [
      {
        title: "제12조 (계약해지)",
        body: ["회원은 언제든지 서비스 내 회원 탈퇴 기능 또는 회사에 대한 요청을 통해 이용계약을 해지(탈퇴)할 수 있습니다."],
      },
      {
        title: "제13조 (이용제한)",
        body: [
          "회사는 회원이 제9조를 위반하거나 서비스의 정상적인 운영을 방해한 경우, 사전 통지 후(긴급한 경우 사후 통지) 이용을 제한하거나 이용계약을 해지할 수 있습니다.",
        ],
      },
    ],
  },
  {
    title: "제6장 손해배상 등",
    articles: [
      {
        title: "제14조 (면책조항)",
        body: [
          "회사는 천재지변 또는 이에 준하는 불가항력, 회원의 귀책사유, OAuth 프로바이더의 장애 등 회사에 책임 없는 사유로 발생한 서비스 이용 장애에 대해 책임을 지지 않습니다.",
        ],
      },
      {
        title: "제15조 (분쟁해결 및 관할법원)",
        body: ["서비스 이용과 관련하여 분쟁이 발생한 경우, 회사의 주된 사무소 소재지를 관할하는 법원을 전속 관할법원으로 합니다."],
      },
    ],
  },
]

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12 md:px-6">
      <h1 className="text-2xl font-bold tracking-tight text-neutral-900">이용약관</h1>
      <p className="mt-2 text-sm text-neutral-500">
        시행일: 2026-07-20 · 공정거래위원회 표준약관 구조를 참고해 작성했습니다.
      </p>

      <div className="mt-8 space-y-10">
        {CHAPTERS.map((chapter) => (
          <section key={chapter.title}>
            <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-400">
              {chapter.title}
            </h2>
            <div className="mt-3 space-y-5">
              {chapter.articles.map((article) => (
                <div key={article.title}>
                  <h3 className="text-base font-semibold text-neutral-900">{article.title}</h3>
                  <div className="mt-1.5 space-y-1">
                    {article.body.map((line, i) => (
                      <p key={i} className="text-sm leading-relaxed text-neutral-600">
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
        <p className="border-t border-neutral-200 pt-6 text-sm text-neutral-500">
          부칙 — 이 약관은 2026년 7월 20일부터 시행합니다.
        </p>
      </div>
    </div>
  )
}
