#!/usr/bin/env bash
# 이 PC(WSL)에 운영 제어 에이전트를 systemd 유저 서비스로 설치한다.
#   bash k8s/ops-agent/install.sh
# 토큰은 처음 한 번 만들어 ~/.config/ops-agent/env(권한 600)에 둔다. 백엔드 .env 의
# OPS_AGENT_TOKEN 에 같은 값을 넣는다(2단계). 다시 돌려도 토큰은 바꾸지 않는다.
set -euo pipefail

CONF="$HOME/.config/ops-agent"
UNIT="$HOME/.config/systemd/user/ops-agent.service"
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$CONF" "$(dirname "$UNIT")"
if [ ! -f "$CONF/env" ]; then
  umask 077
  printf 'OPS_AGENT_TOKEN=%s\n' "$(openssl rand -hex 32)" > "$CONF/env"
fi
mkdir -p "$HOME/.local/lib/ops-agent"
cp "$HERE/ops_agent.py" "$HOME/.local/lib/ops-agent/ops_agent.py"   # 저장소 사본과 떼어 둔다(다시 설치하면 갱신)
cp "$HERE/ops-agent.service" "$UNIT"
systemctl --user daemon-reload
systemctl --user enable ops-agent
systemctl --user restart ops-agent   # enable --now 는 이미 돌던 서비스를 다시 띄우지 않는다(10-28 실측 — 새 코드가 안 실렸다)
sleep 2
systemctl --user --no-pager status ops-agent | sed -n 1,5p
echo "토큰 위치: $CONF/env (백엔드 OPS_AGENT_TOKEN 에 같은 값)"
