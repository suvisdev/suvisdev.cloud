# vision_ocr_scan 하네스 (프론트)

백엔드 하네스는 `suvisdev/_docs/s3-ocr-reverse-harness.md` — S3에 저장된 이미지를
OCR로 읽어 `GET /vision/ocr/scan`이 `[{image_url, extracted_text}]`를 반환하는
read 경로. 이 문서는 그 응답을 **suvis(Next.js) 웹의 지정 화면이 mount 시점에
불러와 렌더링하는 쪽**을 다룬다.

## 전제 — 백엔드 "결정 필요" 3번(인증 여부)이 이 문서를 좌우한다

백엔드 하네스의 "결정 필요" §3(엔드포인트 인증 여부)이 아직 미확정이다. 이
문서는 **인증이 붙는다는 가정**으로 설계한다(사진이 사용자 개인 소유 데이터라
무인증 노출은 `.claude/rules/security/auth.md`가 금지하는 패턴에 가깝다). 백엔드가
최종적으로 무인증으로 확정되면 아래 3계층 토큰 전달 절만 생략하면 된다 — 나머지
구조(프록시, 화면, 상태 관리)는 그대로 유효하다.

인증이 붙는다면 어떤 로그인 세션을 쓸지도 별도 결정 사항이다. 이 저장소는 앱마다
JWT `aud`가 분리돼 있다(`suvis-susu`=susu 모바일, `suvis-mova`=mova 웹 로그인).
현재 suvis 웹에서 실제로 동작하는 로그인은 mova 로그인(`aud=suvis-mova`)뿐이라,
이 화면도 그 세션을 재사용하는 편이 새 로그인 표면을 만드는 것보다 스코프가
작다 — 다만 이것도 백엔드가 `vision/ocr/scan`에 어떤 `aud`를 요구할지에 달려
있으므로 착수 전 확정한다.

---

## 스코프

- **포함**: 지정 화면 mount → `GET /vision/ocr/scan` 프록시 호출 → 목록 렌더
- **제외**: 사진 촬영·업로드 UI(susu 쪽), OCR 엔진·S3 스캔 자체(백엔드 하네스)

---

## 레이어 (이 저장소의 실측 3계층 프록시 패턴)

`.claude/rules/api-standards.md` 기준, 인증이 필요한 백엔드 호출은 항상 세 층을
거친다:

```
클라이언트 컴포넌트 → lib/vision-api.ts → app/api/vision/ocr-scan/route.ts → FastAPI
```

### 1. `lib/vision-api.ts` (신규)

`suvis/lib/harvester-api.ts`를 그대로 참조한다 — 파일당 fetch 래퍼 하나, 인증
토큰은 있을 때만 헤더에 싣는다(빈 문자열 금지).

```ts
import { authHeader } from "@/lib/suvis-session"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

export type OcrScanItem = {
  image_url: string
  extracted_text: string
}

type ApiErrorBody = { detail?: string | unknown }

export async function getOcrScan(): Promise<OcrScanItem[]> {
  const res = await fetch("/api/vision/ocr-scan", { headers: authHeader() })
  const data = (await res.json()) as OcrScanItem[] & ApiErrorBody
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, "사진을 불러오지 못했습니다.", res.status))
  }
  return data
}
```

> `authHeader()`가 실제로 `suvis-session.ts`에 있는지, 아니면 각 `lib/*-api.ts`가
> `getSuvisSession()?.token`을 직접 꺼내 조립하는지(`admin-api.ts` 패턴)는 착수 시
> `suvis/lib/suvis-session.ts`를 확인하고 기존 관례를 따른다 — 이 문서가 임의로
> 새 헬퍼를 도입하지 않는다.

### 2. `app/api/vision/ocr-scan/route.ts` (신규)

`.claude/rules/api-standards.md` §5 그대로: 받은 `Authorization` 헤더를 그대로
백엔드로 넘기고, 업스트림 호출만 `try/catch` 한 겹으로 감싼다.

```ts
import { NextResponse } from "next/server"

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://127.0.0.1:8000"

export async function GET(req: Request) {
  const auth = req.headers.get("authorization")
  try {
    const res = await fetch(`${API_BASE}/vision/ocr/scan`, {
      headers: auth ? { Authorization: auth } : {},
    })
    const body = await res.json().catch(() => ({}))
    return NextResponse.json(body, { status: res.status })
  } catch {
    return NextResponse.json({ error: "서버에 연결할 수 없습니다." }, { status: 502 })
  }
}
```

백엔드가 무인증으로 확정되면 `auth`/`Authorization` 관련 두 줄만 제거한다.

### 3. 화면 컴포넌트 (신규, 배치 위치는 착수 시 결정)

- `react-rules.md`의 "여러 `useState` 금지" 원칙에 따라 로딩/에러/데이터를
  한 객체로 묶는다(§2 `FormStatus` 패턴과 동형이나, 이건 서버 데이터 fetch라
  "폼 상태"는 아니다 — `suvis/lib/form-status.ts`를 그대로 재사용하지 않고
  화면 전용 타입을 둔다).
- mount 시 호출이므로 `useEffect` + 아래 상태 하나로 충분하다. `useState`를
  `loading`/`error`/`items`로 3개 쪼개지 않는다.

```tsx
type ScanState = {
  status: "loading" | "error" | "ready"
  items: OcrScanItem[]
  message: string | null
}

const [scan, setScan] = useState<ScanState>({ status: "loading", items: [], message: null })

useEffect(() => {
  let cancelled = false
  getOcrScan()
    .then((items) => {
      if (!cancelled) setScan({ status: "ready", items, message: null })
    })
    .catch((e) => {
      if (!cancelled) {
        setScan({
          status: "error",
          items: [],
          message: e instanceof Error ? e.message : "사진을 불러오지 못했습니다.",
        })
      }
    })
  return () => {
    cancelled = true
  }
}, [])
```

- 렌더 분기는 `react-rules.md` §9 기준 — 중첩 삼항 대신 `status`별 early
  return을 쓰는 별도 함수/컴포넌트로 쪼갠다(`loading` → 스피너, `error` →
  `scan.message` 표시, `ready` && 빈 배열 → Empty, 그 외 → 목록).
- 목록 아이템은 `image_url`(presigned, 브라우저가 S3 직접 fetch — `next/image`를
  쓴다면 `next.config`의 `images.remotePatterns`에 S3 버킷 도메인을 추가해야
  한다는 점을 착수 시 확인) + `extracted_text`.
- `error` 메시지는 `safeApiErrorMessage`를 이미 `lib/vision-api.ts`에서 거쳤으므로
  화면에서 추가 가공 없이 그대로 표시(§6: `alert`/`JSON.stringify` 금지).

---

## 결정 필요 (착수 전, 백엔드 문서와 연동)

1. 백엔드 인증 여부 확정에 맞춰 §1 위 3계층 중 어느 정도까지 만들지(무인증이면
   `route.ts` 프록시조차 얇아지고 `authHeader()` 관련 코드가 빠진다).
2. 인증이 붙는다면 어떤 로그인 세션(`aud`)을 재사용할지 — 위 "전제" 절 참조.
3. 이 화면이 어디에 걸리는지(신규 페이지 `app/.../page.tsx`인지, 기존 화면에
   섹션으로 얹는지) — 백엔드 하네스의 "스캔 대상 S3 경로" 결정과 맞물린다
   (예: `media/{user_id}/` prefix를 스캔하기로 하면 "내 사진" 성격의 화면일
   가능성이 높고, 로그인 사용자 소유 데이터이므로 무인증 노출은 더 위험해진다).

---

## 참조 구현 (필수 정독)

| 파일 | 참조 이유 |
|------|-----------|
| `suvis/lib/harvester-api.ts` | `lib/*-api.ts` fetch 래퍼 관례 |
| `suvis/_docs/react-rules.md` §2, §9, §10 | 상태 압축, 분기, try/catch 경계 |
| `.claude/rules/api-standards.md` | 프록시 라우트 표준(에러 응답 형태, 3계층 토큰) |
| `.claude/rules/security/auth.md` | 무인증 엔드포인트를 프론트가 그대로 호출하고 있지 않은지 체크리스트 |
| `.claude/rules/typescript.md` | `any` 금지, `type` 우선, non-null 단언 금지 등 |
