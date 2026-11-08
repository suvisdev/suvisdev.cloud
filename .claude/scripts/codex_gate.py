#!/usr/bin/env python3
"""커밋·머지 관문과 자동 마무리 트리거. 절차는 루트 CLAUDE.md "자동 마무리".

훅(인자 없음): `gh pr merge`를 Codex 승인·CI·선행 작업으로 막고, git 훅을 끄는 명령을 막으며, 세션이 미완료 변경을 남기고 끝나면 마무리로 돌려보낸다.
pre-commit·pre-push: .claude/githooks가 부른다. git이 넘긴 실제 내용을 판정하므로 명령 문자열을 해석하지 않는다.
review: 스테이지된 변경을 Codex에 리뷰받아 OK면 승인을 기록한다. 종료 코드 0 OK, 1 지적, 2 실행 실패.
confirm-prereq <PR>: 사용자가 선행 작업 완료를 확인해 준 뒤에만 실행한다.

절차를 빠뜨리는 실수를 막는 장치이고 보안 경계가 아니다. 승인 파일을 직접 쓰는 등의 고의 우회는 막지 않는다.
자동 마무리 트리거는 Edit·Write로 고친 파일만 추적한다. Bash로만 고친 파일은 빠지지만 커밋·머지 관문은 그대로 적용된다.
"""
import hashlib
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

# 승인 범위 밖 경로. 워크로그 등 문서는 리뷰 뒤에 고쳐도 승인이 유지된다.
CODE_PATHS = [".", ":(exclude,glob)**/_docs/**"]
# 머지되면 바로 운영에 배포되므로 사용자 작업이 먼저 필요한 변경.
PREREQ = re.compile(r"(^|/)alembic/versions/|(^|/)\.env\.example$")
# .github/workflows 경로 필터와 맞춘다. 걸리는 변경이 있으면 그 워크플로가 등록되고 끝나야 한다.
CI_WORKFLOWS = {
    "backend-ci": re.compile(r"^(suvisdev|k8s)/(?!.*\.md$)|^\.github/workflows/backend-[^/]*\.yml$"),
    "frontend-ci": re.compile(r"^suvis/|^\.github/workflows/frontend-ci\.yml$"),
    "gildle-ci": re.compile(r"^gildle/|^\.github/workflows/gildle-ci\.yml$"),
}
# 커밋 메시지·스크립트 본문은 명령이 아니다.
HEREDOC = re.compile(r"""<<-?\s*['"]?(\w+)['"]?[^\n]*\n.*?\n\s*\1\b""", re.S)
OPERATORS = set(";&|()<>\n")
MERGE_VALUE_FLAGS = {"-t", "--subject", "-b", "--body", "-F", "--body-file", "-A", "--author-email", "--match-head-commit"}
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "findings"],
    "properties": {
        "verdict": {"type": "string", "enum": ["OK", "ISSUES"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["file", "line", "summary"],
                "properties": {"file": {"type": "string"}, "line": {"type": "integer"}, "summary": {"type": "string"}},
            },
        },
    },
}
PROMPT = """저장소의 변경을 코드 리뷰한다. 대상 diff는 파일 {diff}에 있다. 필요하면 저장소 코드를 읽어 확인한다. 파일은 고치지 않는다.
실제 동작을 깨는 버그·보안 문제·회귀만 지적한다. 취향과 사소한 스타일은 지적하지 않는다.
문제가 없으면 verdict를 OK, 있으면 ISSUES로 하고 findings에 적는다."""


def git(repo, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=True).stdout.strip()


def change_diff(repo, treeish: str, *heads: str) -> str:
    """대상의 코드 변경(문서 제외). 내용이 같으면 main이 움직이거나 커밋을 나눠도 결과가 같다.
    heads가 여럿이면 그 머지 커밋을 기준으로 삼는다. 충돌을 푼 머지에서 main 변경이 섞이지 않는다."""
    base = git(repo, "merge-base", "origin/main", *heads)
    return git(repo, "diff", "--binary", base, treeish, "--", *CODE_PATHS)


def commit_parents(repo) -> list[str]:
    """곧 만들 커밋의 부모. 머지 중이면 MERGE_HEAD도 포함한다."""
    merging = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "MERGE_HEAD"))
    return ["HEAD", *(merging.read_text().split() if merging.exists() else [])]


def diff_key(diff: str) -> str:
    return hashlib.sha256(diff.encode()).hexdigest()


def change_key(repo, treeish: str, *heads: str) -> str | None:
    diff = change_diff(repo, treeish, *heads)
    return diff_key(diff) if diff else None


def record_file(repo, name: str) -> Path:
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")) / name


def recorded(repo, name: str) -> set[str]:
    path = record_file(repo, name)
    return set(path.read_text().split()) if path.exists() else set()


def record(repo, name: str, key: str) -> None:
    with record_file(repo, name).open("a") as file:
        file.write(key + "\n")


def pre_commit() -> int:
    """git이 넘긴 인덱스가 곧 커밋될 내용이다(`-a`·파일 지정 커밋 포함)."""
    key = change_key(".", git(".", "write-tree"), *commit_parents("."))
    if key is None or key in recorded(".", "codex-approved"):
        return 0
    print("[Codex 관문] 승인이 없는 변경이다. 스테이지 후 `python3 .claude/scripts/codex_gate.py review`로 리뷰받는다.", file=sys.stderr)
    return 1


def pre_push() -> int:
    """git이 stdin으로 넘기는 실제 대상 ref를 본다."""
    for line in sys.stdin:
        parts = line.split()
        if len(parts) == 4 and parts[2] == "refs/heads/main":
            print("[Codex 관문] main에 직접 푸시하지 않는다. PR로 올린다.", file=sys.stderr)
            return 1
    return 0


def simple_commands(command: str) -> list[list[str]]:
    """따옴표를 지켜 토큰으로 나누고 셸 연산자에서 끊는다."""
    lexer = shlex.shlex(HEREDOC.sub("", command), posix=True, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    commands: list[list[str]] = [[]]
    for token in lexer:
        if set(token) <= OPERATORS:
            commands.append([])
        else:
            commands[-1].append(token.lstrip("$(`"))
    return [words for words in commands if words]


def nested_commands(words: list[str]) -> list[list[str]]:
    """`sh -c "..."`의 안쪽 명령."""
    return [inner for i, word in enumerate(words[:-1])
            if word == "-c" and any(w.rsplit("/", 1)[-1] in ("sh", "bash") for w in words[:i])
            for inner in simple_commands(words[i + 1])]


def merge_block(repo: str, options: list[str]) -> str | None:
    if any(w in ("-R", "--repo") or w.startswith("--repo=") for w in options):
        return "다른 저장소 PR의 머지는 관문이 판정할 수 없다."
    selectors = [w for i, w in enumerate(options)
                 if not w.startswith("-") and (i == 0 or options[i - 1] not in MERGE_VALUE_FLAGS)]
    view = subprocess.run(["gh", "pr", "view", *selectors[:1], "--json", "number,headRefOid"],
                          cwd=repo, text=True, capture_output=True, check=True)
    pr = json.loads(view.stdout)
    head = pr["headRefOid"]
    git(repo, "fetch", "-q", "origin", "main", f"pull/{pr['number']}/head")

    key = change_key(repo, head, head)
    if key is not None and key not in recorded(repo, "codex-approved"):
        return f"PR #{pr['number']}의 현재 코드는 Codex 승인을 받지 않았다. 그 코드를 리뷰받은 뒤 머지한다."

    base = git(repo, "merge-base", "origin/main", head)
    changed = git(repo, "diff", "--name-only", base, head).splitlines()
    checks = subprocess.run(["gh", "pr", "checks", str(pr["number"]), "--json", "name,bucket,workflow"],
                            cwd=repo, text=True, capture_output=True)
    if checks.returncode and not checks.stdout.strip() and "no checks reported" not in checks.stderr:
        return f"CI 상태를 확인하지 못했다: {checks.stderr.strip()}"
    results = json.loads(checks.stdout or "[]")
    # 푸시 직후에는 일부 워크플로가 아직 등록되지 않았을 수 있다.
    registered = {c["workflow"] for c in results}
    missing = [w for w, paths in CI_WORKFLOWS.items() if w not in registered and any(paths.search(p) for p in changed)]
    if missing:
        return f"CI 대상 변경인데 {', '.join(missing)} 검사가 아직 없다. 등록될 때까지 기다린 뒤 `gh pr checks --watch`로 확인한다."
    unfinished = [c["name"] for c in results if c["bucket"] not in ("pass", "skipping")]
    if unfinished:
        return f"CI가 끝나지 않았거나 실패했다: {', '.join(unfinished)}. `gh pr checks --watch`로 확인한다."

    needs = [path for path in changed if PREREQ.search(path)]
    if needs and head not in recorded(repo, "prereq-confirmed"):
        return (f"사용자 선행 작업이 필요한 변경이다({', '.join(needs)}). 머지하지 말고 필요한 작업을 사용자에게 알린다. "
                f"사용자가 완료를 확인해 주면 `python3 .claude/scripts/codex_gate.py confirm-prereq {pr['number']}` 후 머지한다.")
    # 판정한 커밋에 머지를 고정한다. 그 사이 PR에 푸시되면 GitHub가 머지를 거부한다.
    pinned = [v for flag, v in zip(options, options[1:]) if flag == "--match-head-commit"]
    pinned += [w.split("=", 1)[1] for w in options if w.startswith("--match-head-commit=")]
    if pinned != [head]:
        return f"판정한 커밋에 고정해서 머지한다: `gh pr merge {pr['number']} --merge --match-head-commit {head}`."
    return None


def disables_git_hooks(words: list[str]) -> bool:
    """git 호출 중 훅을 건너뛰거나 훅 경로를 바꾸는 형태만 고른다. 조회·검색은 해당하지 않는다."""
    if "git" not in words:
        return False
    args = words[words.index("git") + 1:]
    if any(word == "-c" and "hooksPath" in value for word, value in zip(args, args[1:])):
        return True
    if "config" in args and any("hooksPath" in w for w in args):
        return not any(w in ("--get", "--get-all", "--list", "-l", "get", "list") for w in args)
    if "commit" in args and any(re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", w) for w in args):
        return True
    return ("commit" in args or "push" in args) and "--no-verify" in args


def bash_block(command: str, cwd: str) -> str | None:
    commands = simple_commands(command)
    repo = cwd
    if commands and commands[0][0] == "cd" and len(commands[0]) == 2:
        repo = str(Path(cwd) / commands[0][1])
        commands = commands[1:]
    commands = [c for words in commands for c in (words, *nested_commands(words))]
    for words in commands:
        if disables_git_hooks(words):
            return "git 훅을 끄거나 바꾸는 명령은 쓰지 않는다."
        for i in range(len(words) - 2):
            if words[i].rsplit("/", 1)[-1] == "gh" and words[i + 1:i + 3] == ["pr", "merge"]:
                # 앞선 명령이 PR을 바꾸면 판정한 내용과 실제 머지 대상이 달라지고, 뒤의 머지는 판정을 건너뛴다.
                if len(commands) > 1:
                    return "머지는 다른 명령과 잇지 말고 단독으로 실행한다."
                return merge_block(repo, words[i + 3:])
    return None


def session_file(event: dict) -> Path:
    session = re.sub(r"[^\w-]", "_", str(event.get("session_id", "none")))
    return Path(tempfile.gettempdir()) / "claude-finish" / session


def unfinished_files(event: dict) -> list[str]:
    """이번 세션에 고친 파일 중 커밋이 안 됐거나 main에 아직 없는 것."""
    state = session_file(event)
    if not state.exists():
        return []
    result = []
    for name in sorted(set(state.read_text().splitlines())):
        path = Path(name)
        try:
            repo = git(path.parent, "rev-parse", "--show-toplevel")
            dirty = git(repo, "status", "--porcelain", "--", name)
            ahead = git(repo, "diff", "--name-only", "origin/main...HEAD", "--", name)
        except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError):
            continue
        if dirty or ahead:
            result.append(name)
    return result


def handle_hook(event: dict) -> dict | None:
    name = event.get("hook_event_name")
    tool_input = event.get("tool_input") or {}
    if name == "Stop":
        if event.get("stop_hook_active"):
            return None
        files = unfinished_files(event)
        if not files:
            return None
        return {
            "decision": "block",
            "reason": "[자동 마무리] 미완료 변경: " + ", ".join(files) + ". 사용자에게 묻지 말고 CLAUDE.md '자동 마무리' "
                      "절차로 머지까지 끝낸다. 사용자가 커밋을 원하지 않았거나 이미 보류 사유(선행 작업, Codex 무응답)를 "
                      "보고했으면 그 사유만 보고하고 끝낸다.",
        }
    if event.get("tool_name") != "Bash":
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if path:
            state = session_file(event)
            state.parent.mkdir(parents=True, exist_ok=True)
            with state.open("a") as file:
                file.write(path + "\n")
        return None
    command = tool_input.get("command", "")
    try:
        reason = bash_block(command, event.get("cwd", "."))
    except (subprocess.CalledProcessError, OSError) as error:
        reason = f"관문 판정 실패: {getattr(error, 'stderr', '') or error}"
    except ValueError as error:
        # 셸 문법으로 읽히지 않는 문자열. 머지가 들어 있을 때만 통과시키지 않는다.
        reason = f"관문 판정 실패: {error}" if "merge" in command else None
    if reason is None:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": f"[Codex 관문] {reason}"}}


def review() -> int:
    repo = git(".", "rev-parse", "--show-toplevel")
    # 승인 키와 리뷰 대상을 같은 스냅샷에서 만든다.
    reviewed = change_diff(repo, git(repo, "write-tree"), *commit_parents(repo))
    if not reviewed:
        print("리뷰할 코드 변경이 없다(스테이지 확인, 문서만 바뀌면 리뷰 면제).")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        diff, schema, answer = Path(tmp, "change.diff"), Path(tmp, "schema.json"), Path(tmp, "answer.json")
        diff.write_text(reviewed)
        schema.write_text(json.dumps(SCHEMA))
        try:
            run = subprocess.run(
                ["codex", "exec", "-s", "read-only", "--ephemeral", "--output-schema", str(schema), "-o", str(answer),
                 PROMPT.format(diff=diff)],
                cwd=repo, stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=1200,
            )
            result = json.loads(answer.read_text())
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            print(f"Codex 실행 실패: {error}")
            return 2
    if run.returncode or result.get("verdict") not in ("OK", "ISSUES"):
        print(f"Codex 실행 실패(종료 코드 {run.returncode}): {run.stderr[-500:]}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["verdict"] != "OK":
        return 1
    record(repo, "codex-approved", diff_key(reviewed))
    return 0


def confirm_prereq(number: str) -> int:
    repo = git(".", "rev-parse", "--show-toplevel")
    view = subprocess.run(["gh", "pr", "view", number, "--json", "headRefOid"], cwd=repo, text=True,
                          capture_output=True, check=True)
    record(repo, "prereq-confirmed", json.loads(view.stdout)["headRefOid"])
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "pre-commit":
            return pre_commit()
        if action == "pre-push":
            return pre_push()
        return review() if action == "review" else confirm_prereq(sys.argv[2])
    output = handle_hook(json.load(sys.stdin))
    if output:
        print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
