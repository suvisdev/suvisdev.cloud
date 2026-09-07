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
sed "s#__REPO_ROOT__#${REPO_ROOT}#g" backend.yaml | kubectl apply -f -

kubectl apply \
  -f auth.yaml \
  -f pgadmin.yaml \
  -f neo4j.yaml \
  -f cloudflared.yaml

# ingress.yaml(Traefik, k3s 내장)은 프로덕션 라우팅용 — 로컬 개발은 ServiceLB 포트로
# 충분해 --external-db(노트북)일 때만 apply한다.
if [ "$EXTERNAL_DB" = 1 ]; then
  kubectl apply -f ingress.yaml
fi

if [ "$BUILD" = 1 ]; then
  # 같은 태그(latest) 재빌드는 spec이 안 바뀌어 rollout이 자동으로 안 일어난다
  kubectl -n "$NS" rollout restart deploy/backend deploy/auth
fi

kubectl -n "$NS" get pods
