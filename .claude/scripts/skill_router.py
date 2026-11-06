#!/usr/bin/env python3
"""작업 구간에 맞는 스킬을 코드로 판정해 훅 컨텍스트로 알린다. 규칙은 .claude/skill-routes.json."""
import json
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

ROUTES = Path(__file__).resolve().parent.parent / "skill-routes.json"
INTENT = ROUTES.with_name("skill-intent.json")
OLLAMA_URL = os.environ.get("SKILL_ROUTER_OLLAMA_URL", "http://127.0.0.1:11434")
MAX_SKILLS = 3
INTENT_TIMEOUT_SECONDS = 5
MAX_PROMPT_CHARS = 2000


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


def intent_system_prompt(intent: dict) -> str:
    lines = [f"{example} => {json.dumps({'skills': [skill]}, ensure_ascii=False)}"
             for skill, examples in intent["examples"].items() for example in examples]
    lines += [f'{example} => {{"skills": []}}' for example in intent["no_skill_examples"]]
    return ("사용자 요청의 의도에 맞는 스킬을 아래 이름 중에서만 최대 2개 고른다. 고장·이상 증상 호소는 systematic-debugging, "
            "기능을 만들거나 넣어 달라는 요청은 ponytail이다. 코드 작업 요청이 아닌 단순 질문·인사는 빈 목록이다. "
            "JSON으로만 답한다.\n이름: " + ", ".join(intent["examples"]) + "\n예시:\n" + "\n".join(lines))


def intent_skills(prompt: str, seen: set[str]) -> list[tuple[str, str]]:
    """규칙에 안 걸린 요청만 무료 로컬 모델이 판단한다. 모델이 없거나 늦으면 판단 없이 진행한다."""
    intent = json.loads(INTENT.read_text(encoding="utf-8"))
    body = {
        "model": intent["model"], "stream": False, "format": "json",
        "options": {"temperature": 0, "num_predict": 60},
        "messages": [{"role": "system", "content": intent_system_prompt(intent)},
                     {"role": "user", "content": prompt[:MAX_PROMPT_CHARS]}],
    }
    request = urllib.request.Request(f"{OLLAMA_URL}/api/chat", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=INTENT_TIMEOUT_SECONDS) as response:
            picks = json.loads(json.load(response)["message"]["content"]).get("skills", [])
    except (OSError, ValueError, KeyError, AttributeError):
        return []
    if not isinstance(picks, list):
        return []
    # 모델이 지어낸 이름과 서브에이전트 스킬은 예시 목록에 없으므로 여기서 걸러진다.
    allowed = [p for p in picks if isinstance(p, str) and p in intent["examples"] and p not in seen]
    return [(skill, "요청 의도 판단") for skill in dict.fromkeys(allowed)][:MAX_SKILLS]


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
    if group == "prompt" and not any(re.search(rule["match"], text, re.IGNORECASE) for rule in rules):
        picked = intent_skills(text, seen)
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
