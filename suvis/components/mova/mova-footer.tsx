import Link from "next/link"

export function MovaFooter() {
  return (
    <footer className="mt-auto border-t border-mova-border bg-mova-surface/60">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-1 px-4 py-3 md:px-6">
        <nav className="flex flex-col gap-0.5 text-[10px] text-mova-muted md:flex-row md:flex-wrap md:items-center md:gap-x-2 md:gap-y-0.5">
          <Link href="/mova/terms" className="hover:text-mova-text">
            이용약관
          </Link>
          <span className="hidden text-neutral-600 md:inline" aria-hidden>
            ·
          </span>
          <Link href="/mova/privacy" className="hover:text-mova-text">
            개인정보 처리방침
          </Link>
          <span className="hidden text-neutral-600 md:inline" aria-hidden>
            ·
          </span>
          <a href="mailto:ssuvisdev@gmail.com" className="hover:text-mova-text">
            문의
          </a>
        </nav>

        {/* TMDB 약관은 로고 표시 + 고지 문구를 요구한다. 로고는 "내 서비스 로고보다
            덜 눈에 띄게"가 조건이라 short 변형을 작은 높이로 쓴다. */}
        <div className="flex items-start gap-2">
          <a
            href="https://www.themoviedb.org"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="The Movie Database"
            className="mt-[2px] shrink-0"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/tmdb-logo.svg" alt="TMDB" width={52} height={7} className="h-[7px] w-auto opacity-70" />
          </a>
          <p className="text-[10px] leading-relaxed text-mova-muted">
            Movie data provided by TMDB. This product uses TMDB and the TMDB APIs but is not
            endorsed, certified, or otherwise approved by TMDB.
          </p>
        </div>

        <p className="text-[10px] text-neutral-500">© 2026 SUVIS · mova</p>
      </div>
    </footer>
  )
}
