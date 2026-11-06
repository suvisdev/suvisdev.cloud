#!/usr/bin/env bash
# 예비 서버(집컴) 동기화 — 노트북이 방금 빌드·배포한 이미지와 매니페스트를 집컴에 그대로 반영한다.
#
# 집컴은 빌드하지 않는다: 8.9GB에서 이미지 빌드(15분)와 기동이 겹치면 메모리가 모자라 DB가 죽었다(2026-10-05).
# 이미지는 집컴의 로컬 레지스트리(127.0.0.1:5000, 컨테이너 standby-registry)로 push 해 바뀐 레이어만 보낸다 —
# 5.8GB 통째 전송은 와이파이를 10분 넘게 막고, 그 와이파이로 노트북 앱이 집컴 DB를 쓴다.
# 집컴 k3s는 그 레지스트리에서 직접 받는다(/etc/rancher/k3s/registries.yaml 의 http 미러, 2026-10-06) —
# 예전처럼 docker pull → docker save → k3s ctr import 로 5.8GB를 통째 옮기던 단계(약 7분)가 없다.
#
# 사용: backend-deploy.yml 이 deploy.sh 다음에 부른다. 손으로: ./k8s/sync-standby.sh
# 환경: STANDBY_HOST(기본: 집 안이면 내부 IP, 아니면 Tailscale), STANDBY_KEY(기본 ~/.ssh/home_desktop),
#       STANDBY_ROLLOUT_TIMEOUT(기본 1200초 — 아래 ROLLOUT_TIMEOUT 설명)
set -euo pipefail
cd "$(dirname "$0")"

KEY="${STANDBY_KEY:-$HOME/.ssh/home_desktop}"
CTL="/tmp/standby-sync-$$.sock"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=10
     -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$HOME/.ssh/known_hosts_ollama_tunnel")
# 같은 집이어도 Tailscale 이 중계(DERP tok)로 붙어 2.7MB/s, 내부 IP 는 34.4MB/s(2026-11-06 실측). 11-05 는 push 만 30분이 걸렸다.
# 내부 IP 는 SSH 인증까지 통과할 때만 쓴다 — 다른 네트워크의 같은 주소는 호스트 키 확인에서 걸러진다.
HOST="${STANDBY_HOST:-}"
if [ -z "$HOST" ]; then
  # 집컴에 부하가 있으면 SSH 연결만 수 초가 걸린다(11-06 실측 2.5~27초). 못 닿으면 Tailscale 로 간다.
  if timeout 15 ssh -n -o ConnectTimeout=8 "${SSH[@]:1}" suvisdev@172.30.1.21 true 2>/dev/null; then
    HOST=suvisdev@172.30.1.21
  else
    HOST=suvisdev@100.91.129.31
  fi
fi
echo "[standby] 경로 $HOST"
IMG=suvisdev-app:latest
REG_LOCAL=127.0.0.1:15000   # 노트북 쪽 임시 터널 → 집컴 127.0.0.1:5000
REG_DESK=127.0.0.1:5000     # 집컴 k3s가 받는 주소
REL='$HOME/serve/k8s-release'
# 집컴 롤아웃 대기(초). 집컴 WSL 디스크가 HDD(D:\WSL\Ubuntu)라 캐시가 식은 상태의 새 backend 는
# 파이썬 import 만 6분이 걸린다 — 재시작부터 Ready 까지 33초~10분 48초(2026-10-20~11-05 실측, 노트북은 21초).
# 600초로는 10-30·11-05 두 번 실패 표시가 났다(11-05 는 47초 차이, 롤아웃은 그 뒤 끝남). 매니페스트의
# progressDeadlineSeconds(1200)와 같이 맞춘다 — 하나만 늘리면 다른 쪽이 먼저 실패를 낸다.
ROLLOUT_TIMEOUT="${STANDBY_ROLLOUT_TIMEOUT:-1200}"

"${SSH[@]}" -fN -M -S "$CTL" -L "$REG_LOCAL:127.0.0.1:5000" "$HOST"
trap '"${SSH[@]}" -S "$CTL" -O exit "$HOST" >/dev/null 2>&1 || true' EXIT

echo "[standby] 이미지 push (바뀐 레이어만)"
docker tag "$IMG" "$REG_LOCAL/$IMG"
docker push -q "$REG_LOCAL/$IMG"
docker rmi "$REG_LOCAL/$IMG" >/dev/null

echo "[standby] 집컴: 매니페스트 적용 + backend·auth 재시작 (k3s가 레지스트리에서 바뀐 레이어만 받음)"
"${SSH[@]}" "$HOST" "rm -rf $REL && mkdir -p $REL"
tar -cf - --exclude='./ollama-proxy/*.log' . | "${SSH[@]}" "$HOST" "tar -xf - -C $REL"
# 집컴 사본만 이미지 주소를 레지스트리로, 받기 정책을 Always 로 바꾼다(같은 latest 태그라 매번 새로 확인해야 한다).
# deploy.sh --external-db 는 cloudflared 를 1로 apply 한다 — 집컴 예비 판단기(standby-agent)가
# 노트북이 서빙 중이면 5초 안에 0으로 되돌린다. DB가 하나라 그 사이 겹쳐도 안전하다.
"${SSH[@]}" "$HOST" "set -e
  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
  cd $REL
  sed -i -e 's#image: $IMG#image: $REG_DESK/$IMG#' -e 's#imagePullPolicy: Never.*#imagePullPolicy: Always#' backend.yaml auth.yaml
  grep -q 'image: $REG_DESK/$IMG' backend.yaml && grep -q 'image: $REG_DESK/$IMG' auth.yaml
  SUVISDEV_DATA_ROOT=\$HOME/projects/suvisdev ./deploy.sh --external-db >/dev/null
  kubectl -n suvisdev rollout restart deploy/backend deploy/auth
  kubectl -n suvisdev rollout status deploy/backend --timeout=${ROLLOUT_TIMEOUT}s
  kubectl -n suvisdev rollout status deploy/auth --timeout=${ROLLOUT_TIMEOUT}s
  sudo -n k3s crictl images 2>/dev/null | awk '\$1 == \"<none>\" { print \$3 }' | xargs -r sudo -n k3s crictl rmi >/dev/null 2>&1 || true
  kubectl -n suvisdev get pods"
echo "[standby] 완료"
