#!/usr/bin/env bash
# 집컴 예비 판단기 (집컴 유저 서비스 standby-agent)
# - 노트북 심장박동(~/serve/laptop_heartbeat: "<epoch> serving|not-serving <코드>")을 5초마다 본다.
# - 15초 넘게 끊겼거나 serving 이 아니면 집컴 cloudflared 1 (집컴이 받음).
# - 노트북이 30초 연속 serving 이면 집컴 cloudflared 0 (노트북이 받음). 겹치는 동안은 둘 다 받는다 — DB가 하나라 안전.
NS=suvisdev
HB=~/serve/laptop_heartbeat
STALE=15
GIVE_BACK=30
good_since=0; last=""

while true; do
  now=$(date +%s)
  { read -r ts state _ < "$HB"; } 2>/dev/null || { ts=0; state=none; }
  age=$(( now - ${ts:-0} ))
  if [ "$state" = "serving" ] && [ "$age" -le "$STALE" ]; then
    [ "$good_since" -eq 0 ] && good_since=$now
    want=$([ $(( now - good_since )) -ge "$GIVE_BACK" ] && echo 0 || echo "")
    verdict="노트북 서빙 중 ($(( now - good_since ))초)"
  else
    good_since=0; want=1
    verdict="노트북 없음 (상태 ${state:-none}, ${age}초 전)"
  fi
  cur=$(kubectl -n $NS get deploy cloudflared -o jsonpath='{.spec.replicas}' 2>/dev/null)
  if [ -n "$want" ] && [ -n "$cur" ] && [ "$cur" != "$want" ]; then
    kubectl -n $NS scale deploy/cloudflared --replicas="$want" >/dev/null && echo "$(date +%T) 집컴 터널 $cur -> $want — $verdict"
  fi
  short=${verdict%% (*}
  [ "$short" != "$last" ] && echo "$(date +%T) $verdict" && last=$short
  sleep 5
done
