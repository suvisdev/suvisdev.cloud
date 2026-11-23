#!/usr/bin/env python3
"""SessionStart 훅: 이 폴더의 하네스 파일이 origin/main과 다르면 세션에 알린다.

메인 폴더는 기능 브랜치에 머물 수 있다(10-20 결정). 그러면 세션이 읽는 CLAUDE.md와 훅 스크립트가 main보다
뒤처진다(11-08 점검: 57커밋 뒤, 자동 마무리 절이 없는 CLAUDE.md를 읽음). 파일을 덮어쓰면 브랜치가 더러워지므로
고치지 않고 알리기만 한다. 네트워크가 안 되면 마지막으로 받은 origin/main과 비교한다.
"""
import json
import os
import subprocess
import sys

REF = "origin/main"
HARNESS = ["CLAUDE.md", "suvisdev/CLAUDE.md", "_docs/SPEC.md", "_docs/STATE.md", ".claude/settings.json", ".claude/skill-routes.json",
           ".claude/scripts", ".claude/githooks", ".claude/rules"]


def git(*args: str, timeout: int = 10) -> str:
    return subprocess.run(["git", *args], text=True, capture_output=True, check=True, timeout=timeout).stdout


# 작업 브랜치가 직접 쓰는 상태 파일. 이 브랜치에서 고친 판은 main보다 새것이라 알리지 않는다.
STATE_FILES = {"_docs/SPEC.md", "_docs/STATE.md"}


def drifted() -> list[str]:
    """origin/main에 있는 하네스 파일 중 작업 트리 내용이 다르거나 없는 것."""
    try:
        base = git("merge-base", "HEAD", REF).strip()
    except subprocess.CalledProcessError:
        base = ""  # 공통 조상이 없다(얕은 클론 등). 상태 파일도 그냥 비교한다.
    result = []
    for line in git("ls-tree", "-r", REF, "--", *HARNESS).splitlines():
        meta, path = line.split("\t", 1)
        expected = meta.split()[2]
        try:
            actual = git("hash-object", "--", path).strip()
        except subprocess.CalledProcessError:
            actual = ""
        own = path in STATE_FILES and has_text(path) and expected == base_blob(base, path) != actual  # main은 그대로, 이 브랜치만 고침
        if (actual != expected and not own) or (path in STATE_FILES and os.path.islink(path)):
            result.append(path)
    return result


def has_text(path: str) -> bool:
    try:
        return not os.path.islink(path) and bool(open(path, encoding="utf-8").read().strip())
    except (OSError, UnicodeDecodeError):
        return False


def base_blob(base: str, path: str) -> str:
    if not base:
        return ""
    try:
        return git("rev-parse", "-q", "--verify", f"{base}:{path}").strip()
    except subprocess.CalledProcessError:
        return ""


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
    files.sort(key=lambda f: f not in STATE_FILES and not f.endswith("CLAUDE.md"))  # 규칙·상태 파일은 잘리지 않게 맨 앞
    shown = ", ".join(files[:8]) + (f" 외 {len(files) - 8}개" if len(files) > 8 else "")
    message = (f"[하네스 드리프트] 이 폴더의 하네스 파일이 기준 브랜치({REF})와 다르다: {shown}. 규칙의 기준은 {REF} 판이다 — "
               f"목록의 파일만 각각 `git show {REF}:<파일>`로 읽고, 로드된 판과 다르면 {REF} 판을 따른다. "
               + ("CLAUDE.md가 목록에 있으면 `@` 불러오기가 안 됐을 수 있으니 이 폴더의 _docs/SPEC.md·STATE.md도 읽는다(목록에 있는 것은 위처럼 기준 판). "
                  if "CLAUDE.md" in files else "")
               + "이 폴더의 파일을 덮어쓰거나 브랜치를 바꾸는 것은 사용자에게 먼저 묻는다.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": message}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
    sys.exit(0)
