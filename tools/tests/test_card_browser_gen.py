#!/usr/bin/env python3
"""Tests for card_browser_gen.py — golden file comparison and key invariants.

To regenerate golden files after an intentional rendering change:
    python3 card_browser_gen.py --input tests/fixture.json --out tests/golden
    # review git diff tests/golden/ before committing
"""
import os
import subprocess
import sys
import tempfile
import unittest

TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT     = os.path.join(TOOLS_ROOT, "card_browser_gen.py")
FIXTURE    = os.path.join(TOOLS_ROOT, "tests", "fixture.json")
GOLDEN     = os.path.join(TOOLS_ROOT, "tests", "golden")


def _collect_files(base: str) -> dict[str, str]:
    result = {}
    for root, _dirs, files in os.walk(base):
        for f in files:
            abs_path = os.path.join(root, f)
            with open(abs_path) as fh:
                result[os.path.relpath(abs_path, base)] = fh.read()
    return result


class TestCardBrowserGen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.out_dir = os.path.join(cls._tmpdir.name, "output")
        result = subprocess.run(
            [sys.executable, SCRIPT, "--input", FIXTURE, "--out", cls.out_dir],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"generator failed:\n{result.stderr}")

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_golden_files_match(self):
        golden = _collect_files(GOLDEN)
        actual = _collect_files(self.out_dir)
        for path, expected in sorted(golden.items()):
            with self.subTest(path=path):
                self.assertIn(path, actual, f"missing file: {path}")
                self.assertEqual(actual[path], expected)
        extra = sorted(set(actual) - set(golden))
        self.assertEqual(extra, [], f"unexpected extra files: {extra}")

    def test_immortalize_lines_unwrapped(self):
        cases = [
            (
                "lifeblood/06-glasswinged-monarch.md",
                "Evasive. Enter or Core Strike: Shift to Abundant Growth. Immortalize: I've seen you Shift twice.",
            ),
            (
                "lifeblood/03-panicked-refugee.md",
                "Immortalize: Round End: I do not see an allied Wolf in play.",
            ),
        ]
        for rel_path, expected_line in cases:
            with self.subTest(file=rel_path):
                with open(os.path.join(self.out_dir, rel_path)) as fh:
                    content = fh.read()
                self.assertIn(expected_line, content.splitlines())


if __name__ == "__main__":
    unittest.main()
