"""실행: python3 -m unittest discover -s .claude/scripts -p 'test_skill_router.py'"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROUTER = SCRIPTS / "skill_router.py"
CLAUDE_DIR = SCRIPTS.parent
ROUTES = json.loads((CLAUDE_DIR / "skill-routes.json").read_text(encoding="utf-8"))
CWD = "/repo"
# 서브에이전트를 띄우는 스킬. 사용자가 말했을 때만 연결돼야 하므로 why에 명시 요청임을 적는다.
SUBAGENT_SKILLS = {"pstack:architect", "pstack:how", "pstack:why", "pstack:thermos", "pstack:interrogate",
                   "anthropic-skills:deep-research", "pstack:arena", "pstack:swarm", "pstack:reflect",
                   "pstack:no-comments", "pstack:babysit"}


class RouterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.session = "s1"
        self.ollama_url = "http://127.0.0.1:9"

    def run_hook(self, **event) -> str:
        event = {"session_id": self.session, "cwd": CWD, **event}
        result = subprocess.run(
            [sys.executable, str(ROUTER)], input=json.dumps(event), text=True, capture_output=True,
            env={**os.environ, "TMPDIR": self.tmp.name, "SKILL_ROUTER_OLLAMA_URL": self.ollama_url}, check=True,
        )
        if not result.stdout:
            return ""
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], event["hook_event_name"])
        self.denied = output.get("permissionDecision") == "deny"
        return output.get("permissionDecisionReason") or output["additionalContext"]

    def prompt(self, text):
        return self.run_hook(hook_event_name="UserPromptSubmit", prompt=text)

    def edit(self, path):
        return self.run_hook(hook_event_name="PreToolUse", tool_name="Edit",
                             tool_input={"file_path": f"{CWD}/{path}"})

    def bash(self, command):
        return self.run_hook(hook_event_name="PreToolUse", tool_name="Bash", tool_input={"command": command})

    def test_prompt_routes(self):
        for text, skill in [
            ("로그인 하면 502 오류가 나", "systematic-debugging"),
            ("구글 로그인 안돼", "systematic-debugging"),
            ("이 라이브러리 쓸까", "ponytail"),
            ("배포 계획 세워줘", "writing-plans"),
            ("코드 리뷰 해줘", "code-review"),
            ("채팅 응답이 느려", "pstack:benchmark-checklist"),
            ("엑셀로 뽑아줘", "anthropic-skills:xlsx"),
            ("CI 실패 고쳐줘", "pstack:fix-ci"),
        ]:
            with self.subTest(text):
                self.session = text
                self.assertIn(f"`{skill}`", self.prompt(text))

    def test_domain_word_review_is_not_code_review(self):
        self.assertNotIn("code-review", self.prompt("mova 영화 리뷰 감성 수치 알려줘"))

    def test_plain_question_gets_nothing(self):
        self.assertEqual(self.prompt("오늘 날짜 알려줘"), "")

    def test_explicit_slash_command_is_left_alone(self):
        self.assertEqual(self.prompt("/code-review 오류 봐줘"), "")

    def test_subagent_skills_need_explicit_words(self):
        for text in ["버그 고쳐줘", "기능 구현해줘", "이거 어떻게 동작해?", "왜 이렇게 됐어?", "코드 리뷰 해줘"]:
            with self.subTest(text):
                self.session = text
                for skill in SUBAGENT_SKILLS:
                    self.assertNotIn(skill, self.prompt(text))
        self.session = "explicit"
        self.assertIn("pstack:thermos", self.prompt("이 브랜치 심층 리뷰 해줘"))

    def test_file_routes_use_repo_relative_path(self):
        self.assertIn("pstack:typescript-best-practices", self.edit("suvis/components/a.tsx"))
        self.assertIn("pstack:principle-make-operations-idempotent", self.edit("k8s/backend.yaml"))
        self.assertIn("pstack:principle-boundary-discipline", self.edit("suvisdev/apps/mova/adapter/outbound/x.py"))
        self.assertIn("pstack:principle-test-behavior-not-implementation", self.edit("suvisdev/apps/mova/tests/test_a.py"))

    def test_docs_edit_gets_nothing(self):
        self.assertEqual(self.edit("_docs/WORK_LOG_MAINPAGE.md"), "")

    def test_same_skill_is_announced_once_per_session(self):
        self.assertIn("ponytail", self.edit("suvisdev/main.py"))
        self.assertEqual(self.edit("suvisdev/other.py"), "")
        self.session = "s2"
        self.assertIn("ponytail", self.edit("suvisdev/other.py"))

    def test_commit_gate_repeats_every_commit(self):
        for _ in range(2):
            self.assertIn("verification-before-completion", self.bash('git commit -m "feat: x"'))
        self.assertIn("verification-before-completion", self.bash("gh pr merge 12 --merge"))
        self.assertEqual(self.bash("git status"), "")

    def test_first_edit_is_denied_once_then_retry_passes(self):
        self.assertIn("ponytail", self.edit("suvisdev/main.py"))
        self.assertTrue(self.denied)
        self.assertEqual(self.edit("suvisdev/main.py"), "")

    def test_commit_is_denied_once_then_only_reminded(self):
        self.bash('git commit -m "a"')
        self.assertTrue(self.denied)
        self.assertIn("verification-before-completion", self.bash('git commit -m "a"'))
        self.assertFalse(self.denied)

    def test_commit_text_inside_other_command_is_ignored(self):
        self.assertEqual(self.bash("""echo 'git commit -m a' > note.txt"""), "")
        self.assertIn("verification-before-completion", self.bash('cd x && git -C y commit -m a'))

    def test_prompt_and_failure_only_add_context(self):
        self.prompt("버그 고쳐줘")
        self.assertFalse(self.denied)

    def test_failed_check_routes_but_other_failure_does_not(self):
        fail = lambda c: self.run_hook(hook_event_name="PostToolUseFailure", tool_name="Bash",
                                       tool_input={"command": c}, error="exit 1")
        self.assertEqual(fail("ls /nope"), "")
        self.assertIn("systematic-debugging", fail("pytest -m 'not gpu and not ollama'"))

    def test_at_most_three_skills_at_once(self):
        context = self.prompt("버그 구현 계획 코드 리뷰 보안 리뷰 엑셀")
        self.assertLessEqual(context.count("`"), 6)

    def test_routes_are_valid(self):
        for group in ROUTES.values():
            for rule in group:
                re.compile(rule["match"])
                self.assertTrue(rule["skills"] and rule["why"])

    def test_project_skills_all_routed_and_exist(self):
        routed = {s for group in ROUTES.values() for rule in group for s in rule["skills"]}
        local = {p.name for p in (CLAUDE_DIR / "skills").iterdir() if p.is_dir()}
        self.assertLessEqual(local, routed)

    def test_installed_pstack_skills_are_all_routed(self):
        routed = {s for group in ROUTES.values() for rule in group for s in rule["skills"]}
        installed = {f"pstack:{p.name}" for p in Path.home().glob(".claude/plugins/cache/pstack-claude/pstack/*/skills/*")}
        self.assertEqual(installed - routed, set())

    def test_subagent_routes_are_labelled_explicit(self):
        for rule in ROUTES["prompt"]:
            if SUBAGENT_SKILLS & set(rule["skills"]):
                self.assertIn("명시 요청", rule["why"])


class IntentTest(RouterTest):
    def start_model(self, content):
        calls = self.calls = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                calls.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"message": {"content": content}}).encode())

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.ollama_url = f"http://127.0.0.1:{server.server_port}"

    def test_model_routes_intent_the_rules_miss(self):
        self.start_model('{"skills": ["systematic-debugging"]}')
        self.assertIn("`systematic-debugging`", self.prompt("로그인 눌러도 아무 반응이 없어"))
        self.assertFalse(self.denied)

    def test_rule_match_skips_the_model(self):
        self.start_model('{"skills": ["dataviz"]}')
        context = self.prompt("로그인 오류가 나")
        self.assertIn("systematic-debugging", context)
        self.assertEqual(self.calls, [])

    def test_model_cannot_pick_unknown_or_subagent_skills(self):
        self.start_model('{"skills": ["today-date", "pstack:thermos", "pstack:arena"]}')
        self.assertEqual(self.prompt("로그인 눌러도 반응이 없어"), "")

    def test_model_garbage_is_ignored(self):
        for content in ["not json", '{"skills": "run"}', '[1, 2]', '{"skills": [1]}']:
            self.start_model(content)
            self.assertEqual(self.prompt("반응이 없어"), "", content)

    def test_model_down_means_no_context_and_no_failure(self):
        self.assertEqual(self.prompt("로그인 눌러도 반응이 없어"), "")

    def test_files_and_commands_never_call_the_model(self):
        self.start_model('{"skills": ["dataviz"]}')
        self.edit("_docs/a.md")
        self.bash("git status")
        self.assertEqual(self.calls, [])

    def test_slash_command_never_calls_the_model(self):
        self.start_model('{"skills": ["dataviz"]}')
        self.prompt("/code-review")
        self.assertEqual(self.calls, [])

    def test_model_pick_is_announced_once_per_session(self):
        self.start_model('{"skills": ["run"]}')
        self.assertIn("`run`", self.prompt("이거 좀 봐"))
        self.assertEqual(self.prompt("이거 좀 봐"), "")

    def test_long_paste_is_truncated(self):
        self.start_model('{"skills": []}')
        self.prompt("가" * 5000)
        self.assertLessEqual(len(self.calls[0]["messages"][1]["content"]), 2000)

    def test_intent_skills_exclude_subagent_skills(self):
        intent = json.loads((CLAUDE_DIR / "skill-intent.json").read_text(encoding="utf-8"))
        self.assertEqual(SUBAGENT_SKILLS & set(intent["examples"]), set())


if __name__ == "__main__":
    unittest.main()
