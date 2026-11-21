#!/usr/bin/env bash
# 쿠모니지 배포(노트북 k3s). 웹 빌드 → 이미지 빌드 → k3s import → apply → 재시작.
# 사용: ./kumoniji/deploy.sh   (저장소 루트 어디서 실행해도 됨)
set -euo pipefail
cd "$(dirname "$0")"
source ~/.cache/gildle-build/env.sh
(cd app && flutter pub get >/dev/null && flutter build web --release --no-web-resources-cdn)  # CanvasKit 자체 호스팅(CSP에 외부 스크립트 없음)
docker build -t kumoniji:latest .
# k3s는 도커와 이미지 저장소를 공유하지 않는다(containerd) — 빌드 후 import 필수
docker save kumoniji:latest | sudo k3s ctr images import -
# kumoniji/.env → Secret kumoniji-env(파드는 envFrom으로 받는다). .env가 없으면 여기서 멈춘다.
# 시험용 키(KUMONIJI_TEST_*)는 운영에 넣지 않는다. 값은 화면에 찍지 않는다.
[ -f .env ] || { echo "kumoniji/.env가 없음 — .env.example을 보고 만든다" >&2; exit 1; }
kubectl -n suvisdev create secret generic kumoniji-env \
  --from-env-file=<(grep -v '^KUMONIJI_TEST_' .env) \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl apply -f k8s.yaml
kubectl -n suvisdev rollout restart deploy/kumoniji
kubectl -n suvisdev rollout status deploy/kumoniji --timeout=120s
