#!/usr/bin/env bash
# 노트북 역방향 터널이 다시 붙기 전에, 끊긴 옛 세션이 쥐고 있는 21434 포트를 놓아 준다.
# 같은 사용자(suvisdev)의 sshd-session 만 대상이라 sudo 가 필요 없다.
pids=$(ss -ltnpH 'sport = :21434' 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u)
for p in $pids; do
  kill "$p" 2>/dev/null && echo "옛 터널 세션 정리: pid $p"
done
exit 0
