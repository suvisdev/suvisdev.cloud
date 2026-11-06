#!/usr/bin/env bash
# 집컴의 시스템 서비스를 끄고 켠다. 노트북 ops-agent 가 전체 끄기·켜기 때 ssh + sudo 로 부른다.
#   /usr/local/sbin/home-server-switch off|on
# 루트 소유로 설치하고 sudo 규칙은 이 두 인자만 허용한다(install-server-switch.sh home).
# disable 까지 하므로 재부팅해도 꺼진 채 남는다. SSH·Tailscale 은 끄지 않는다 — 노트북이 다시 켜는 길이다.
set -uo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
DATA_CONTAINERS=(suvisdev-db-1 suvisdev-redis-1)

case "${1:-}" in
  off)
    rc=0
    systemctl disable --now k3s ollama || rc=1
    /usr/local/bin/k3s-killall.sh >/dev/null 2>&1 || rc=1
    # 도커 종료의 기본 15초에 맡기지 않고 DB 가 정상 종료할 시간을 준다. 다시 실행할 때는 도커가 이미 꺼져 있다
    if systemctl is-active -q docker; then
      docker stop -t 60 "${DATA_CONTAINERS[@]}" || rc=1
    fi
    systemctl disable --now docker.socket docker containerd || rc=1
    exit "$rc"
    ;;
  on)
    systemctl enable --now containerd docker.socket docker ollama k3s || exit 1
    # docker stop 한 컨테이너는 unless-stopped 여도 저절로 뜨지 않는다
    docker start "${DATA_CONTAINERS[@]}"
    ;;
  *)
    echo "사용법: $0 off|on" >&2
    exit 2
    ;;
esac
