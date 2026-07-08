#!/usr/bin/env python3
"""
Generate a browsable deck directory from a Chrono CCG deck code.

Usage:
    python3 deck_browser_gen.py CODE [NAME] [--cards FILE] [--out DIR]

    CODE           deck code (from in-game export)
    NAME           deck name (default: name embedded in code)
    --cards FILE   path to cards.json (default: ./tools/cards.json)
    --out DIR      output root (default: ./decks)

Output:
    decks/
      <deck-slug>/
        !index.md        deck summary, card counts, reimport code
        NN-slug.md       one file per unique card (same format as cards/)

Re-running regenerates the deck directory from scratch.
"""
import argparse
import json
import os
import sys

from render import TYPE_CONFIG, build_immo_map, render_card, slugify
from deckcode import decode


def _render_index(deck_name: str, deck_fmt: str, deck_code: str,
                  diver_names: list[str], cards_resolved: list[dict]) -> str:
    total = sum(c["count"] for c in cards_resolved) + len(diver_names)
    unique = len(cards_resolved) + len(diver_names)
    lines = [
        f"{deck_name}  [{deck_fmt}]",
        "---",
        f"Divers: {', '.join(diver_names)}",
        f"{total} cards  ({unique} unique)",
        "",
    ]
    for c in cards_resolved:
        cost_s = "?" if c["cost"] is None else str(c["cost"])
        lines.append(f"{c['count']}x  [{cost_s}]  {c['name']}")
    lines += ["", "---", "", deck_code, ""]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate a browsable deck directory from a Chrono CCG deck code"
    )
    p.add_argument("code", metavar="CODE", help="deck code string")
    p.add_argument("name", metavar="NAME", nargs="?", default=None,
                   help="deck name (default: name embedded in code)")
    p.add_argument("--cards", metavar="FILE", default="tools/cards.json",
                   help="path to cards.json (default: ./tools/cards.json)")
    p.add_argument("--out", metavar="DIR", default="./decks",
                   help="output root (default: ./decks)")
    args = p.parse_args()

    try:
        deck = decode(args.code)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")
    deck_name = args.name or deck["name"]
    deck_fmt = deck["format"]
    deck_card_ids: dict[int, int] = deck["cards"]

    with open(args.cards) as f:
        raw_cards: list[dict] = json.load(f)

    by_id: dict[int, dict] = {c["id"]: c for c in raw_cards}
    base_to_immo = build_immo_map(by_id)

    def sort_key(cid: int) -> tuple:
        card = by_id.get(cid)
        return (card.get("cost") or 0, card.get("name") or "") if card else (999, f"#{cid}")

    sorted_ids = sorted(deck_card_ids, key=sort_key)

    cards_resolved: list[dict] = []
    for cid in sorted_ids:
        card = by_id.get(cid)
        if card is None:
            print(f"WARNING: card id {cid} not in card database, skipping", file=sys.stderr)
            continue
        cards_resolved.append({
            "id": cid,
            "count": deck_card_ids[cid],
            "name": card.get("name") or f"#{cid}",
            "cost": card.get("cost"),
        })

    diver_names = []
    for did in deck["divers"]:
        card = by_id.get(did)
        diver_names.append(card["name"] if card else f"#{did}")

    deck_slug = slugify(deck_name)
    deck_dir = os.path.join(args.out, deck_slug)

    if os.path.isdir(deck_dir):
        for root, dirs, files in os.walk(deck_dir, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                p_ = os.path.join(root, d)
                if not os.listdir(p_):
                    os.rmdir(p_)
    os.makedirs(deck_dir, exist_ok=True)

    with open(os.path.join(deck_dir, "!index.md"), "w") as f:
        f.write(_render_index(deck_name, deck_fmt, args.code, diver_names, cards_resolved))

    # All unique card ids to render: deck cards + divers (deduplicated, order preserved)
    all_ids = list(dict.fromkeys([e["id"] for e in cards_resolved] + deck["divers"]))

    slugs_used: dict[str, int] = {}
    for cid in all_ids:
        card = by_id.get(cid)
        if card is None:
            continue
        types = card.get("cardType") or []
        if not types:
            continue
        ctype = types[0]
        if ctype not in TYPE_CONFIG or ctype in ("IMMORTALIZED_AGENT", "UNKNOWN"):
            continue

        prose, show_stats = TYPE_CONFIG[ctype]
        cost = card.get("cost") or 0
        slug = slugify(card["name"])
        base_key = f"{cost:02d}-{slug}"
        n = slugs_used.get(base_key, 0) + 1
        slugs_used[base_key] = n
        filename = f"{base_key}.md" if n == 1 else f"{base_key}-{n}.md"

        immo = base_to_immo.get(cid)
        with open(os.path.join(deck_dir, filename), "w") as f:
            f.write(render_card(card, immo, prose, show_stats))

    print(f"Done. Written to {deck_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
