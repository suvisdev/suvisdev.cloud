# RBAC + 멀티에이전트 관리 대시보드 구현 지시서

> **대상**: Claude Code
> **방식**: 헤르메스 엔지니어링 (Harness 단계 분할 + 단계별 검증 산출물)
> **선행 문서**: SUVIS 프로젝트 통합 정리(마스터 노트) PART 3

---

## 0. 이 문서를 읽는 Claude Code에게

아래 Harness 단계(H0~H4)를 **순서대로** 진행하고, 각 단계 끝의 **검증 게이트(✅ Gate)** 를 통과하기 전에는 다음 단계로 넘어가지 않는다.

**절대 금지**: role을 클라이언트가 결정하게 두는 것, admin API에 가드 누락, JWT payload에 민감정보 삽입.

---

## 1. 설계 요약

```
OAuth 로그인(이미 구현) → email 확보
      ↓
RBAC: email ∈ ADMIN_EMAILS(env) ? admin : user
      ↓
백엔드: admin API는 require_admin 가드로 보호 (최종 방어선)
프론트: admin → 에이전트 관리 대시보드 / user → 포트폴리오 (UX 분기)
```

## 2. 보안 원칙 (반드시 준수)

1. role은 **서버가 로그인 시 산출**, 클라이언트가 못 바꾼다.
2. **모든 admin API는 require_admin 가드** 뒤에 둔다(누락 금지).
3. 요청 바디/헤더의 role 값은 **신뢰하지 않는다** — 검증된 세션 JWT의 role claim만 신뢰.
4. 미인증은 401, 인증됐지만 권한 없으면 403.
5. JWT payload는 누구나 base64 디코드로 열람 가능 — 민감정보(비밀번호 등) 금지, role/이메일 정도만.

## 3. 핵심 결정

| 항목 | 결정 |
|------|------|
| 관리자 지정 | env 하드코딩 `ADMIN_EMAILS`(콤마 구분), 지금은 `ssuvisdev@gmail.com` 하나 |
| 화면 분리 | admin=관리 대시보드 / user=포트폴리오 메인 |
| 관리 기능 | 목록·상태, 상세, 토글, 테스트 호출, 로그, 모델 정보 |
| 에이전트 실연동 | mock부터 시작 → 각 에이전트(Argus/Loom/Atlas/Prisma/Sentinel/Echo/Chronos + 완성된 이미지 분류기) 완성 시 점진 연결 |

---

## 4. Harness 단계

### H0. Role 산출 + JWT에 반영

**작업**:
1. `ADMIN_EMAILS` 환경변수 추가(`.env`, `.env.example`), 콤마 구분 파싱
2. OAuth 콜백 처리 흐름(`OAuthLoginInteractor`)에서 identity.email로 role 산출
3. `SessionStorePort.issue_session()`에 email 파라미터 추가, JWT claims에 `role` 포함
4. `OAuthExchangeResponse`(및 consent 응답)에 `role` 필드 노출 — 프론트가 매번 JWT 디코드 안 해도 되게

**✅ Gate H0**: 실제 OAuth 로그인으로 admin 이메일 계정 → 응답에 `role: "admin"` 확인, 그 외 이메일 → `role: "user"` 확인

### H1. require_admin 가드

**작업**:
1. `viewer/dependencies`에 `require_admin` FastAPI Depends 함수 — Authorization 헤더의 세션 JWT 검증 + role 체크
2. 미인증 401, role≠admin이면 403

**✅ Gate H1**: 가드 뒤에 임시 테스트 라우트 하나 만들어 — 토큰 없음(401), user 토큰(403), admin 토큰(200) 3가지 실측

### H2. 관리 대시보드 API (mock)

**작업**: `require_admin` 가드로 보호되는 아래 엔드포인트, 지금은 mock 데이터로 8개 에이전트(이미지 분류기 포함) 반환

| 기능 | 엔드포인트 |
|------|-----------|
| 목록·상태 | GET /admin/agents |
| 상세 | GET /admin/agents/{id} |
| 토글(on/off) | POST /admin/agents/{id}/toggle |
| 테스트 호출 | POST /admin/agents/{id}/invoke |
| 로그 조회 | GET /admin/agents/{id}/logs |
| 모델 정보 | GET /admin/agents/{id}/model |

**✅ Gate H2**: 전 엔드포인트 admin 토큰으로 curl 실측 200, 비admin 토큰으로 403 확인

### H3. 프론트 화면 분기

**작업**: 로그인 후 role에 따라 `/admin`(관리 대시보드) vs 기존 포트폴리오 메인으로 라우팅. 대시보드는 H2 API를 mock 그대로 붙여 목록/토글/로그 UI 스켈레톤.

**✅ Gate H3**: admin 계정 로그인 → 대시보드 진입, 그 외 계정 → 기존 화면 그대로 확인

### H4. 최종 통합 테스트

admin 이메일로 실제 OAuth 로그인 → 대시보드에서 mock 에이전트 8개 확인 → 토글/로그 조회 1회 성공 → non-admin 계정으로 접근 시 차단 확인.

---

## 5. 다음 단계(이후 별도 진행)

각 비전 에이전트(Echo→Sentinel→Argus/Loom/Atlas→Prisma/Chronos) 완성 시, 해당 mock 항목을 실제 interactor 호출로 교체.
