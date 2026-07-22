"use client"

/** auth 게이트웨이(auth.suvisdev.cloud) 로그인 연동 테스트 전용 페이지.
 * 기존 메인 로그인 버튼(/login, viewer 연동)과는 완전히 별개 — 그쪽은 건드리지 않는다. */
export default function TestAuthLoginPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
        auth 게이트웨이 로그인 테스트
      </h1>
      <p className="max-w-md text-sm text-neutral-600 dark:text-neutral-400">
        기존 로그인과 무관한 테스트 버튼입니다. Google 로그인 → auth.suvisdev.cloud 콜백 →
        발급된 토큰으로 /mova/whoami 호출까지 확인합니다.
      </p>
      <button
        type="button"
        onClick={() => {
          window.location.href =
            "https://auth.suvisdev.cloud/auth/login/google?aud=suvis-mova"
        }}
        className="rounded-2xl bg-[#f0dc3a] px-6 py-3 font-bold text-neutral-900 shadow-sm hover:bg-[#e8d020]"
      >
        Google로 테스트 로그인
      </button>
    </div>
  )
}
