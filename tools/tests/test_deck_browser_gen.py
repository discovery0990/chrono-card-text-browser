#!/usr/bin/env python3
"""Smoke tests for deck_browser_gen.py.

Uses fixture.json as the card database. A test deck is constructed via
encode() so the test has no dependency on any live API or saved deck code.

Fixture card IDs used:
  Agents (playable):  19 Panicked Refugee, 51 Peaceful Synthesizer,
                      154 Enlightened Refugee
  Action:             327 Magmatic Teachings
  Divers (not in deck cards list): 33 Hungry Tyrannosaur, 21 Sleepy Druid
  Immortalized (must not get own file): 34 Wreck-o Rex, 22 Xae Dreamstrider
"""
import os
import subprocess
import sys
import tempfile
import unittest

from deckcode import encode

TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT     = os.path.join(TOOLS_ROOT, "deck_browser_gen.py")
FIXTURE    = os.path.join(TOOLS_ROOT, "tests", "fixture.json")

DECK_NAME = "Test Deck"
DECK_CODE = encode(
    name=DECK_NAME,
    fmt="constructed",
    diver_a=33,   # Hungry Tyrannosaur
    diver_b=21,   # Sleepy Druid
    cards={19: 2, 51: 2, 154: 2, 327: 2},
)


class TestDeckBrowserGen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        result = subprocess.run(
            [sys.executable, SCRIPT, DECK_CODE, DECK_NAME,
             "--cards", FIXTURE, "--out", cls._tmpdir.name],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"deck_browser_gen failed:\n{result.stderr}")
        cls.deck_dir = os.path.join(cls._tmpdir.name, "test-deck")

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_expected_files_present(self):
        files = set(os.listdir(self.deck_dir))
        expected = {
            "!index.md",
            "03-panicked-refugee.md",
            "01-peaceful-synthesizer.md",
            "03-enlightened-refugee.md",
            "03-magmatic-teachings.md",
            # diver cards — not in deck["cards"] but must still be rendered
            "08-hungry-tyrannosaur.md",
            "03-sleepy-druid.md",
        }
        for name in expected:
            with self.subTest(file=name):
                self.assertIn(name, files)

    def test_immortalized_agents_absent(self):
        files = os.listdir(self.deck_dir)
        for slug in ["wreck-o-rex", "xae"]:
            matches = [f for f in files if slug in f]
            self.assertEqual(matches, [], f"IMMORTALIZED_AGENT got a file: {matches}")

    def test_index_content(self):
        with open(os.path.join(self.deck_dir, "!index.md")) as fh:
            content = fh.read()
        self.assertIn(DECK_NAME, content)
        self.assertIn("constructed", content)
        self.assertIn("Hungry Tyrannosaur", content)
        self.assertIn("Sleepy Druid", content)
        self.assertIn("10 cards", content)
        self.assertIn("6 unique", content)
        self.assertIn(DECK_CODE, content)

    def test_index_sorts_first(self):
        files = sorted(os.listdir(self.deck_dir))
        self.assertEqual(files[0], "!index.md")


if __name__ == "__main__":
    unittest.main()
