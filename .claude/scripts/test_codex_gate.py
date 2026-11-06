"""실행: python3 -m unittest discover -s .claude/scripts -p 'test_codex_gate.py'
진짜 git 저장소에 진짜 git 훅과 가짜 codex·gh를 붙여 관문 동작을 본다."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
GATE = SCRIPTS / "codex_gate.py"
GITHOOKS = SCRIPTS.parent / "githooks"

FAKE_CODEX = """#!/bin/sh
[ -n "$FAKE_CODEX_FAIL" ] && exit 3
while [ $# -gt 0 ]; do [ "$1" = -o ] && out=$2; shift; done
printf '{"verdict":"%s","findings":[]}' "${FAKE_VERDICT:-OK}" > "$out"
"""
FAKE_GH = """#!/bin/sh
case "$2" in
  view)
    echo "$3" >> "$FAKE_GH_LOG"
    printf '{"number":7,"headRefOid":"%s"}' "$(git rev-parse HEAD)" ;;
  checks)
    if [ -n "$FAKE_NO_CHECKS" ]; then echo 'no checks reported' >&2; exit 1; fi
    if [ -n "$FAKE_CHECKS_DOWN" ]; then echo 'network down' >&2; exit 1; fi
    printf '[{"name":"backend","workflow":"backend-ci","bucket":"%s"}]' "${FAKE_BUCKET:-pass}" ;;
esac
"""


class GateTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / "repo"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in (("codex", FAKE_CODEX), ("gh", FAKE_GH)):
            path = self.bin / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        self.env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "TMPDIR": str(self.root),
                    "FAKE_GH_LOG": str(self.root / "gh.log"), "CLAUDECODE": "1"}
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.root / "origin.git"], check=True)
        subprocess.run(["git", "clone", "-q", self.root / "origin.git", self.repo], check=True, capture_output=True)
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.git("checkout", "-q", "-b", "main")
        self.write("a.py", "1\n")
        self.git("add", ".")
        self.git("commit", "-qm", "init")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "-b", "feat")
        scripts = self.repo / ".claude/scripts"
        scripts.mkdir(parents=True)
        shutil.copy(GATE, scripts)
        shutil.copytree(GITHOOKS, self.repo / ".claude/githooks")
        (self.repo / ".git/info/exclude").write_text(".claude/\n")
        self.git("config", "core.hooksPath", ".claude/githooks")

    def git(self, *args, env=None):
        return subprocess.run(["git", *args], cwd=self.repo, check=True, text=True, capture_output=True,
                              env={**self.env, **(env or {})}).stdout

    def try_git(self, *args, **env):
        return subprocess.run(["git", *args], cwd=self.repo, text=True, capture_output=True,
                              env={**self.env, **env})

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def review(self, **env):
        return subprocess.run([sys.executable, str(GATE), "review"], cwd=self.repo, text=True, capture_output=True,
                              env={**self.env, **env}).returncode

    def hook(self, env=None, **event):
        event = {"session_id": "s", "cwd": str(self.repo), **event}
        result = subprocess.run([sys.executable, str(GATE)], input=json.dumps(event), text=True, capture_output=True,
                                env={**self.env, **(env or {})}, check=True)
        return json.loads(result.stdout) if result.stdout else None

    def bash(self, command, **env):
        output = self.hook(env, hook_event_name="PreToolUse", tool_name="Bash", tool_input={"command": command})
        return output["hookSpecificOutput"]["permissionDecisionReason"] if output else None

    def stage_change(self, text="2\n", name="a.py"):
        self.write(name, text)
        self.git("add", ".")

    def test_commit_blocked_until_codex_ok(self):
        self.stage_change()
        self.assertEqual(self.try_git("commit", "-qm", "x").returncode, 1)
        self.assertEqual(self.review(), 0)
        self.assertEqual(self.try_git("commit", "-qm", "x").returncode, 0)

    def test_code_changed_after_approval_needs_new_review(self):
        self.stage_change()
        self.review()
        self.stage_change("3\n")
        self.assertEqual(self.try_git("commit", "-qm", "x").returncode, 1)

    def test_every_commit_form_checks_what_is_really_committed(self):
        self.stage_change()
        self.review()
        self.write("a.py", "unreviewed\n")
        for args in (["commit", "-qam", "x"], ["commit", "-q", "a.py", "-m", "x"], ["commit", "-q", "--only", "a.py", "-m", "x"]):
            self.assertEqual(self.try_git(*args).returncode, 1, args)

    def test_codex_issues_or_failure_do_not_approve(self):
        self.stage_change()
        self.assertEqual(self.review(FAKE_VERDICT="ISSUES"), 1)
        self.assertEqual(self.review(FAKE_CODEX_FAIL="1"), 2)
        self.assertEqual(self.try_git("commit", "-qm", "x").returncode, 1)

    def test_docs_only_change_is_exempt_and_keeps_approval(self):
        self.stage_change("문서\n", "_docs/log.md")
        self.assertEqual(self.try_git("commit", "-qm", "docs").returncode, 0)
        self.stage_change("2\n")
        self.review()
        self.stage_change("문서 추가\n", "suvisdev/_docs/log.md")
        self.assertEqual(self.try_git("commit", "-qm", "x").returncode, 0)

    def test_user_commit_and_push_are_not_gated(self):
        self.stage_change()
        env = {**self.env}
        del env["CLAUDECODE"]
        for args in (["commit", "-qm", "x"], ["push", "-q", "origin", "HEAD:main"]):
            result = subprocess.run(["git", *args], cwd=self.repo, text=True, capture_output=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_pre_commit_hook_still_runs(self):
        legacy = self.repo / ".git/hooks/pre-commit"
        legacy.write_text('#!/bin/sh\necho ran > "$FAKE_GH_LOG.legacy"\n')
        legacy.chmod(0o755)
        self.stage_change("문서\n", "_docs/log.md")
        self.assertEqual(self.try_git("commit", "-qm", "x").returncode, 0)
        self.assertTrue((self.root / "gh.log.legacy").exists())

    def test_push_to_main_is_blocked_in_every_form(self):
        self.write("b.md", "x\n")
        self.git("add", ".")
        self.git("commit", "-qm", "b", "--no-verify")
        self.assertEqual(self.try_git("push", "origin", "feat:main").returncode, 1)
        self.assertEqual(self.try_git("push", "origin", "HEAD:refs/heads/main").returncode, 1)
        self.git("update-ref", "refs/heads/main", "HEAD")
        self.assertEqual(self.try_git("push", "--all", "origin").returncode, 1)
        self.assertEqual(self.try_git("push", "-q", "origin", "feat").returncode, 0)

    def test_commands_that_disable_git_hooks_are_denied(self):
        for command in ["git commit --no-verify -m x", "git commit -nm x", "git -c core.hooksPath=/dev/null commit -m x",
                        "git config core.hooksPath x", "git push --no-verify origin feat", " git commit -n -m x",
                        'bash -c "git commit --no-verify -m x"']:
            self.assertIn("훅", self.bash(command), command)

    def test_reading_hook_settings_is_allowed(self):
        for command in ["git config --get core.hooksPath", "rg hooksPath .claude", "git log --grep hooksPath",
                        'git commit -m "core.hooksPath 설정 추가"', "grep -- --no-verify README.md"]:
            self.assertIsNone(self.bash(command), command)

    def test_message_text_is_not_read_as_a_command(self):
        for command in ['git commit -m "fix --no-verify note; gh pr merge 7"', "echo 'gh pr merge 7'", "git status",
                        "python3 - <<'EOF'\ngh pr merge 7\ngit commit --no-verify\nEOF\necho done",
                        """python3 -c "print('it's')" """]:
            self.assertIsNone(self.bash(command), command)

    def committed_pr(self, name="a.py"):
        self.stage_change("2\n", name)
        self.review()
        self.git("commit", "-qm", "x")
        self.git("push", "-q", "origin", "HEAD:refs/pull/7/head")

    def pinned_merge(self, command, **env):
        head = self.git("rev-parse", "HEAD").strip()
        return self.bash(f"{command} --match-head-commit {head}", **env)

    def test_merge_must_be_pinned_to_the_checked_commit(self):
        self.committed_pr()
        self.assertIn("고정", self.bash("gh pr merge 7 --merge"))
        self.assertIn("고정", self.bash("gh pr merge 7 --merge --match-head-commit deadbeef"))
        head = self.git("rev-parse", "HEAD").strip()
        self.assertIsNone(self.bash(f"gh pr merge 7 --merge --match-head-commit={head}"))

    def test_review_records_the_snapshot_it_reviewed(self):
        self.stage_change()
        self.assertEqual(self.review(), 0)
        self.assertEqual(self.try_git("commit", "-qm", "x").returncode, 0)

    def test_merge_requires_approved_head(self):
        self.committed_pr()
        self.assertIsNone(self.pinned_merge("gh pr merge 7 --merge"))
        self.stage_change("unreviewed\n")
        self.git("commit", "-qm", "y", "--no-verify")
        self.git("push", "-q", "origin", "HEAD:refs/pull/7/head")
        self.assertIn("승인", self.bash("gh pr merge 7 --merge"))

    def test_merge_is_found_however_it_is_written(self):
        self.stage_change()
        self.git("commit", "-qm", "unreviewed", "--no-verify")
        self.git("push", "-q", "origin", "HEAD:refs/pull/7/head")
        for command in ["gh pr merge 7", "  gh pr merge 7", "A=1 gh pr merge 7", "env A=1 gh pr merge 7", 'bash -c "gh pr merge 7"',
                        f"cd {self.repo} && gh pr merge 7"]:
            self.assertIsNotNone(self.bash(command), command)

    def test_merge_option_with_quoted_operator_works(self):
        self.committed_pr()
        self.assertIsNone(self.pinned_merge('gh pr merge 7 --merge --body "검증 완료; 배포 가능 | 끝"'))

    def test_chained_merge_is_denied(self):
        self.committed_pr()
        self.assertIn("단독", self.bash("git push origin feat && gh pr merge 7"))
        self.assertIn("단독", self.bash("echo a; gh pr merge 7 && gh pr merge 8"))
        self.assertIn("단독", self.bash("gh pr merge 7 --merge && gh pr merge 8 --merge"))
        self.assertIn("단독", self.bash("gh pr merge 7 --merge; echo done"))

    def test_merge_checks_the_pr_the_command_names(self):
        self.committed_pr()
        for selector in ["https://github.com/o/r/pull/9", "other-branch"]:
            self.bash(f"gh pr merge {selector} --merge")
            self.assertEqual((self.root / "gh.log").read_text().splitlines()[-1], selector)
        self.bash('gh pr merge --subject "12 fixes" --merge')
        self.assertEqual((self.root / "gh.log").read_text().splitlines()[-1], "--json")
        self.assertIn("저장소", self.bash("gh pr merge 7 -R other/repo"))

    def test_merge_blocked_on_failed_or_pending_ci(self):
        self.committed_pr()
        self.assertIn("backend", self.bash("gh pr merge 7", FAKE_BUCKET="fail"))
        self.assertIn("backend", self.bash("gh pr merge 7", FAKE_BUCKET="pending"))

    def test_merge_allowed_when_no_checks_but_blocked_when_ci_unknown(self):
        self.committed_pr()
        self.assertIsNone(self.pinned_merge("gh pr merge 7", FAKE_NO_CHECKS="1"))
        self.assertIn("CI 상태", self.bash("gh pr merge 7", FAKE_CHECKS_DOWN="1"))

    def test_merge_blocked_when_ci_target_has_no_checks_yet(self):
        self.committed_pr("suvisdev/apps/x.py")
        self.assertIn("검사가 아직 없다", self.bash("gh pr merge 7", FAKE_NO_CHECKS="1"))

    def test_merge_waits_for_every_expected_workflow(self):
        self.write("suvis/app/x.tsx", "1\n")
        self.committed_pr("suvisdev/apps/x.py")
        self.assertIn("frontend-ci", self.bash("gh pr merge 7"))

    def test_merge_passes_when_expected_workflow_finished(self):
        self.committed_pr("suvisdev/apps/x.py")
        self.assertIsNone(self.pinned_merge("gh pr merge 7"))

    def test_markdown_under_frontend_still_expects_its_workflow(self):
        self.committed_pr("suvis/README.md")
        self.assertIn("frontend-ci", self.bash("gh pr merge 7"))

    def test_paths_outside_ci_filter_need_no_checks(self):
        self.committed_pr("suvisdev/README.md")
        self.assertIsNone(self.pinned_merge("gh pr merge 7", FAKE_NO_CHECKS="1"))

    def test_workflow_outside_ci_filter_needs_no_checks(self):
        self.committed_pr(".github/workflows/gildle-data-sync.yml")
        self.assertIsNone(self.pinned_merge("gh pr merge 7", FAKE_NO_CHECKS="1"))

    def test_workflow_inside_ci_filter_needs_checks(self):
        self.committed_pr(".github/workflows/backend-ci.yml")
        self.assertIn("검사가 아직 없다", self.bash("gh pr merge 7", FAKE_NO_CHECKS="1"))

    def test_merge_held_for_migration_until_user_confirms(self):
        self.committed_pr("suvisdev/alembic/versions/001_x.py")
        self.assertIn("선행 작업", self.bash("gh pr merge 7"))
        subprocess.run([sys.executable, str(GATE), "confirm-prereq", "7"], cwd=self.repo, env=self.env, check=True)
        self.assertIsNone(self.pinned_merge("gh pr merge 7"))

    def test_merge_held_for_new_env_key(self):
        self.committed_pr("suvisdev/.env.example")
        self.assertIn("선행 작업", self.bash("gh pr merge 7"))

    def test_merge_fails_closed_outside_repo(self):
        output = self.hook(None, cwd=str(self.root), hook_event_name="PreToolUse", tool_name="Bash",
                           tool_input={"command": "gh pr merge 7"})
        self.assertIn("판정 실패", output["hookSpecificOutput"]["permissionDecisionReason"])

    def edit(self, name="a.py"):
        self.hook(hook_event_name="PreToolUse", tool_name="Edit", tool_input={"file_path": str(self.repo / name)})

    def stop(self, active=False):
        return self.hook(hook_event_name="Stop", stop_hook_active=active)

    def test_stop_sends_session_edits_back_to_finish(self):
        self.edit()
        self.write("a.py", "2\n")
        output = self.stop()
        self.assertEqual(output["decision"], "block")
        self.assertIn("a.py", output["reason"])

    def test_stop_does_not_loop(self):
        self.edit()
        self.write("a.py", "2\n")
        self.assertIsNone(self.stop(active=True))

    def test_stop_ignores_sessions_without_edits_and_other_dirty_files(self):
        self.write("unrelated.yaml", "x\n")
        self.assertIsNone(self.stop())

    def test_stop_blocks_committed_but_unmerged_then_passes_after_merge(self):
        self.edit()
        self.stage_change()
        self.review()
        self.git("commit", "-qm", "x")
        self.assertEqual(self.stop()["decision"], "block")
        env = {**self.env}
        del env["CLAUDECODE"]
        subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=self.repo, check=True, env=env)
        self.git("fetch", "-q", "origin")
        self.assertIsNone(self.stop())

    def test_stop_ignores_files_outside_git(self):
        outside = self.root / "scratch.py"
        outside.write_text("x")
        self.hook(hook_event_name="PreToolUse", tool_name="Write", tool_input={"file_path": str(outside)})
        self.assertIsNone(self.stop())


if __name__ == "__main__":
    unittest.main()
