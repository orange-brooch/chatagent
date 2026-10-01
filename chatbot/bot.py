"""Orchestration: parse -> call tools -> format a reply. Every filter that was applied is echoed in the
section header, and every word that was not understood is listed, so the user can see what the bot did."""
from __future__ import annotations

from .parser import Clause, fmt_number, parse
from .store import Record, Store
from .tools import price_span, recommend_hotels, recommend_restaurants

LIMIT = 10


def _help(store: Store) -> str:
    cities = ", ".join(sorted(store.vocab.cities.values())) or "(none loaded)"
    return (
        "I can find hotels and restaurants. Try, for example:\n"
        "  - Find me a hotel in <city> under <price>\n"
        "  - Show me <cuisine> restaurants in <city>\n"
        "  - Find me a hotel in <city> under <price> and a <cuisine> restaurant in the same city\n"
        "  - Find me luxury hotels in <city> above <price>\n"
        f"Cities I have data for: {cities}."
    )


def _filters(clause: Clause, store: Store) -> str:
    bits = []
    if clause.price.active:
        bits.append(clause.price.describe())
    bits += [f"cuisine: {store.vocab.cuisines[c].title()}" for c in clause.cuisines]
    tag_vocab = store.vocab.hotel_tags if clause.kind == "hotel" else store.vocab.restaurant_tags
    bits += [f"tag: {tag_vocab[t]}" for t in clause.tags]
    return ", ".join(bits)


def _line(i: int, record: Record, kind: str) -> str:
    price = fmt_number(record.price) if record.price is not None else "n/a"
    cuisine = f" ({record.cuisine.title()})" if kind == "restaurant" and record.cuisine else ""
    return f"  {i}. {record.name}{cuisine} - {price}"


def _section(store: Store, clause: Clause, key: str) -> str:
    city = store.vocab.cities[key]
    noun = "Hotels" if clause.kind == "hotel" else "Restaurants"
    filters = _filters(clause, store)
    header = f"{noun} in {city}" + (f" ({filters})" if filters else "")
    try:
        if clause.kind == "hotel":
            rows = recommend_hotels(store, key, clause.price, clause.tags)
            everything = recommend_hotels(store, key)
        else:
            rows = recommend_restaurants(store, key, clause.cuisines, clause.price, clause.tags)
            everything = recommend_restaurants(store, key)
    except Exception as exc:  # one failing tool must not take down the rest of the reply
        return f"{header}:\n  unavailable right now ({exc})"

    if rows:
        lines = [_line(i, r, clause.kind) for i, r in enumerate(rows[:LIMIT], 1)]
        if len(rows) > LIMIT:
            lines.append(f"  (+{len(rows) - LIMIT} more)")
        return f"{header}:\n" + "\n".join(lines)

    span = price_span(everything)
    hint = f" {noun} in {city} range from {fmt_number(span[0])} to {fmt_number(span[1])}." if span else ""
    return f"{header}:\n  No matches.{hint}"


def answer(store: Store, text: str) -> str:
    parsed = parse(text, store.vocab)
    if parsed.status == "fallback":
        return _help(store)

    sections = [_section(store, c, key) for c in parsed.clauses for key in c.cities]
    reply = "\n\n".join(sections)

    missing = [("hotels" if c.kind == "hotel" else "restaurants") for c in parsed.clauses if not c.cities]
    if missing:
        cities = ", ".join(sorted(store.vocab.cities.values()))
        ask = f"Which city for the {' and '.join(missing)}? I have data for: {cities}."
        reply = f"{reply}\n\n{ask}" if reply else ask

    if parsed.ignored:
        words = ", ".join(f"'{w}'" for w in parsed.ignored)
        verb = "that word" if len(parsed.ignored) == 1 else "those words"
        reply += f"\n\nNote: I didn't understand {words}, so I ignored {verb}. An explicit price helps, e.g. \"under 100\"."
    return reply
