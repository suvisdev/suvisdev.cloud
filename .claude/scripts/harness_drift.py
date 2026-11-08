#!/usr/bin/env python3
"""SessionStart 훅: 이 폴더의 하네스 파일이 origin/main과 다르면 세션에 알린다.

메인 폴더는 기능 브랜치에 머물 수 있다(10-20 결정). 그러면 세션이 읽는 CLAUDE.md와 훅 스크립트가 main보다
뒤처진다(11-08 점검: 57커밋 뒤, 자동 마무리 절이 없는 CLAUDE.md를 읽음). 파일을 덮어쓰면 브랜치가 더러워지므로
고치지 않고 알리기만 한다. 네트워크가 안 되면 마지막으로 받은 origin/main과 비교한다.
"""
import json
import subprocess
import sys

REF = "origin/main"
HARNESS = ["CLAUDE.md", "suvisdev/CLAUDE.md", ".claude/settings.json", ".claude/skill-routes.json",
           ".claude/scripts", ".claude/githooks", ".claude/rules"]


def git(*args: str, timeout: int = 10) -> str:
    return subprocess.run(["git", *args], text=True, capture_output=True, check=True, timeout=timeout).stdout


def drifted() -> list[str]:
    """origin/main에 있는 하네스 파일 중 작업 트리 내용이 다르거나 없는 것."""
    result = []
    for line in git("ls-tree", "-r", REF, "--", *HARNESS).splitlines():
        meta, path = line.split("\t", 1)
        expected = meta.split()[2]
        try:
            actual = git("hash-object", "--", path).strip()
        except subprocess.CalledProcessError:
            actual = ""
        if actual != expected:
            result.append(path)
    return result


def main() -> None:
    try:
        git("fetch", "-q", "origin", "main", timeout=15)
    except (subprocess.SubprocessError, OSError):
        pass
    try:
        files = drifted()
    except (subprocess.SubprocessError, OSError):
        return
    if not files:
        return
    shown = ", ".join(files[:8]) + (f" 외 {len(files) - 8}개" if len(files) > 8 else "")
    message = (f"[하네스 드리프트] 이 폴더의 하네스 파일이 기준 브랜치({REF})와 다르다: {shown}. 규칙의 기준은 {REF} 판이다 — "
               f"`git show {REF}:CLAUDE.md`(필요하면 suvisdev/CLAUDE.md도)로 읽고, 로드된 판과 다르면 {REF} 판을 따른다. "
               "이 폴더의 파일을 덮어쓰거나 브랜치를 바꾸는 것은 사용자에게 먼저 묻는다.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": message}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
    sys.exit(0)
