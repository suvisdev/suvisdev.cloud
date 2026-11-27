-- 지갑 스냅숏 순서 번호(v). 지갑 행을 잠근 채 nextval — 같은 계정이면 처리(커밋) 순서대로 커지고,
-- 서버 시계가 되감기거나 재시작해도 거꾸로 가지 않는다(11-26 앱 리뷰 22·25·29·30차).
CREATE SEQUENCE wallet_version;

-- 회전한 요청이 보낸 재시도 키의 해시. 응답을 못 받은 클라이언트가 같은 키로 다시 오면 같은 새 토큰을 다시 준다
-- (멱등 갱신). 키는 클라이언트 메모리에만 있어, 저장된 쿠키·토큰을 훔친 사람은 다시 받지 못한다(앱 리뷰 49·50차).
ALTER TABLE spent_refresh ADD COLUMN retry bytea;
-- 회전한 요청의 IP — 방금 회전된 토큰을 다시 받는 게 같은 브라우저 탭들의 동시 갱신인지(같은 IP) 보는 데 쓴다(앱 리뷰 52차)
ALTER TABLE spent_refresh ADD COLUMN ip text;
-- 이 토큰을 이미 다시 받기로(replayed)·동시 갱신으로(raced) 센 적 있나 — 탭 여럿이 같은 토큰으로 와도 한 번만 센다(앱 리뷰
-- 56·57차). 둘을 따로 둔다 — 같이 쓰면 탭들의 동시 갱신이 먼저 표시해 다른 IP의 다시 받기가 안 세어진다(58차)
ALTER TABLE spent_refresh ADD COLUMN replayed boolean NOT NULL DEFAULT false,
    ADD COLUMN raced boolean NOT NULL DEFAULT false;

-- 다시 받기(멱등 갱신) 횟수. 웹은 재시도 키가 리프레시와 같은 쿠키 통에 있어, 둘을 함께 훔치면 다시 받기로 탐지 없이
-- 토큰을 이어 받을 수 있다. 정상 다시 받기는 응답을 잃었을 때뿐이라 드물다 — 하루에 MAX_REPLAYS를 넘으면 탈취로 본다(앱 리뷰 40차).
ALTER TABLE sessions ADD COLUMN replays int NOT NULL DEFAULT 0, ADD COLUMN races int NOT NULL DEFAULT 0,
    ADD COLUMN replayed_at timestamptz;

-- 웹 재시도 키(로그인·갱신 응답이 심는 쿠키)가 생기기 전의 세션은 한 번 모두 끊는다 — 다시 로그인하면 키를 받는다.
-- 옛 세션에 키를 나중에 심어 주는 길은 그 첫 물음이 훔친 사람의 것일 수 있고, 두 탭이 겹치면 키 없는 회전과 엇갈렸다
-- (앱 리뷰 35·49·50차). 이 판을 배포할 때 사용자는 한 명뿐이라 다시 로그인 한 번으로 정리한다.
UPDATE sessions SET revoked_at = now() WHERE revoked_at IS NULL;
