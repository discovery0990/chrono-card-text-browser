# tools

Scripts and supporting code for generating and managing the card and deck browsers.

## Setup

The card database lives at `tools/cards.json`.

## Generating the card browser data

    just cards

Re-running on unchanged input produces no diff. Output goes to `./cards/` by default (`--out DIR` to change).

## Generating a deck directory

    just deck CODE NAME


## Tests

    just test

To run a single suite:

    uv run python tools/tests/test_card_browser_gen.py
    uv run python tools/tests/test_deckcode.py
    uv run python tools/tests/test_deck_browser_gen.py
