from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_APPS = _ROOT / "apps"
for _p in (_ROOT, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_CLI_PATH = _ROOT / "scripts" / "assign_collection_cli.py"
_spec = importlib.util.spec_from_file_location("assign_collection_cli", _CLI_PATH)
assert _spec is not None and _spec.loader is not None
assign_collection_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assign_collection_cli)


class ParseArgsTests(unittest.TestCase):
    def test_assign_basic(self) -> None:
        args = assign_collection_cli._parse_args(
            ["--slug", "nolan-world", "--movie-ids", "99,106,85"]
        )
        self.assertEqual(args.slug, "nolan-world")
        self.assertEqual(args.movie_ids, [99, 106, 85])
        self.assertFalse(args.unassign)
        self.assertFalse(args.dry_run)

    def test_unassign_dry_run(self) -> None:
        args = assign_collection_cli._parse_args(
            ["--slug", "sf-classics", "--movie-ids", "1,2", "--unassign", "--dry-run"]
        )
        self.assertTrue(args.unassign)
        self.assertTrue(args.dry_run)

    def test_movie_ids_non_integer_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            assign_collection_cli._parse_args(
                ["--slug", "x", "--movie-ids", "1,abc,3"]
            )

    def test_movie_ids_empty_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            assign_collection_cli._parse_args(["--slug", "x", "--movie-ids", ""])

    def test_movie_ids_whitespace_tolerated(self) -> None:
        args = assign_collection_cli._parse_args(
            ["--slug", "x", "--movie-ids", " 1 , 2 , 3 "]
        )
        self.assertEqual(args.movie_ids, [1, 2, 3])

    def test_parse_movie_ids_helper_direct(self) -> None:
        # 커버리지 — helper 시그니처 안정성.
        self.assertEqual(assign_collection_cli._parse_movie_ids("10,20"), [10, 20])
        with self.assertRaises(argparse.ArgumentTypeError):
            assign_collection_cli._parse_movie_ids("")


if __name__ == "__main__":
    unittest.main()
