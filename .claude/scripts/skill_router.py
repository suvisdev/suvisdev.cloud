#!/usr/bin/env python3
"""작업 구간에 맞는 스킬을 코드로 판정해 훅 컨텍스트로 알린다. 규칙은 .claude/skill-routes.json."""
import json
import re
import sys
import tempfile
from pathlib import Path

ROUTES = Path(__file__).resolve().parent.parent / "skill-routes.json"
MAX_SKILLS = 3


def target(event: dict) -> tuple[str, str]:
    """훅 입력에서 (규칙 묶음, 검사할 문자열)을 고른다. 해당 없으면 빈 묶음."""
    name = event.get("hook_event_name")
    tool_input = event.get("tool_input") or {}
    if name == "UserPromptSubmit":
        prompt = event.get("prompt", "")
        # 사용자가 /스킬로 직접 고른 경우는 라우팅하지 않는다.
        return ("", "") if prompt.lstrip().startswith("/") else ("prompt", prompt)
    if name == "PostToolUseFailure":
        return "command_failure", tool_input.get("command", "")
    if event.get("tool_name") == "Bash":
        return "command", tool_input.get("command", "")
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    root = event.get("cwd", "")
    return "file", path[len(root) + 1 :] if root and path.startswith(root + "/") else path


def select(rules: list[dict], text: str, seen: set[str]) -> list[tuple[str, str]]:
    """맞는 규칙에서 이번 세션에 아직 안 알린 스킬을 표 순서대로 MAX_SKILLS개까지 고른다."""
    picked: dict[str, str] = {}
    for rule in rules:
        if not re.search(rule["match"], text, re.IGNORECASE):
            continue
        for skill in rule["skills"]:
            if skill not in picked and (rule.get("repeat") or skill not in seen):
                picked[skill] = rule["why"]
    return list(picked.items())[:MAX_SKILLS]


def main() -> None:
    event = json.load(sys.stdin)
    group, text = target(event)
    if not group or not text:
        return

    session = re.sub(r"[^\w-]", "_", str(event.get("session_id", "none")))
    state = Path(tempfile.gettempdir()) / "claude-skill-router" / session
    seen = set(state.read_text().split()) if state.exists() else set()

    rules = json.loads(ROUTES.read_text(encoding="utf-8"))[group]
    picked = select(rules, text, seen)
    if not picked:
        return

    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("\n".join(sorted(seen | {skill for skill, _ in picked})))

    listing = ", ".join(f"`{skill}`({why})" for skill, why in picked)
    message = (
        f"[스킬 라우터] 이 작업 구간에 해당: {listing}. 답하거나 다른 도구를 쓰기 전에 Skill 도구로 먼저 불러 "
        "따른다(이번 세션에 이미 불렀으면 생략). 가능한 스킬 목록에 없으면 건너뛴다. CLAUDE.md와 사용자 "
        "지시가 스킬보다 우선한다. 작업과 무관한 오탐이면 무시하고 진행한다."
    )
    output = {"hookEventName": event["hook_event_name"], "additionalContext": message}
    # PreToolUse 컨텍스트는 도구가 실행된 뒤에야 모델에게 보이므로, 처음 한 번은 막아서 먼저 읽게 한다.
    if event["hook_event_name"] == "PreToolUse" and {skill for skill, _ in picked} - seen:
        del output["additionalContext"]
        output["permissionDecision"] = "deny"
        output["permissionDecisionReason"] = f"{message} 스킬을 확인한 뒤 같은 도구를 다시 호출한다."
    print(json.dumps({"hookSpecificOutput": output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
