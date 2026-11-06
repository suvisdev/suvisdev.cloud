#!/usr/bin/env bash
# 서버 켜기·끄기에 필요한 루트 스크립트와 sudo 규칙을 설치한다. 기기마다 처음 한 번 직접 실행:
#   sudo bash k8s/ops-agent/install-server-switch.sh        # 노트북
#   sudo bash install-server-switch.sh home                 # 집컴(같은 폴더에 home-server-switch.sh)
set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "sudo 로 실행하세요" >&2; exit 1; }
AGENT_USER="${SUDO_USER:-}"
[ -n "$AGENT_USER" ] && [ "$AGENT_USER" != root ] || { echo "일반 사용자에서 sudo 로 실행하세요" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
MACHINE="${1:-laptop}"
case "$MACHINE" in laptop|home) ;; *) echo "사용법: $0 [laptop|home]" >&2; exit 2 ;; esac
TARGET="/usr/local/sbin/$MACHINE-server-switch"
RULE="/etc/sudoers.d/$MACHINE-server-switch"

install -o root -g root -m 755 "$HERE/$MACHINE-server-switch.sh" "$TARGET"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
printf '%s ALL=(root) NOPASSWD: %s on, %s off\n' "$AGENT_USER" "$TARGET" "$TARGET" > "$TMP"
visudo -cf "$TMP" >/dev/null       # 문법이 틀린 규칙이 들어가면 sudo 전체가 막힌다 — 넣기 전에 검사
install -o root -g root -m 440 "$TMP" "$RULE"

echo "설치 완료: $TARGET · $RULE (사용자 $AGENT_USER, 허용 인자 on·off)"
