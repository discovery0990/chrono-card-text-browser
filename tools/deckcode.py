#!/usr/bin/env python3
"""Chrono CCG deck code encoder/decoder (client export format, version 5).

Format verified against the C# reference implementation supplied by the
Chrono devs. Only version 5 is supported; other versions raise ValueError.

    u8      format version (must be 5)
    string  deck name        (varint length + utf-8 bytes)
    string  format           (e.g. "constructed")
    u16le   diver 1 id       (0 = empty slot)
    u16le   diver 2 id       (0 = empty slot)
    section 1-of cards:  varint n, then n varint deltas (ascending card ids,
                         base 0, delta from previous id)
    section 2-of cards:  same shape
    section other:       varint n, then n (varint delta, varint count) pairs
                         (counts ≥ 3)

The whole buffer is base32 (RFC 4648, A-Z2-7, padding stripped).

decode() returns {"divers": [...]} with zero-valued slots omitted.

Usage:
    python3 deckcode.py CODE [--cards tools/cards.json]

With --cards, ids are joined to names/costs and output is cost-sorted
(feeds the deck-sheet pipeline). The loader is schema-tolerant: it accepts
a list of card objects or an id-keyed dict, and looks for id/name/cost
under a few likely field names.
"""

import argparse
import base64
import json
import sys


FORMAT_VERSION = 5

# ---------- primitives ----------

def _varint_encode(n: int) -> bytes:
    if n < 0:
        raise ValueError(f"varint requires a non-negative integer, got {n}")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def u8(self) -> int:
        v = self.data[self.pos]
        self.pos += 1
        return v

    def u16le(self) -> int:
        v = self.data[self.pos] | (self.data[self.pos + 1] << 8)
        self.pos += 2
        return v

    def varint(self) -> int:
        shift = result = 0
        while True:
            b = self.data[self.pos]
            self.pos += 1
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                return result
            shift += 7

    def string(self) -> str:
        n = self.varint()
        s = self.data[self.pos:self.pos + n].decode("utf-8")
        self.pos += n
        return s


# ---------- decode / encode ----------

def decode(code: str) -> dict:
    try:
        padded = code + "=" * ((8 - len(code) % 8) % 8)
        r = _Reader(base64.b32decode(padded))

        version = r.u8()
        if version != FORMAT_VERSION:
            raise ValueError(f"unsupported format version {version} "
                             f"(only version 5 is implemented)")

        name = r.string()
        fmt = r.string()
        diver_a = r.u16le()
        diver_b = r.u16le()

        cards: dict[int, int] = {}
        for implied_count in (1, 2):
            n = r.varint()
            cid = 0
            for _ in range(n):
                cid += r.varint()
                cards[cid] = cards.get(cid, 0) + implied_count
        n = r.varint()
        cid = 0
        for _ in range(n):
            cid += r.varint()
            cards[cid] = cards.get(cid, 0) + r.varint()

        if r.pos != len(r.data):
            print(f"warning: {len(r.data) - r.pos} trailing bytes not consumed",
                  file=sys.stderr)

        return {
            "version": version,
            "name": name,
            "format": fmt,
            "divers": [d for d in (diver_a, diver_b) if d != 0],
            "cards": cards,
        }
    except Exception as exc:
        raise ValueError(f"invalid deck code: {exc}") from exc


def encode(name: str, fmt: str, diver_a: int, diver_b: int,
           cards: dict[int, int]) -> str:
    buf = bytearray([FORMAT_VERSION])
    for s in (name, fmt):
        e = s.encode("utf-8")
        buf += _varint_encode(len(e)) + e
    for d in (diver_a, diver_b):
        buf += bytes([d & 0xFF, (d >> 8) & 0xFF])

    for target in (1, 2):
        ids = sorted(k for k, v in cards.items() if v == target)
        buf += _varint_encode(len(ids))
        prev = 0
        for cid in ids:
            buf += _varint_encode(cid - prev)
            prev = cid
    rest = sorted((k, v) for k, v in cards.items() if v not in (1, 2))
    buf += _varint_encode(len(rest))
    prev = 0
    for cid, cnt in rest:
        buf += _varint_encode(cid - prev) + _varint_encode(cnt)
        prev = cid

    return base64.b32encode(bytes(buf)).decode().rstrip("=")


# ---------- card data join (schema-tolerant) ----------

_ID_KEYS = ("id", "cardId", "card_id")
_NAME_KEYS = ("name", "cardName", "title")
_COST_KEYS = ("cost", "manaCost", "energy", "price")


def _pick(obj: dict, keys) -> object:
    for k in keys:
        if k in obj:
            return obj[k]
    return None


def load_cards(path: str) -> dict[int, dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict) and "cards" in data:
        data = data["cards"]

    index: dict[int, dict] = {}
    if isinstance(data, dict):
        items = []
        for k, v in data.items():
            if isinstance(v, dict):
                v = dict(v)
                v.setdefault("id", k)
                items.append(v)
        data = items
    for obj in data:
        if not isinstance(obj, dict):
            continue
        cid = _pick(obj, _ID_KEYS)
        try:
            cid = int(cid)
        except (TypeError, ValueError):
            continue
        index[cid] = {
            "name": _pick(obj, _NAME_KEYS) or f"card {cid}",
            "cost": _pick(obj, _COST_KEYS),
        }
    return index


# ---------- CLI ----------

def main() -> None:
    p = argparse.ArgumentParser(description="Decode a Chrono CCG deck code")
    p.add_argument("code")
    p.add_argument("--cards", help="path to card database JSON "
                                   "(list of objects or id-keyed dict)")
    p.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON instead of text")
    args = p.parse_args()

    try:
        deck = decode(args.code)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")

    index = load_cards(args.cards) if args.cards else {}

    def describe(cid: int) -> tuple:
        info = index.get(cid)
        if info:
            cost = info["cost"]
            return (cost if cost is not None else 999, info["name"])
        return (999, f"#{cid}")

    if args.json:
        if index:
            deck["cards_resolved"] = [
                {"id": cid, "count": cnt,
                 "name": index.get(cid, {}).get("name"),
                 "cost": index.get(cid, {}).get("cost")}
                for cid, cnt in sorted(deck["cards"].items(),
                                       key=lambda kv: describe(kv[0]))
            ]
        print(json.dumps(deck, indent=2))
        return

    print(f"{deck['name']}  [{deck['format']}]")
    print(f"divers: {deck['divers'][0]}, {deck['divers'][1]}"
          + (f"  ({index[deck['divers'][0]]['name']}, "
             f"{index[deck['divers'][1]]['name']})"
             if all(d in index for d in deck["divers"]) else ""))
    total = sum(deck["cards"].values())
    print(f"{total} cards, {len(deck['cards'])} unique")
    print()
    for cid, cnt in sorted(deck["cards"].items(),
                           key=lambda kv: describe(kv[0])):
        cost, name = describe(cid)
        cost_s = "?" if cost == 999 else str(cost)
        print(f"  {cnt}x  [{cost_s}]  {name}")


if __name__ == "__main__":
    main()
