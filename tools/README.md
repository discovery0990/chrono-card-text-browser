# tools

Scripts and supporting code for generating and managing the card and deck browsers.

## Setup

The raw card data lives at `tools/cards.json`.

## Generating the card browser data

    just cards

Re-running on unchanged input produces no diff. Output goes to `./cards/` by default.

## Tests

    just test

To run a single suite:

    uv run python tools/tests/test_card_browser_gen.py
    uv run python tools/tests/test_deckcode.py
    uv run python tools/tests/test_deck_browser_gen.py
