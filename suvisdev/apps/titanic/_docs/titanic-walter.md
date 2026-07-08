# Walter Nichols (Crew Roaster) — 승객 명단 조회

Walter는 DB에서 train/test 데이터셋을 `pd.DataFrame`으로 조회하는 역할이다.

---

## 1. 아키텍처 결정 사항

| 항목 | 결정 | 이유 |
|------|------|------|
| 메서드 형태 | `def` (동기) | Pandas + 동기 SQLAlchemy 엔진 사용 — `async def` 쓰면 이벤트 루프 블로킹 |
| 반환 타입 | `pd.DataFrame` | DTO 없이 DataFrame 직접 반환 (분석용) |
| DB 엔진 | `create_engine(sync_url)` | `pd.read_sql`은 sync 엔진만 지원 |

포트 시그니처:

```python
class WalterRoasterUseCase(ABC):
    def get_train_set(self) -> pd.DataFrame: ...  # survived IS NOT NULL
    def get_test_set(self) -> pd.DataFrame: ...   # survived IS NULL
```

---

## 2. 트러블슈팅 내역

| 문제 | 원인 | 해결 |
|------|------|------|
| DB 인증 실패 | `str(engine.url)` 이 패스워드를 `***` 마스킹 | `url.render_as_string(hide_password=False)` 사용 |
| 엔진 None 오류 | `from module import engine` 시 `init_engine()` 전 `None` 스냅숏 | `import module as _m` 후 런타임에 `_m.engine` 참조 |
| Provider/Router 오류 | 경로 및 팩토리 메서드 네이밍 오타 | 전수 교정 |

---

## 3. 검증 결과 (PASS)

| 엔드포인트 | 결과 | 비고 |
|-----------|------|------|
| `GET /api/titanic/walter/train` | 200 OK — 891건 | survived IS NOT NULL |
| `GET /api/titanic/walter/test` | 200 OK — 0건 | survived IS NULL 행 없음 (업로드 전) |

---

## 관련 문서

- [[titanic-features]]
- [[titanic-machine-learning]]
- [[titanic-erd]]
