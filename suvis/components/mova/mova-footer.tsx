import Link from "next/link"

export function MovaFooter() {
  return (
    <footer className="mt-auto border-t border-mova-border bg-mova-surface/60">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-2 px-4 py-4 md:px-6 md:py-5">
        <nav className="flex flex-col gap-1 text-xs text-mova-muted md:flex-row md:flex-wrap md:items-center md:gap-x-3 md:gap-y-1">
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

        <p className="text-[11px] leading-relaxed text-mova-muted">
          Movie data provided by{" "}
          <a
            href="https://www.themoviedb.org"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-mova-text"
          >
            TMDB
          </a>
          . This product uses the TMDB API but is not endorsed or certified by TMDB.
        </p>

        <p className="text-[11px] text-neutral-500">© 2026 SUVIS · mova</p>
      </div>
    </footer>
  )
}
