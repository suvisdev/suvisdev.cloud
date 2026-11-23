"""실행: python3 -m unittest discover -s .claude/scripts -p 'test_harness_drift.py'"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "harness_drift.py"


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class DriftTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        sh(self.repo, "git", "init", "-q", "-b", "work")
        sh(self.repo, "git", "config", "user.email", "t@t")
        sh(self.repo, "git", "config", "user.name", "t")
        (self.repo / ".claude/scripts").mkdir(parents=True)
        (self.repo / "CLAUDE.md").write_text("new rules\n")
        (self.repo / ".claude/scripts/gate.py").write_text("v2\n")
        (self.repo / "app.py").write_text("x\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "main")
        # origin/main 역할: 원격 없이 같은 이름의 원격 추적 ref를 만든다
        sh(self.repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")

    def run_hook(self) -> str:
        out = subprocess.run([sys.executable, str(SCRIPT)], cwd=self.repo, text=True,
                             capture_output=True, check=True).stdout
        return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""

    def test_same_as_main_says_nothing(self):
        (self.repo / "app.py").write_text("other branch work\n")  # 하네스 밖 변경은 무시
        self.assertEqual(self.run_hook(), "")

    def test_old_claude_md_and_stale_untracked_script_are_reported(self):
        (self.repo / "CLAUDE.md").write_text("old rules\n")
        (self.repo / ".claude/scripts/gate.py").write_text("v1\n")
        message = self.run_hook()
        self.assertIn("CLAUDE.md", message)
        self.assertIn(".claude/scripts/gate.py", message)
        self.assertIn("git show origin/main:<파일>", message)
        self.assertIn("이 폴더의 _docs/SPEC.md·STATE.md", message)  # 옛 CLAUDE.md면 @가 안 돌았을 수 있다

    def test_missing_harness_file_is_reported(self):
        (self.repo / ".claude/scripts/gate.py").unlink()
        self.assertIn(".claude/scripts/gate.py", self.run_hook())

    def test_state_file_written_on_this_branch_is_not_reported(self):
        (self.repo / "_docs").mkdir()
        (self.repo / "_docs/STATE.md").write_text("base\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "state")
        sh(self.repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
        (self.repo / "_docs/STATE.md").write_text("이 브랜치에서 갱신\n")
        self.assertEqual(self.run_hook(), "")

    def test_stale_state_file_is_reported(self):
        (self.repo / "_docs").mkdir()
        (self.repo / "_docs/STATE.md").write_text("old\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "state")
        sh(self.repo, "git", "checkout", "-q", "-b", "main-ahead")
        (self.repo / "_docs/STATE.md").write_text("new\n")
        sh(self.repo, "git", "commit", "-qam", "newer")
        sh(self.repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
        sh(self.repo, "git", "checkout", "-q", "work")
        self.assertIn("_docs/STATE.md", self.run_hook())

    def test_state_changed_on_both_sides_is_reported(self):
        (self.repo / "_docs").mkdir()
        (self.repo / "_docs/STATE.md").write_text("base\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "state")
        sh(self.repo, "git", "checkout", "-q", "-b", "main-ahead")
        (self.repo / "_docs/STATE.md").write_text("main에서 갱신\n")
        sh(self.repo, "git", "commit", "-qam", "newer")
        sh(self.repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
        sh(self.repo, "git", "checkout", "-q", "work")
        (self.repo / "_docs/STATE.md").write_text("이 브랜치에서 갱신\n")
        self.assertIn("_docs/STATE.md", self.run_hook())

    def test_blank_state_file_is_reported(self):
        (self.repo / "_docs").mkdir()
        (self.repo / "_docs/STATE.md").write_text("base\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "state")
        sh(self.repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
        (self.repo / "_docs/STATE.md").write_text("\n")
        self.assertIn("_docs/STATE.md", self.run_hook())
        (self.repo / "_docs/STATE.md").write_bytes(b"\xff\xfe broken\n")
        self.assertIn("_docs/STATE.md", self.run_hook())

    def test_state_symlink_is_reported(self):
        (self.repo / "_docs").mkdir()
        (self.repo / "_docs/STATE.md").write_text("base\n")
        (self.repo / "_docs/OLD.md").write_text("old summary\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "state")
        sh(self.repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
        (self.repo / "_docs/STATE.md").unlink()
        (self.repo / "_docs/STATE.md").symlink_to("OLD.md")
        self.assertIn("_docs/STATE.md", self.run_hook())
        (self.repo / "_docs/OLD.md").write_text("base\n")  # 링크 대상 내용이 main과 같아도
        self.assertIn("_docs/STATE.md", self.run_hook())

    def test_unrelated_history_still_reports_old_claude_md(self):
        sh(self.repo, "git", "checkout", "-q", "--orphan", "shallow")
        (self.repo / "CLAUDE.md").write_text("old rules\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "no common base")
        self.assertIn("CLAUDE.md", self.run_hook())

    def test_stale_state_is_shown_even_with_many_drifted_files(self):
        (self.repo / "_docs").mkdir()
        (self.repo / "_docs/STATE.md").write_text("old\n")
        for n in range(9):
            (self.repo / f".claude/scripts/s{n}.py").write_text("v1\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "old")
        sh(self.repo, "git", "checkout", "-q", "-b", "main-ahead")
        (self.repo / "_docs/STATE.md").write_text("new\n")
        for n in range(9):
            (self.repo / f".claude/scripts/s{n}.py").write_text("v2\n")
        sh(self.repo, "git", "commit", "-qam", "newer")
        sh(self.repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
        sh(self.repo, "git", "checkout", "-q", "work")
        (self.repo / "CLAUDE.md").write_text("old rules\n")
        message = self.run_hook()
        self.assertIn("_docs/STATE.md", message)
        self.assertIn("CLAUDE.md,", message)

    def test_no_origin_main_fails_quietly(self):
        sh(self.repo, "git", "update-ref", "-d", "refs/remotes/origin/main")
        self.assertEqual(self.run_hook(), "")


if __name__ == "__main__":
    unittest.main()
