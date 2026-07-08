#!/usr/bin/env python3
"""Tests for deckcode decode/encode."""
import unittest

from deckcode import decode, encode

# Real deck code captured from a live export (nmp-rewind).
KNOWN_CODE = (
    "AUGVK3TUNF2GYZLEEBCGKY3LBNRW63TTORZHKY3UMVSBSAHRAAAAQHIIAIBQD2ABA"
    "44AQBIDAIBQEAYDAMCQGEQDAEBQSAY"
)


class TestDeckcode(unittest.TestCase):

    def test_round_trip(self):
        deck = decode(KNOWN_CODE)
        divers = deck["divers"]
        reproduced = encode(
            deck["name"], deck["format"],
            divers[0] if len(divers) > 0 else 0,
            divers[1] if len(divers) > 1 else 0,
            deck["cards"],
        )
        self.assertEqual(reproduced, KNOWN_CODE)

    def test_known_values(self):
        deck = decode(KNOWN_CODE)
        self.assertEqual(deck["format"], "constructed")
        self.assertEqual(len(deck["cards"]), 16)
        self.assertEqual(sum(deck["cards"].values()), 40)
        self.assertTrue(all(v in (2, 3) for v in deck["cards"].values()))
        self.assertTrue(all(d != 0 for d in deck["divers"]))

    def test_encode_decode_synthetic(self):
        cards = {10: 2, 20: 2, 30: 1}
        code = encode("My Deck", "constructed", 10, 20, cards)
        deck = decode(code)
        self.assertEqual(deck["name"], "My Deck")
        self.assertEqual(deck["format"], "constructed")
        self.assertEqual(deck["divers"], [10, 20])
        self.assertEqual(deck["cards"], cards)

    def test_single_diver(self):
        code = encode("Test", "constructed", 42, 0, {5: 2})
        deck = decode(code)
        self.assertEqual(deck["divers"], [42])

    def test_no_divers(self):
        code = encode("Test", "constructed", 0, 0, {5: 2})
        deck = decode(code)
        self.assertEqual(deck["divers"], [])

    def test_unsupported_version_raises(self):
        import base64
        # Hand-craft a v4 buffer (just the version byte matters for this check)
        buf = bytes([4]) + b"\x00" * 10
        code = base64.b32encode(buf).decode().rstrip("=")
        with self.assertRaises(ValueError):
            decode(code)


if __name__ == "__main__":
    unittest.main()
