---
paths:
  - "suvisdev/apps/**/*_orm*.py"
  - "suvisdev/alembic/versions/*.py"
---

## ORM 컬럼 타입·길이 규칙

`characters.character_name`이 `String(50)`이라 TMDB 배역명이 잘리며 배치가
통째로 실패한 사고(2026-08-05)에서 나온 규칙이다. 저장소 실측 기준으로만 적는다.

### 1. 문자열 컬럼 기본값은 `Text`

**외부에서 들어오거나 사람이 자유롭게 쓰는 값은 `Text`를 쓴다.** 길이 상한은
"이 값이 이보다 길 리 없다"를 확신할 수 있을 때만 둔다.

실제 `Text`인 컬럼들이 이 기준과 일치한다 — `movies.synopsis`·`poster_url`,
`characters.character_name`, `reviews.body`, `receive.subject`·`body`,
`hub_knowledge.title`·`content`, `pdf_loader.extracted_text`·`summary`,
`chats.raw_message`, `assistants.system_prompt`.

특히 다음은 **항상 `Text`**:

- 외부 API가 주는 이름·제목·설명 (TMDB·KOFIC·KBO 등)
- LLM이 생성한 텍스트 (길이 상한이 원리적으로 없다)
- URL (`poster_url`, `profile_photo_url`, `avatar_url`)
- 본문·요약·메모 계열

### 2. 길이 제한은 형식이 고정된 식별자·코드에만

`String(N)`이 정당한 경우는 값의 형식을 우리가 정하거나 규격이 고정된 것뿐이다.
현행 예: `movies.slug` `String(64)`, `movies.age_rating` `String(8)`(`전체|12세|
15세|청불`), `movies.original_language` `String(8)`(ISO 639-1),
`tags.tag_kind` `String(16)`(`mood|genre|cast`), `tags.slug` `String(64)`,
`actors.role_type` `String(16)`.

### 3. 기존 컬럼 현황 (2026-08-07 실측)

외부 데이터를 받는데 아직 `String(N)`인 컬럼이 남아 있지만 **여유가 충분해
당장 옮길 필요는 없다** — 프로덕션 최대 길이 대비:

| 컬럼 | 상한 | 실제 최대 | 여유 |
|------|------|-----------|------|
| `movies.title` | 255 | 77 | 3.3배 |
| `actors.name` | 128 | 31 | 4.1배 |
| `tags.label` | 255 | 5 | 넉넉 |
| `picks.hook` | 120 | 40 | 3배 (코드에서 `[:120]`로 자름) |

**이 규칙은 신규 컬럼에 적용한다.** 기존 컬럼은 실제로 잘릴 조짐이 보일 때
마이그레이션한다(`20260805_0001` 패턴 — `op.alter_column(..., type_=sa.Text())`).

### 4. 새 컬럼을 추가할 때

1. 그 값의 출처가 외부 API·LLM·사용자 입력인가 → **`Text`**
2. 우리가 형식을 정하는 코드·식별자인가 → `String(N)`, N은 형식 근거를 주석에 남긴다
3. 마이그레이션·ORM·DTO·스키마를 한 커밋에 함께 바꾼다
   (`movies.synopsis`·`original_language` 추가가 이 패턴)

### 5. 길이 초과가 배치를 죽이지 않게

DB 예외는 세션을 pending-rollback으로 만들어, 롤백 없이 같은 세션을 계속 쓰면
이후 **모든** 항목이 도미노로 실패한다(실측: 1건이 418건을 죽임). 배치에서
항목 단위 `try/except`를 쓸 땐 반드시 `await session.rollback()`을 함께 넣는다.
