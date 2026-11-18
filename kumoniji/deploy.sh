#!/usr/bin/env bash
# 쿠모니지 배포(노트북 k3s). 웹 빌드 → 이미지 빌드 → k3s import → apply → 재시작.
# 사용: ./kumoniji/deploy.sh   (저장소 루트 어디서 실행해도 됨)
set -euo pipefail
cd "$(dirname "$0")"
source ~/.cache/gildle-build/env.sh
(cd app && flutter pub get >/dev/null && flutter build web --release)
docker build -t kumoniji:latest .
# k3s는 도커와 이미지 저장소를 공유하지 않는다(containerd) — 빌드 후 import 필수
docker save kumoniji:latest | sudo k3s ctr images import -
kubectl apply -f ../k8s/kumoniji.yaml
kubectl -n suvisdev rollout restart deploy/kumoniji
kubectl -n suvisdev rollout status deploy/kumoniji --timeout=120s
