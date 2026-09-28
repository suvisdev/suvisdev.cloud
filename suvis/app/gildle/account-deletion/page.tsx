import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "계정 삭제 안내 — 길들",
  description: "길들(gildle) 계정과 산책 기록을 삭제하는 방법",
}

// Google Play 계정 삭제 정책용 공개 페이지(2026-09-28). 스토어의 "계정 삭제 URL"에 이 주소를 넣는다.
// 앱 안의 탈퇴(내 정보 > 회원 탈퇴)와 같은 범위를 삭제한다는 점이 서로 맞아야 한다.
export default function GildleAccountDeletionPage() {
  return (
    <main className="gildle-nature-bg min-h-screen">
      <div className="mx-auto max-w-3xl px-4 py-10 md:px-6 md:py-14">
        <Link href="/gildle" className="text-gildle-muted hover:text-gildle-text text-xs">
          ← 길들
        </Link>
        <h1 className="text-gildle-text mt-4 text-2xl font-bold tracking-tight">
          길들 계정 삭제 안내
        </h1>
        <p className="text-gildle-muted mt-2 text-sm">
          길들(개발자: suvisdev) 계정과 산책 기록을 삭제하는 방법입니다.
        </p>

        <div className="text-gildle-muted mt-8 space-y-8 text-sm leading-relaxed">
          <section>
            <h2 className="text-gildle-text text-base font-semibold">1. 앱에서 바로 삭제하기</h2>
            <ol className="mt-2 list-decimal space-y-1 pl-5">
              <li>길들 앱을 열고 로그인합니다.</li>
              <li>아래 탭에서 &quot;내 정보&quot;를 누릅니다.</li>
              <li>&quot;회원 탈퇴&quot;를 누르고 확인하면 즉시 삭제됩니다.</li>
            </ol>
          </section>

          <section>
            <h2 className="text-gildle-text text-base font-semibold">2. 앱 없이 요청하기</h2>
            <p className="mt-2">
              앱을 지웠거나 로그인할 수 없다면{" "}
              <a
                className="hover:text-gildle-text underline underline-offset-2"
                href="mailto:ssuvisdev@gmail.com?subject=%5B%EA%B8%B8%EB%93%A4%5D%20%EA%B3%84%EC%A0%95%20%EC%82%AD%EC%A0%9C%20%EC%9A%94%EC%B2%AD"
              >
                ssuvisdev@gmail.com
              </a>
              으로 &quot;[길들] 계정 삭제 요청&quot;을 보내 주세요. 가입한 이메일 주소(카카오로
              로그인했다면 카카오 닉네임)를 적어 주시면 본인 확인 후 7일 안에 삭제하고 결과를
              회신합니다.
            </p>
          </section>

          <section>
            <h2 className="text-gildle-text text-base font-semibold">3. 삭제되는 정보</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>계정 정보: 이메일 주소, 암호화된 비밀번호, 카카오 연동 정보, 닉네임</li>
              <li>산책 기록 전부: 걸은 경로 좌표, 시각, 거리, 소요 시간, 그늘 비율</li>
              <li>푸시 알림용 기기 토큰</li>
            </ul>
            <p className="mt-2">
              삭제는 즉시 이루어지며 되돌릴 수 없습니다. 계정을 지우지 않고 산책 기록만 지우려면
              앱의 기록 화면에서 기록별로 삭제할 수 있습니다.
            </p>
          </section>

          <section>
            <h2 className="text-gildle-text text-base font-semibold">4. 보관되는 정보</h2>
            <p className="mt-2">
              서비스 오류 진단용 서버 접속 기록(IP 주소 등)은 계정과 연결되지 않은 형태로 최대 3개월
              보관 후 삭제됩니다. 그 밖에 따로 보관하는 정보는 없습니다. 자세한 내용은{" "}
              <Link
                href="/gildle/privacy"
                className="hover:text-gildle-text underline underline-offset-2"
              >
                개인정보처리방침
              </Link>
              을 확인해 주세요.
            </p>
          </section>
        </div>
      </div>
    </main>
  )
}
