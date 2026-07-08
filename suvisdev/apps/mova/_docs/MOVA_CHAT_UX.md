# Mova AI 채팅 UX (프론트)

> **역할:** `/mova` 랜딩·`/mova/main` 메인의 AI 추천 채팅 UI 동작 정의.  
> **상위:** `CLAUDE.md` (동일 폴더)  
> **백엔드 API:** `POST /mova/chat` — Mova CLAUDE C절 · `MOVA_ERD.md` 채팅 추천 흐름

---

## 관련 파일 (suvis)

| 역할 | 경로 |
|------|------|
| 메인 채팅 패널 | `suvis/components/mova/mova-ai-chat-bar.tsx` |
| 랜딩 검색 바 | `suvis/components/mova/mova-landing-chat-bar.tsx` |
| 일일 추천 문구 | `suvis/lib/mova-chat-suggestions.ts` |
| API 프록시 | `suvis/app/api/mova/chat/route.ts` |

---

## 사용자 흐름

```text
/mova (랜딩) — MovaLandingChatBar
  → 힌트 클릭 또는 입력 후 전송
  → /mova/main?q={질문} 이동

/mova/main — MovaAiChatBar
  → ?q= 있으면 1회 자동 전송 (히스토리 복원 시 생략)
  → POST /api/mova/chat → 추천 카드 3편 + intro 텍스트
```

---

## 채팅 상태·영속성

| 항목 | 값 |
|------|-----|
| 저장소 | `sessionStorage` |
| 키 | `mova-ai-chat-history-v1` |
| 저장 내용 | `{ messages: ChatMessage[] }` |
| 범위 | **탭·세션** 단위 (브라우저 닫으면 초기화) |

### 복원 시 동작

- 저장된 `messages`가 있으면 마운트 시 복원한다.
- 복원된 히스토리에 **사용자 메시지가 1건 이상** 있으면 `?q=` 자동 전송을 하지 않는다 (`autoSentRef`).
- 페이지 이동 후 돌아와도 대화·추천 카드가 유지된다.

---

## 입력·전송 UX

| 규칙 | 구현 |
|------|------|
| Enter 전송 | `Shift+Enter`는 줄바꿈, IME 조합 중(`isComposing`) 전송 안 함 |
| 전송 성공 시 | 폼 `reset()` — 입력창만 비움 |
| 전송 실패 시 | 사용자 메시지 롤백, 입력값 복원, `error` 배너 표시 |
| 로딩 중 | 전송·힌트 버튼 비활성 |

---

## 빠른 추천 문구 (일일 로테이션)

`getDailyMovaChatSuggestions(3)` — `suvis/lib/mova-chat-suggestions.ts`

- **풀:** 18개 한국어 프롬프트 (`SUGGESTION_POOL`)
- **선택:** 로컬 날짜 `YYYY-MM-DD` + FNV-1a 해시로 그날 3개 결정 (같은 날 동일, 날짜 바뀌면 변경)
- **적용 위치**
  - `MovaAiChatBar` — 입력창 위 칩 (대화 시작 전만 표시)
  - `MovaLandingChatBar` — 랜딩 하단 힌트

### 추천 칩 표시 조건 (`MovaAiChatBar`)

- `messages`에 `role === "user"` 메시지가 **없을 때만** 칩 행을 렌더한다.
- 사용자가 첫 메시지를 보내거나, `?q=` 자동 전송·칩 클릭으로 대화가 시작되면 칩은 숨긴다.

문구 추가·수정은 `SUGGESTION_POOL` 배열만 편집한다.

---

## API 요청 형식 (프론트 → 백엔드)

```json
{
  "message": "사용자 입력",
  "history": [{ "role": "user"|"assistant", "content": "..." }],
  "model": "flash15",
  "user_id": "<suvis 세션 id 또는 생략>"
}
```

- `history`: 직전 대화 최대 10턴 (`user`·`assistant`만)
- 응답의 `refined_query`는 사용자 말풍선 하단 `intentLabel`로 표시
- `recommendations`는 `MovaRecommendationCards`로 최대 3편 렌더

---

## 2026-06-25 변경 이력

| 변경 | 파일 |
|------|------|
| 전송 성공 시에만 입력 초기화 | `mova-ai-chat-bar.tsx` |
| `sessionStorage` 대화 복원 | `mova-ai-chat-bar.tsx` |
| `?q=` 중복 자동 전송 방지 | `mova-ai-chat-bar.tsx` |
| 추천 칩 — 대화 시작 후 숨김 | `mova-ai-chat-bar.tsx` |
| 추천 칩·랜딩 힌트 일일 로테이션 | `mova-chat-suggestions.ts`, 양 채팅 바 |
