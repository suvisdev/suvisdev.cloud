#!/usr/bin/env bash
# 노트북 서빙 판단기 (노트북 유저 서비스 serve-agent)
# - 5초마다 노트북 앱을 끝까지 확인한다: Traefik → backend → (집컴) DB 를 타는 요청 1건.
# - 2번 연속 성공이면 노트북 cloudflared 1(서빙), 3번 연속 실패면 0(빠짐).
# - 매 주기 상태를 집컴 ~/serve/laptop_heartbeat 에 남긴다. 집컴 판단기는 이게 끊기거나 'serving'이 아니면 자기 터널을 켠다.
# DB·Redis는 집컴 한 곳뿐이라 두 터널이 잠깐 겹쳐도 데이터는 갈라지지 않는다.
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
NS=suvisdev
DESK=suvisdev@172.30.1.21
SSH=(ssh -i "$HOME/.ssh/home_desktop" -o BatchMode=yes -o ConnectTimeout=5 -o LogLevel=ERROR
     -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$HOME/.ssh/known_hosts_ollama_tunnel"
     -o ControlMaster=auto -o ControlPath="$HOME/.ssh/cm-serve-%r@%h" -o ControlPersist=120)
PROBE='/mova/search?q=%EC%9D%B8%ED%84%B4&limit=1'
ok=0; bad=0; last=""

while true; do
  tip=$(kubectl -n kube-system get svc traefik -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 8 -H 'Host: api.suvisdev.cloud' "http://${tip:-127.0.0.1}$PROBE" 2>/dev/null)
  if [ "$code" = "200" ]; then ok=$((ok+1)); bad=0; else bad=$((bad+1)); ok=0; fi
  want=""
  [ "$ok" -ge 2 ] && want=1
  [ "$bad" -ge 3 ] && want=0
  cur=$(kubectl -n $NS get deploy cloudflared -o jsonpath='{.spec.replicas}' 2>/dev/null)
  if [ -n "$want" ] && [ -n "$cur" ] && [ "$cur" != "$want" ]; then
    kubectl -n $NS scale deploy/cloudflared --replicas="$want" >/dev/null && echo "$(date +%T) 노트북 터널 $cur -> $want (앱 응답 $code)"
    cur=$want
  fi
  ready=$(kubectl -n $NS get deploy cloudflared -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
  if [ "$cur" = "1" ] && [ "${ready:-0}" -ge 1 ] && [ "$code" = "200" ]; then state=serving; else state=not-serving; fi
  [ "$state" != "$last" ] && echo "$(date +%T) 상태 $state (앱 $code, 터널 ${cur:-?}/${ready:-0})" && last=$state
  timeout 6 "${SSH[@]}" "$DESK" "mkdir -p ~/serve && echo '$(date +%s) $state $code' > ~/serve/laptop_heartbeat" >/dev/null 2>&1
  sleep 5
done
