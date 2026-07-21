"use client"

type OAuthProvider = "google" | "naver" | "kakao"

type OAuthButtonsProps = {
  /** 백엔드에 실제 로그인 라우트가 연결된 프로바이더 (window.location 이동) */
  onSelect?: (provider: OAuthProvider) => void
}

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://127.0.0.1:8000"

/** 백엔드 /viewer/oauth/{provider}/login이 실제로 연결된 프로바이더. */
const LIVE_PROVIDERS: ReadonlySet<OAuthProvider> = new Set(["google", "kakao", "naver"])

function GoogleIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-4.5 w-4.5" aria-hidden>
      <path
        fill="#4285F4"
        d="M19.6 10.23c0-.68-.06-1.33-.17-1.96H10v3.71h5.38a4.6 4.6 0 0 1-2 3.02v2.5h3.23c1.89-1.74 2.99-4.3 2.99-7.27Z"
      />
      <path
        fill="#34A853"
        d="M10 20c2.7 0 4.96-.89 6.61-2.42l-3.23-2.5c-.9.6-2.04.96-3.38.96-2.6 0-4.8-1.76-5.59-4.12H1.07v2.59A10 10 0 0 0 10 20Z"
      />
      <path
        fill="#FBBC05"
        d="M4.41 11.92a5.99 5.99 0 0 1 0-3.84V5.49H1.07a10 10 0 0 0 0 9.02l3.34-2.59Z"
      />
      <path
        fill="#EA4335"
        d="M10 3.96c1.47 0 2.79.5 3.83 1.5l2.87-2.87A9.55 9.55 0 0 0 10 0 10 10 0 0 0 1.07 5.49l3.34 2.59C5.2 5.72 7.4 3.96 10 3.96Z"
      />
    </svg>
  )
}

function NaverIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden>
      <path fill="#fff" d="M11.6 10.6 8.1 5.3H5.3v9.4h3.1v-5.3l3.5 5.3h2.8V5.3h-3.1z" />
    </svg>
  )
}

function KakaoIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-4.5 w-4.5" aria-hidden>
      <path
        fill="#191919"
        d="M10 2.5c-4.42 0-8 2.79-8 6.24 0 2.2 1.46 4.14 3.66 5.25-.16.58-.58 2.1-.66 2.43-.1.4.15.4.31.29.13-.09 2.06-1.39 2.9-1.96.58.08 1.17.13 1.79.13 4.42 0 8-2.8 8-6.24s-3.58-6.14-8-6.14Z"
      />
    </svg>
  )
}

const PROVIDERS: {
  id: OAuthProvider
  label: string
  className: string
  icon: () => React.ReactElement
}[] = [
  {
    id: "google",
    label: "Google로 계속하기",
    className:
      "border border-neutral-300 bg-white text-neutral-800 hover:bg-neutral-50",
    icon: GoogleIcon,
  },
  {
    id: "naver",
    label: "네이버로 계속하기",
    className: "border border-transparent bg-[#03C75A] text-white hover:bg-[#02b350]",
    icon: NaverIcon,
  },
  {
    id: "kakao",
    label: "카카오로 계속하기",
    className: "border border-transparent bg-[#FEE500] text-[#191919] hover:bg-[#f5dc00]",
    icon: KakaoIcon,
  },
]

export function OAuthButtons({ onSelect }: OAuthButtonsProps) {
  const handleClick = (id: OAuthProvider) => {
    if (LIVE_PROVIDERS.has(id)) {
      window.location.href = `${API_BASE}/viewer/oauth/${id}/login`
      return
    }
    onSelect?.(id)
  }

  return (
    <div className="space-y-2.5">
      {PROVIDERS.map(({ id, label, className, icon: Icon }) => (
        <button
          key={id}
          type="button"
          onClick={() => handleClick(id)}
          className={`flex w-full items-center justify-center gap-2.5 rounded-2xl px-4 py-2.5 text-sm font-semibold shadow-sm transition-colors ${className}`}
        >
          <Icon />
          {label}
        </button>
      ))}
    </div>
  )
}

export type { OAuthProvider }
