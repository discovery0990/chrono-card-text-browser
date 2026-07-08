[private]
default:
    @just --list

# Regenerate the card browser data (extra flags: see tools/card_browser_gen.py --help)
cards:
    ./tools/card_browser_gen.py

# Import a deck for browsing (extra flags: see tools/deck_browser_gen.py --help)
deck code name:
    ./tools/deck_browser_gen.py {{code}} {{name}}

# Run test suite
test:
    uv run --directory tools python -m unittest discover tests
