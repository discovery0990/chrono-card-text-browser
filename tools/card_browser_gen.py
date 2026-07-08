#!/usr/bin/env python3
"""
Generate a yazi-browsable plain-text card directory from the Chrono DB
card database.

Usage:
    python3 card_browser_gen.py [--input FILE] [--out DIR]

    --input FILE   path to cards.json (default: ./tools/cards.json)
    --out DIR      output directory   (default: ./cards)

Each run wipes and regenerates the output tree; re-running on unchanged
input produces zero git diff.

Output tree:
    cards/
      <syndicate>/
        NN-slug.md          (agents and actions, cost-sorted by filename)
        _tokens/
          NN-slug.md        (TOKEN cards)

Card files contain only faithful renderings of printed card data.
Derived/computed content is prohibited by design. Query patterns for
condition keywords, gained/lost abilities, etc. live in tools/README.md.
"""
import argparse
import json
import os
import sys

from render import TYPE_CONFIG, build_immo_map, render_card, slugify


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate a yazi-browsable card tree from Chrono CCG data"
    )
    p.add_argument("--input", metavar="FILE", default="tools/cards.json",
                   help="path to cards.json (default: ./tools/cards.json)")
    p.add_argument("--out", metavar="DIR", default="./cards",
                   help="output directory (default: ./cards)")
    args = p.parse_args()

    if args.input:
        with open(args.input) as f:
            cards: list[dict] = json.load(f)
    else:
        cards = json.load(sys.stdin)

    # Validate card types; fail loudly on unknowns or multi-type cards
    seen_types: set[str] = set()
    for card in cards:
        types = card.get("cardType") or []
        if len(types) > 1:
            sys.exit(
                f"ERROR: card {card['id']} ({card['name']!r}) has multiple types: "
                f"{', '.join(types)}\nCannot generate without a type-joining rule."
            )
        if types:
            seen_types.add(types[0])

    unknown = seen_types - set(TYPE_CONFIG)
    if unknown:
        sys.exit(
            f"ERROR: unknown cardType values: {', '.join(sorted(unknown))}\n"
            f"Update TYPE_CONFIG before running."
        )

    by_id: dict[int, dict] = {c["id"]: c for c in cards}

    base_to_immo = build_immo_map(by_id)

    out = args.out
    if os.path.isdir(out):
        for root, dirs, files in os.walk(out, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                p_ = os.path.join(root, d)
                if not os.listdir(p_):
                    os.rmdir(p_)
    os.makedirs(out, exist_ok=True)

    # Track slug collisions per directory
    slugs_used: dict[str, int] = {}
    written: int = 0
    by_syndicate: dict[str, int] = {}

    for card in cards:
        types = card.get("cardType") or []
        if not types:
            print(
                f"WARNING: card {card['id']} ({card['name']!r}) has no cardType, skipping",
                file=sys.stderr,
            )
            continue

        ctype = types[0]
        if ctype == "IMMORTALIZED_AGENT":
            continue

        prose, show_stats = TYPE_CONFIG[ctype]

        syndicate = (card.get("syndicate") or "unknown").lower()
        if ctype in ("TOKEN", "UNKNOWN"):
            card_dir = os.path.join(out, syndicate, "_tokens")
        else:
            card_dir = os.path.join(out, syndicate)

        os.makedirs(card_dir, exist_ok=True)

        cost = card.get("cost") or 0
        slug = slugify(card["name"])
        base_key = f"{card_dir}\x00{cost:02d}-{slug}"

        n = slugs_used.get(base_key, 0) + 1
        slugs_used[base_key] = n

        if n == 1:
            filename = f"{cost:02d}-{slug}.md"
        else:
            filename = f"{cost:02d}-{slug}-{n}.md"

        immo = base_to_immo.get(card["id"])
        content = render_card(card, immo, prose, show_stats)

        with open(os.path.join(card_dir, filename), "w") as f:
            f.write(content)
        written += 1
        by_syndicate[syndicate] = by_syndicate.get(syndicate, 0) + 1

    syndicate_summary = ", ".join(
        f"{s[:3].upper()}: {n}" for s, n in sorted(by_syndicate.items())
    )
    print(f"Done. {written} cards written to {out}/  ({syndicate_summary})", file=sys.stderr)


if __name__ == "__main__":
    main()
