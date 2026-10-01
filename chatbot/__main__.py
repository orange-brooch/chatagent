"""CLI.  python3 -m chatbot                       interactive
       python3 -m chatbot "hotel in Paris under 90"   one-shot
       python3 -m chatbot --data path/to/folder         use another hotels.json / restaurants.json pair
"""
from __future__ import annotations

import argparse
import sys

from .bot import answer
from .store import DataError, Store


def main() -> int:
    ap = argparse.ArgumentParser(prog="chatbot", description="Rule-based hotel and restaurant chatbot (no LLM).")
    ap.add_argument("query", nargs="*", help="ask one question and exit")
    ap.add_argument("--data", default="data", help="folder with hotels.json and restaurants.json (default: data)")
    args = ap.parse_args()

    try:
        store = Store.load(args.data)
    except DataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.query:
        print(answer(store, " ".join(args.query)))
        return 0

    print("Ask about hotels and restaurants (blank line or 'q' to quit).")
    while True:
        try:
            line = input("\n> ").strip()
        except EOFError:
            break
        if not line or line.lower() in {"q", "quit", "exit"}:
            break
        print(answer(store, line))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
