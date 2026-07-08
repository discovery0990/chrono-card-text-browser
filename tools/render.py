"""Shared card rendering primitives used by card_browser_gen and deck_browser_gen."""
import re
import sys
import unicodedata

# cardType → (prose label, show_stats)
TYPE_CONFIG: dict[str, tuple[str | None, bool]] = {
    "AGENT":               ("",          True),
    "IMMORTALIZED_AGENT":  (None,        False),  # embedded; no file
    "ACTION_SLOW":         ("Slow",      False),
    "ACTION_FAST":         ("Fast",      False),
    "ACTION_IMMEDIATE":    ("Immediate", False),
    "TOKEN":               ("",          True),
    "UNKNOWN":             ("UNKNOWN",   False),  # created by effects; not deckable
}

# Characters reserved for the card name in the header line.
# Longest observed name is 28 chars; 33 guarantees a 5-char gap.
NAME_COL = 33

# Prefix on the immortalized-form embed line (2 spaces + arrow + space = 4 cols).
EMBED_PREFIX = "  ⇒ "


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"['']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def clean_text(text: str) -> str:
    """Normalize line endings; strip trailing whitespace per line."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("[icon]", "(C)")
    return "\n".join(line.rstrip() for line in text.split("\n"))


def indent_embed(text: str) -> str:
    """Prepend 2 spaces to each line of the immortalized embed text."""
    return "\n".join(
        ("  " + line) if line.strip() else ""
        for line in clean_text(text).split("\n")
    )


def stat_suffix(cost: int, s: int, d: int, prose: str, show_stats: bool) -> str:
    """Return the right-hand side of a header line."""
    if show_stats and (s or d):
        base = f"{cost} | {s}/{d}"
        return f"{base} | {prose}" if prose else base
    return f"{cost} | {prose}"


def render_card(
    card: dict,
    immo: dict | None,
    prose: str,
    show_stats: bool,
) -> str:
    parts: list[str] = []

    cost = card["cost"]
    s = card.get("strength") or 0
    d = card.get("durability") or 0
    parts.append(f"{card['name']:<{NAME_COL}}{stat_suffix(cost, s, d, prose, show_stats)}")

    parts.append("---")

    parts.append(clean_text(card.get("text") or ""))

    if immo is not None:
        embed_name_col = NAME_COL - len(EMBED_PREFIX)
        ic = immo["cost"]
        is_ = immo.get("strength") or 0
        id_ = immo.get("durability") or 0
        parts.append("")
        immo_name = immo["name"]
        immo_pad = " " * max(embed_name_col - len(immo_name), 1)
        parts.append(f"{EMBED_PREFIX}{immo_name}{immo_pad}{ic} | {is_}/{id_}")
        parts.append(indent_embed(immo.get("text") or ""))

    parts.append("---")

    rarity = card.get("rarityName") or ""
    set_name = (card.get("cardSet") or {}).get("name") or ""
    parts.append(f"{rarity} · {set_name}")

    return "\n".join(parts) + "\n"


def build_immo_map(by_id: dict[int, dict]) -> dict[int, dict]:
    """Return base_card_id → immortalized_card, warning on data anomalies."""
    result: dict[int, dict] = {}
    immo_used: set[int] = set()

    for card in by_id.values():
        immo_id = card.get("immortalizedCardId")
        if immo_id is None:
            continue
        immo = by_id.get(immo_id)
        if immo is None:
            print(
                f"WARNING: card {card['id']} ({card['name']!r}) references "
                f"missing immortalizedCardId={immo_id}",
                file=sys.stderr,
            )
        else:
            result[card["id"]] = immo
            immo_used.add(immo_id)

    for card in by_id.values():
        ctype = (card.get("cardType") or [None])[0]
        if ctype == "IMMORTALIZED_AGENT" and card["id"] not in immo_used:
            print(
                f"WARNING: orphaned IMMORTALIZED_AGENT: {card['id']} ({card['name']!r})",
                file=sys.stderr,
            )
        if ctype == "TOKEN" and card.get("immortalizedCardId"):
            print(
                f"WARNING: TOKEN card {card['id']} ({card['name']!r}) has "
                f"immortalizedCardId={card['immortalizedCardId']}",
                file=sys.stderr,
            )

    return result
