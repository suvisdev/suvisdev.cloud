#!/usr/bin/env bash
# suvisdev k8s 배포 — 구 `docker compose --env-file suvisdev/.env up -d`의 대체.
#
# 사용법:
#   ./k8s/deploy.sh            # Secret 갱신 + 매니페스트 apply
#   ./k8s/deploy.sh --build    # 이미지 재빌드 후 배포(backend/auth 재시작 포함)
#
# 전제: k3s 설치돼 있을 것(README.md 설치 절 참고).
set -euo pipefail
cd "$(dirname "$0")"
NS=suvisdev

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

if [ "${1:-}" = "--build" ]; then
  docker build -t suvisdev-app:latest ../suvisdev
  # k3s는 도커와 이미지 저장소를 공유하지 않는다(containerd) — 빌드 후 import 필수
  docker save suvisdev-app:latest | sudo k3s ctr images import -
fi

# ingress.yaml은 제외 — ingress-nginx 컨트롤러 설치 후 수동 apply (파일 상단 주석 참고)
kubectl apply \
  -f db.yaml \
  -f redis.yaml \
  -f backend.yaml \
  -f auth.yaml \
  -f pgadmin.yaml \
  -f neo4j.yaml \
  -f cloudflared.yaml

if [ "${1:-}" = "--build" ]; then
  # 같은 태그(latest) 재빌드는 spec이 안 바뀌어 rollout이 자동으로 안 일어난다
  kubectl -n "$NS" rollout restart deploy/backend deploy/auth
fi

kubectl -n "$NS" get pods
