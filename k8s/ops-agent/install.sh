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
cp "$HERE/server_on.py" "$HOME/.local/lib/ops-agent/server_on.py"
cp "$HERE/ops-agent.service" "$UNIT"
systemctl --user daemon-reload
systemctl --user enable ops-agent
systemctl --user restart ops-agent   # enable --now 는 이미 돌던 서비스를 다시 띄우지 않는다(10-28 실측 — 새 코드가 안 실렸다)
sleep 2
systemctl --user --no-pager status ops-agent | sed -n 1,5p
echo "토큰 위치: $CONF/env (백엔드 OPS_AGENT_TOKEN 에 같은 값)"
# 전체 끄기 뒤에는 어드민을 쓸 수 없어 바탕화면 바로가기로 켠다
if command -v powershell.exe >/dev/null; then
  DESKTOP="$(wslpath -u "$(powershell.exe -NoProfile -Command "[Environment]::GetFolderPath('Desktop')" | tr -d '\r')")"
  printf '@echo off\r\nchcp 65001 >nul\r\nwsl.exe -d %s --cd ~ -e python3 .local/lib/ops-agent/server_on.py\r\npause\r\n' \
    "${WSL_DISTRO_NAME:-Ubuntu}" > "$DESKTOP/서버 켜기.cmd"
  echo "바로가기: $DESKTOP/서버 켜기.cmd"
fi
[ -x /usr/local/sbin/laptop-server-switch ] || echo "서버 켜기·끄기를 쓰려면 한 번 실행: sudo bash $HERE/install-server-switch.sh"
