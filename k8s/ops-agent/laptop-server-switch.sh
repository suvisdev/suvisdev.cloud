#!/usr/bin/env bash
# 노트북 서버의 시스템 서비스를 끄고 켠다. ops-agent 가 sudo 로 부른다(2026-11-06).
#   /usr/local/sbin/laptop-server-switch off|on
# 루트 소유로 설치해 에이전트 사용자가 고칠 수 없게 하고, sudo 규칙은 이 두 인자만 허용한다(install-server-switch.sh).
# disable 까지 하므로 노트북을 재부팅해도 꺼진 채 남는다. Tailscale 은 끄지 않는다(원격 SSH 길).
set -uo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

case "${1:-}" in
  off)
    rc=0
    systemctl disable --now k3s ollama || rc=1
    # k3s 는 서비스를 멈춰도 파드가 그대로 돈다(공식 동작) — 파드까지 없애는 건 이 스크립트뿐이다
    /usr/local/bin/k3s-killall.sh >/dev/null 2>&1 || rc=1
    # 재시작 정책이 unless-stopped 인 컨테이너도 도커가 꺼지면 같이 멈춘다
    systemctl disable --now docker.socket docker containerd || rc=1
    # 파일 캐시까지 비워 WSL 이 쥐고 있던 메모리를 윈도에 돌려준다
    sync
    echo 3 > /proc/sys/vm/drop_caches || rc=1
    exit "$rc"
    ;;
  on)
    systemctl enable --now containerd docker.socket docker ollama k3s
    ;;
  *)
    echo "사용법: $0 off|on" >&2
    exit 2
    ;;
esac
