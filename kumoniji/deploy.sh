#!/usr/bin/env bash
# 쿠모니지 배포(노트북 k3s). 웹 빌드 → 이미지 빌드 → k3s import → apply → 재시작.
# 사용: ./kumoniji/deploy.sh   (저장소 루트 어디서 실행해도 됨)
set -euo pipefail
# 손 배포와 CD 배포가 같은 kumoniji:latest를 덮어쓰지 않게 한 번에 하나만(노트북 한 대라 파일 잠금이면 된다).
mkdir -p "$HOME/.cache" && exec 9>"$HOME/.cache/kumoniji-deploy.lock"
flock 9
cd "$(dirname "$0")"
# 판 = 개발 문서(CLAUDE.md·_docs/)를 뺀 kumoniji/ 파일들의 해시. 문서만 바뀐 머지로 파드를 재시작하지 않게.
# app/assets/legal/*.md(약관)는 앱에 들어가므로 판에 넣는다.
SRC=(. ':(exclude)CLAUDE.md' ':(exclude)_docs/')
TREE=$(git ls-files -s -- "${SRC[@]}" | sha1sum | cut -c1-40)
[ -z "$(git status --porcelain -- "${SRC[@]}")" ] || TREE=dirty
# CD(KUMONIJI_CD=1)는 CI가 통과한 체크아웃에서 돌므로 .env는 SUVISDEV_DATA_ROOT(운영 저장소) 쪽을 읽는다. 손 배포는 이 폴더 .env.
ENV_FILE=.env
[ -z "${KUMONIJI_CD:-}" ] || ENV_FILE="${SUVISDEV_DATA_ROOT:?CD는 러너 .env에 SUVISDEV_DATA_ROOT가 있어야 함}/kumoniji/.env"
[ -f "$ENV_FILE" ] || { echo "$ENV_FILE 이 없음 — .env.example을 보고 만든다" >&2; exit 1; }
# .env → Secret kumoniji-env(파드는 envFrom으로 받는다)를 여기서 한 번만 만든다. 아래 DB 검사도 이 Secret에서 읽어
# 배포 도중 .env가 바뀌거나 파싱이 달라 어긋나는 일이 없게. 시험용 키(KUMONIJI_TEST_*)는 운영에 넣지 않는다. 값은 찍지 않는다.
SECRET_JSON=$(kubectl -n suvisdev create secret generic kumoniji-env \
  --from-env-file=<(grep -v '^KUMONIJI_TEST_' "$ENV_FILE") --dry-run=client -o json)
# CD(KUMONIJI_CD=1)는 잠금 안에서 판단한다 — 기다리는 사이 더 새 판이 나갔으면 옛 판으로 되돌리지 않게.
#  · 지금 main의 kumoniji/와 다르면 더 새 변경이 있고, 그 CI가 배포한다.
#  · 지금 도는 판(아래에서 deploy 주석에 적는 값)과 같으면 재시작하지 않는다 — 메모리의 대국이 사라진다.
if [ -n "${KUMONIJI_CD:-}" ]; then
  git fetch -q --no-tags --depth=1 origin main
  if ! git diff --quiet HEAD FETCH_HEAD -- "${SRC[@]}"; then echo "::warning::배포 건너뜀 — main에 더 새 쿠모니지 변경이 있음(그 CI가 배포한다. 그 CI가 실패하면 운영은 옛 판 그대로)"; exit 0; fi
  running=$(kubectl -n suvisdev get deploy kumoniji -o jsonpath='{.metadata.annotations.kumoniji/tree}' 2>/dev/null || true)
  if [ "$running" = "$TREE" ]; then echo "::warning::배포 건너뜀 — 이미 도는 판과 같음"; exit 0; fi
  # 서버는 시작할 때 마이그레이션을 자동 적용한다. DB에 아직 없는 마이그레이션이 든 판은 자동으로 내보내지 않는다 —
  # 사용자가 덤프를 뜬 뒤 손으로 ./kumoniji/deploy.sh(ADR-0029). 실패로 끝내 Actions에서 눈에 띄게 한다.
  # 서버가 실제로 붙을 DB(위 Secret의 KUMONIJI_DATABASE_URL)에서 읽는다. 주소(비밀번호 포함)는 명령행에 안 올리고
  # 표준 입력으로만 넘긴다. psycopg가 든 지금 서버 이미지를 쓴다(이미지가 없으면 실패 — 처음 설치는 손 배포).
  applied=$(python3 -c 'import base64,json,sys; sys.stdout.write(base64.b64decode(json.load(sys.stdin)["data"]["KUMONIJI_DATABASE_URL"]).decode())' <<<"$SECRET_JSON" |
    docker run --rm -i --add-host host.docker.internal:host-gateway --entrypoint python kumoniji:latest \
      -c 'import sys,psycopg; c=psycopg.connect(sys.stdin.read()); print("\n".join(str(r[0]) for r in c.execute("SELECT n FROM schema_version")))')
  for f in server/kumoniji/accounts/migrations/*.sql; do
    n=$((10#$(basename "$f" | cut -d_ -f1)))
    grep -qx "$n" <<<"$applied" || { echo "::error::새 마이그레이션 $(basename "$f") — DB 덤프 뒤 노트북에서 ./kumoniji/deploy.sh로 배포한다"; exit 1; }
  done
fi
# 여기부터 운영을 바꾼다 — 도중에 실패하면 '도는 판'을 모르게 두어 다음 CD가 반드시 다시 배포하게.
! kubectl -n suvisdev get deploy/kumoniji >/dev/null 2>&1 || kubectl -n suvisdev annotate deploy/kumoniji kumoniji/tree- >/dev/null  # 처음 설치면 deploy가 없다
source ~/.cache/gildle-build/env.sh
(cd app && flutter pub get >/dev/null && flutter build web --release --no-web-resources-cdn)  # CanvasKit 자체 호스팅(CSP에 외부 스크립트 없음)
docker build -t kumoniji:latest .
# k3s는 도커와 이미지 저장소를 공유하지 않는다(containerd) — 빌드 후 import 필수
docker save kumoniji:latest | sudo k3s ctr images import -
kubectl apply -f - <<<"$SECRET_JSON" >/dev/null
kubectl apply -f k8s.yaml
kubectl -n suvisdev rollout restart deploy/kumoniji
kubectl -n suvisdev rollout status deploy/kumoniji --timeout=120s
# 지금 도는 판을 deploy 주석에 적는다(위 CD 판단이 본다). 커밋 안 된 수정이 있으면 dirty.
kubectl -n suvisdev annotate --overwrite deploy/kumoniji kumoniji/tree="$TREE" >/dev/null
