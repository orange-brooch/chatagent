"""Phrasings that probe the edges of the rule-based grammar, with the status the parser is expected to give.

full      every word understood, filters applied
partial   answered, but some words were not understood and the reply says which were ignored
clarify   a clause has no usable city, so the bot asks instead of guessing
fallback  no hotel/restaurant intent at all, so the bot shows what it can do

These are my own phrasings, written to find where the grammar stops. The point is the shape of the
failures (the bot reports what it ignored), not a benchmark score.
Run:  python -m evals.phrasings
"""
from __future__ import annotations

from pathlib import Path

from chatbot import Store
from chatbot.parser import parse

CASES: list[tuple[str, str, str]] = [
    # (phrasing, expected status, note)
    ("Find me a hotel in Paris under 90", "full", "example query 1"),
    ("Show me French restaurants in Miami", "full", "example query 2"),
    ("Find me a hotel in Miami under 100 and a Caribbean restaurant in the same city", "full", "example query 3"),
    ("Find me luxury hotels in Paris above 500", "full", "example query 4"),
    ("hotels in Paris between 100 and 200", "full", "range, inclusive"),
    ("paris hotels at most 150", "full", "different word order and price phrase"),
    ("I want Caribbean food in Miami", "full", "'food' implies restaurant"),
    ("Find a hotel in Paris and a restaurant in Miami", "full", "two cities, one per clause"),
    ("budget hotels in Miami with a pool", "full", "tags come from the data"),
    ("a hotel and a restaurant in Paris under 100", "full", "KNOWN GAP: the price binds to the restaurant clause only"),
    ("somewhere cheap to stay in Paris", "partial", "'cheap' has no number"),
    ("romantic dinner in Miami", "partial", "'romantic' is a judgement, not a field"),
    ("a hotel in Paris under ninety euros", "partial", "number words are not parsed"),
    ("what's the cheapest hotel in Miami?", "partial", "superlatives need ranking logic"),
    ("hotel near the Eiffel Tower", "clarify", "no city, and no notion of distance"),
    ("hotels in Tokyo under 200", "clarify", "city not in the data"),
    ("and something cheaper?", "fallback", "follow-ups need conversation state"),
    ("what's the weather in Paris?", "fallback", "out of scope"),
]


def run(data_dir: str | Path = Path(__file__).resolve().parent.parent / "tests" / "fixtures"):
    store = Store.load(data_dir)
    return [(text, expected, note, parse(text, store.vocab)) for text, expected, note in CASES]


def main() -> None:
    results = run()
    print("| Phrasing | Status | Ignored words | Note |")
    print("|---|---|---|---|")
    for text, _expected, note, parsed in results:
        ignored = ", ".join(parsed.ignored) or "-"
        print(f"| {text} | {parsed.status} | {ignored} | {note} |")
    counts = {s: sum(1 for *_, p in results if p.status == s) for s in ("full", "partial", "clarify", "fallback")}
    print(f"\n{len(results)} phrasings: " + ", ".join(f"{n} {s}" for s, n in counts.items()))


if __name__ == "__main__":
    main()
