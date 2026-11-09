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
        self.assertIn("git show origin/main:CLAUDE.md", message)

    def test_missing_harness_file_is_reported(self):
        (self.repo / ".claude/scripts/gate.py").unlink()
        self.assertIn(".claude/scripts/gate.py", self.run_hook())

    def test_no_origin_main_fails_quietly(self):
        sh(self.repo, "git", "update-ref", "-d", "refs/remotes/origin/main")
        self.assertEqual(self.run_hook(), "")


if __name__ == "__main__":
    unittest.main()
