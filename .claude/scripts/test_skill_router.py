"""실행: python3 -m unittest discover -s .claude/scripts -p 'test_skill_router.py'"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
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

    def run_hook(self, **event) -> str:
        event = {"session_id": self.session, "cwd": CWD, **event}
        result = subprocess.run(
            [sys.executable, str(ROUTER)], input=json.dumps(event), text=True, capture_output=True,
            env={**os.environ, "TMPDIR": self.tmp.name}, check=True,
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


if __name__ == "__main__":
    unittest.main()
