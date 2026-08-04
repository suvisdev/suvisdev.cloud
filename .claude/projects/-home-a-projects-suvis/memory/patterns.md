# 코드 패턴 메모

새 코드를 쓸 때 따라야 할 기존 형태. 세부 규칙이 이미 문서화된 영역은 **여기서
반복하지 않고 위치만** 가리킨다(사본이 갈라지는 것을 막기 위해).

---

## 규칙 문서 위치 (먼저 여기를 볼 것)

| 영역 | 문서 |
|------|------|
| TypeScript 언어 규칙 (any 금지, type 별칭, enum 금지 등) | `.claude/rules/typescript.md` |
| API 클라이언트 · 라우트 핸들러 | `.claude/rules/api-standards.md` |
| 프론트 구조 · 서버/클라이언트 컴포넌트 · null · try/catch | `suvis/CLAUDE.md` |
| React 세부 (§8 null, §9 분기, §10 try/catch) | `suvis/_docs/react-rules.md` |

---

## 백엔드 — 클린 아키텍처 계층

`suvisdev/apps/<app>/`는 인바운드에서 아웃바운드까지 계층이 고정돼 있다. 새 기능은
계층을 건너뛰지 말고 전부 거친다.

```text
adapter/inbound/api/v1/<x>_router.py     라우터 (HTTP)
adapter/inbound/api/schemas/<x>_schema.py  pydantic 스키마 (HTTP 경계)
app/ports/input/<x>_use_case.py          입력 포트 (ABC)
app/use_cases/<x>_interactor.py          유스케이스 (정책·임계값 소유)
app/dtos/<x>_dto.py                      DTO (frozen dataclass)
app/ports/output/<x>_port.py             출력 포트 (ABC)
adapter/outbound/repositories/<x>_repository.py  리포지토리 구현
adapter/outbound/orm/<x>_orm.py          SQLAlchemy ORM
```

- **DTO는 `@dataclass(frozen=True)`**. 응답에 값을 덧붙일 땐 `dataclasses.replace()`.
- **정책은 인터랙터가 소유한다.** 예: Sentinel 게이트의 블러 임계값·포스터 소프트
  플래그 판정은 `vision_interactor.py`에 있고, 어댑터는 raw 점수만 돌려준다.
- **DI는 `dependencies/<x>_provider.py`** 한 곳에서 조립한다. 저장 백엔드를 바꿀 때
  이 파일의 `get_<x>_repository()`만 교체하면 된다(S3 → DB 전환이 그렇게 됐다).

### 어드민 전용 엔드포인트

`shared/security/require_admin.py`의 가드를 `Depends`로 붙인다. 앱 간 import를 피해
`shared/` 리프 계층에 있다.

```python
from shared.security.require_admin import AdminPrincipal, require_admin

@router.patch("/{upload_id}/poster-flag", response_model=VisionPosterFlagSchema)
async def override_poster_flag(
    upload_id: int,
    body: VisionPosterFlagUpdateSchema,
    _: AdminPrincipal = Depends(require_admin),
    vision: VisionUseCase = Depends(get_vision_use_case),
) -> VisionPosterFlagSchema:
    dto = await vision.override_poster_flag(upload_id, body.is_poster_warning)
    if not dto.updated:
        raise HTTPException(status_code=404, detail=f"id={upload_id} 없음")
    return VisionPosterFlagSchema(...)
```

- 갱신 결과 DTO는 `updated: bool`을 담아 라우터가 404를 판정한다
  (mova `market_picks_router.py`가 원형).
- **프론트까지 3계층**(클라이언트 → `route.ts` 프록시 → 백엔드) 모두 세션 Bearer를
  전달해야 한다. 한 곳만 빠져도 401이다.

---

## 마이그레이션

- 새 파일은 `alembic/versions/YYYYMMDD_NNNN_<설명>.py`, `down_revision`은 **직전
  head**를 가리킨다. 브랜치가 갈리지 않게 `alembic history`로 단일 head를 확인한다.
- ORM에 컬럼을 추가하면 마이그레이션도 **같이** 추가한다. `vision_uploads`처럼
  `ensure_titanic_tables()`의 `create_all()` 경로와 alembic 양쪽에 걸친 테이블이
  있어서, ORM만 고치면 기존 DB에 컬럼이 안 생긴다.
- 기존 행이 있는 테이블에 `nullable=False` 컬럼을 넣을 땐 `server_default`를 준다.

---

## 테스트

- 실제 모델·GPU가 필요하면 `@pytest.mark.gpu`, 실제 Ollama가 필요하면
  `@pytest.mark.ollama`. 일반 실행(`-m "not gpu"`)에서 빠지도록.
- 포트를 구현한 **fake**로 유스케이스 로직만 검증한다(저장 백엔드와 분리).
  `test_vision_upload_sentinel_gate.py`의 `_FakeVisionRepository`가 예시.
- 포트(ABC)에 추상 메서드를 추가하면 **테스트의 fake도 같이 구현**해야 한다.
  안 하면 인스턴스화 시점에 `TypeError`가 난다.
