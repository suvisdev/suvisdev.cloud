#!/usr/bin/env bash
# 집컴 올라마 예열기
# - 임베딩(bge-m3)은 집컴에 늘 올려 둔다: 노트북이 빠진 직후 로딩(50~70초)을 도메인 챗봇·mova 검색이 떠안아
#   504·빈 추천이 났다(10-05). 메모리는 약 1GB.
# - 판단 모델(exaone3.5:2.4b)은 노트북이 빠지는 순간 예열하고, 노트북이 2분 넘게 돌아와 있으면 내린다.
#   둘 다 상주시키면 배포 때 집컴 메모리(8.9GB)가 모자라 DB가 죽었다(10-05).
RESIDENT=(bge-m3)
ON_DEMAND=(exaone3.5:2.4b)
OLLAMA=http://127.0.0.1:11434
UNLOAD_AFTER=120   # 노트북이 이만큼(초) 연속으로 붙어 있으면 ON_DEMAND 모델을 내린다
up_since=0

laptop_state() { curl -s -m 3 "127.0.0.1:8404/;csv" | awk -F, '$1=="ollama" && $2=="laptop"{print $18}'; }
loaded() { curl -s -m 3 "$OLLAMA/api/ps" | grep -q "\"name\":\"$1"; }
load() {
  local s; s=$(date +%s)
  case "$1" in
    bge-m3) curl -s -m 300 "$OLLAMA/api/embed" -d "{\"model\":\"$1\",\"input\":\"\",\"keep_alive\":\"-1m\"}" >/dev/null ;;
    *)      curl -s -m 300 "$OLLAMA/api/generate" -d "{\"model\":\"$1\",\"keep_alive\":\"-1m\"}" >/dev/null ;;
  esac
  echo "$(date +%T) 집컴 $1 올림 ($(( $(date +%s) - s ))초)"
}
unload() { curl -s -m 30 "$OLLAMA/api/generate" -d "{\"model\":\"$1\",\"keep_alive\":0}" >/dev/null; }

while true; do
  pids=()
  for m in "${RESIDENT[@]}"; do
    if curl -s -m 3 "$OLLAMA/api/version" >/dev/null && ! loaded "$m"; then
      echo "$(date +%T) 상주 모델 $m 없음 — 올림"; load "$m" & pids+=($!)
    fi
  done
  st=$(laptop_state)
  now=$(date +%s)
  if [ "$st" = "UP" ]; then
    [ "$up_since" -eq 0 ] && up_since=$now
    if [ $((now - up_since)) -ge "$UNLOAD_AFTER" ]; then
      for m in "${ON_DEMAND[@]}"; do
        if loaded "$m"; then unload "$m"; echo "$(date +%T) 노트북 복귀 ${UNLOAD_AFTER}초 — 집컴 $m 내림"; fi
      done
    fi
  elif [ -n "$st" ]; then
    up_since=0
    for m in "${ON_DEMAND[@]}"; do
      if ! loaded "$m"; then
        echo "$(date +%T) 노트북 상태 $st — 집컴 $m 예열 시작"; load "$m" & pids+=($!)
      fi
    done
  fi
  [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
  sleep 3
done
