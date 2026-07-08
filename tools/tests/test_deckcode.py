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
        reproduced = encode(
            deck["name"], deck["format"],
            deck["divers"][0], deck["divers"][1],
            deck["cards"],
        )
        self.assertEqual(reproduced, KNOWN_CODE)

    def test_known_values(self):
        deck = decode(KNOWN_CODE)
        self.assertEqual(deck["format"], "constructed")
        self.assertEqual(len(deck["cards"]), 16)
        self.assertEqual(sum(deck["cards"].values()), 40)
        self.assertTrue(all(v in (2, 3) for v in deck["cards"].values()))

    def test_encode_decode_synthetic(self):
        cards = {10: 2, 20: 2, 30: 1}
        code = encode("My Deck", "constructed", 10, 20, cards)
        deck = decode(code)
        self.assertEqual(deck["name"], "My Deck")
        self.assertEqual(deck["format"], "constructed")
        self.assertEqual(deck["divers"], [10, 20])
        self.assertEqual(deck["cards"], cards)


if __name__ == "__main__":
    unittest.main()
