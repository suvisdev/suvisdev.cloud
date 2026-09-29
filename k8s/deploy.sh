#!/usr/bin/env bash
# suvisdev k8s 배포 — 구 `docker compose --env-file suvisdev/.env up -d`의 대체.
#
# 사용법:
#   ./k8s/deploy.sh                 # Secret 갱신 + 매니페스트 apply (데스크톱: db·redis 클러스터 안)
#   ./k8s/deploy.sh --build         # 이미지 재빌드 후 배포(backend/auth 재시작 포함)
#   ./k8s/deploy.sh --external-db   # 노트북 1단계: db·redis는 기존 도커 컨테이너를 그대로 쓰고
#                                   #   (external-db-redis.yaml) nginx-alias.yaml·ingress.yaml까지 apply
#   플래그는 조합 가능: ./k8s/deploy.sh --external-db --build
#
# 전제: k3s 설치돼 있을 것(README.md 설치 절 참고).
set -euo pipefail
cd "$(dirname "$0")"
NS=suvisdev
REPO_ROOT="$(cd .. && pwd)"   # backend.yaml hostPath의 __REPO_ROOT__ 치환용
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}"   # __HF_CACHE__ — 감성 배치 가중치 캐시(09-27)

BUILD=0
EXTERNAL_DB=0
for arg in "$@"; do
  case "$arg" in
    --build) BUILD=1 ;;
    --external-db) EXTERNAL_DB=1 ;;
    *) echo "알 수 없는 옵션: $arg" >&2; exit 1 ;;
  esac
done

# k3s kubeconfig — 셸에 KUBECONFIG를 안 잡아놨어도 동작하게
if [ -z "${KUBECONFIG:-}" ] && [ -r /etc/rancher/k3s/k3s.yaml ]; then
  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
fi

kubectl apply -f namespace.yaml

# suvisdev/.env → Secret. compose의 --env-file 주입을 대체한다.
# (구 사고 재발 방지: compose는 --env-file을 빠뜨리면 빈 자격증명으로 조용히
#  떴지만, 이 스크립트는 .env가 없으면 여기서 바로 실패한다.)
kubectl -n "$NS" create secret generic suvisdev-env \
  --from-env-file=../suvisdev/.env \
  --dry-run=client -o yaml | kubectl apply -f -

# .env.auth는 있을 때만(auth 매니페스트에서 optional 참조)
if [ -f ../suvisdev/.env.auth ]; then
  kubectl -n "$NS" create secret generic suvisdev-env-auth \
    --from-env-file=../suvisdev/.env.auth \
    --dry-run=client -o yaml | kubectl apply -f -
fi

if [ "$BUILD" = 1 ]; then
  docker build -t suvisdev-app:latest ../suvisdev
  # k3s는 도커와 이미지 저장소를 공유하지 않는다(containerd) — 빌드 후 import 필수
  docker save suvisdev-app:latest | sudo k3s ctr images import -

  # 태그를 잃은 이미지 정리 — 안전망이다. 이 환경의 buildkit은 같은 태그 재빌드 시
  # 이전 이미지를 자동 정리해 실측상 dangling이 0개였지만(2026-09-22, 두 번 빌드
  # 모두 0B 회수), 빌더가 바뀌거나 중단된 빌드가 남기면 14GB대가 <none>으로 잡힌다.
  # dangling만 지우므로 실행 중 컨테이너의 이미지와 다른 태그는 건드리지 않는다.
  echo "[prune] 태그 없는 도커 이미지 정리"
  docker image prune -f
  # containerd(`crictl rmi --prune`)는 여기서 쓰면 안 된다 — 방금 import한 이미지를
  # "아직 아무 파드도 참조하지 않는 미사용 이미지"로 보고 지워버려서, 뒤따르는
  # rollout이 ErrImageNeverPull로 죽는다(2026-09-22 실측: 새 파드 2개가 116분간
  # Pending). import → prune → rollout 순서에서는 필연적이다. containerd 정리는
  # 이 파일 맨 아래에서 rollout 완료 **후** 태그 잃은 이미지만 지운다.
  # 실제로 쌓이는 건 dangling 이미지가 아니라 빌드 캐시다(2026-09-22 실측: 두 번
  # 빌드에 0.8GB→15.3GB, dangling은 0개 — buildkit이 같은 태그 재빌드 시 이전
  # 이미지를 자동 정리한다). 캐시는 다음 빌드를 5~6분 줄여주는 자산이고 디스크도
  # 818GB 남아 있어 매번 지우지 않는다. 무한 증가만 상한으로 막는다.
  docker builder prune -f --max-used-space 20GB >/dev/null 2>&1 || true
fi

# db·redis: 데스크톱은 클러스터 안(StatefulSet/PVC), 노트북 1단계는 도커 컨테이너를
# 셀렉터 없는 Service로 연결. 둘을 같이 apply하면 셀렉터 있는 쪽이 이겨 빈 DB에 붙으니
# 반드시 한쪽만.
if [ "$EXTERNAL_DB" = 1 ]; then
  # nginx-alias.yaml: 터널 라우트 `api → http://nginx:80`을 대시보드 변경 없이 Traefik으로
  kubectl apply -f external-db-redis.yaml -f nginx-alias.yaml
else
  kubectl apply -f db.yaml -f redis.yaml
fi

# backend.yaml의 hostPath(__REPO_ROOT__)를 이 머신의 저장소 루트로 치환해 apply
sed "s#__REPO_ROOT__#${REPO_ROOT}#g; s#__HF_CACHE__#${HF_CACHE}#g" backend.yaml | kubectl apply -f -

kubectl apply \
  -f auth.yaml \
  -f pgadmin.yaml \
  -f cloudflared.yaml

# ingress.yaml(Traefik, k3s 내장)은 프로덕션 라우팅용 — 로컬 개발은 ServiceLB 포트로
# 충분해 --external-db(노트북)일 때만 apply한다.
if [ "$EXTERNAL_DB" = 1 ]; then
  kubectl apply -f ingress.yaml
  # cloudflared.yaml은 데스크톱 보호용 replicas:0이라, 위 apply가 노트북 터널
  # 커넥터를 0으로 덮어 api./auth.suvisdev.cloud가 530이 된다(2026-09-09 사고).
  # 프로덕션(--external-db)에서만 1로 복원한다(README 수동 scale 단계 자동화).
  kubectl -n "$NS" scale deploy/cloudflared --replicas=1
fi

if [ "$BUILD" = 1 ]; then
  # 같은 태그(latest) 재빌드는 spec이 안 바뀌어 rollout이 자동으로 안 일어난다
  kubectl -n "$NS" rollout restart deploy/backend deploy/auth
  # containerd 구 이미지 정리(2026-09-22 사용자 요청: 배포마다 4.8GB씩 쌓이지 않게).
  # 같은 태그로 import하면 이전 이미지는 태그를 잃고 <none>으로 남는다. 새 파드가
  # 다 뜬 뒤에만 지운다 — 그 전에 지우면 롤백 대상이 사라지고, --prune은 파드가
  # 0인 다른 이미지(pgadmin·cloudflared)까지 지워 재풀을 유발하므로 안 쓴다.
  # 실행 중 컨테이너가 참조하는 이미지는 crictl이 거부하므로 롤아웃 실패 시에도 안전.
  kubectl -n "$NS" rollout status deploy/backend --timeout=600s
  kubectl -n "$NS" rollout status deploy/auth --timeout=600s
  echo "[prune] containerd 태그 없는 이미지 정리"
  sudo k3s crictl images 2>/dev/null | awk '$1 == "<none>" { print $3 }' \
    | xargs -r sudo k3s crictl rmi || true
fi

kubectl -n "$NS" get pods
