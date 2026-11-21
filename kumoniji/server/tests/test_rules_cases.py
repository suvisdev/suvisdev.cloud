import json
from pathlib import Path

import pytest

from kumoniji import rules

CASES = json.loads((Path(rules.__file__).parent / "cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case(case):
    assert rules.run_case(case) == case["expect"]


def test_case_count():
    assert len(CASES) == 91


def test_full_count():
    got = rules.full_count()
    assert (got["포카드"], got["스트레이트플러시"], got["같은모양홀짝"]) == (
        624,
        36,
        20,
    )
