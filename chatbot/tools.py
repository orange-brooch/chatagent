"""The two tools. Same shape as the lab's runtimes: one function per domain, parameters in, rows out.
No parsing and no formatting in here, so a different front end (a menu, a REST endpoint, an LLM
choosing tool arguments) can call them unchanged.
"""
from __future__ import annotations

from typing import Iterable

from .parser import PriceRange
from .store import Record, Store


def _ordered(rows: Iterable[Record]) -> list[Record]:
    return sorted(rows, key=lambda r: (r.price is None, r.price or 0.0, r.name))


def _has_tags(record: Record, tags: Iterable[str]) -> bool:
    have = {t.lower() for t in record.tags}
    return all(t in have for t in tags)


def recommend_hotels(store: Store, city: str, price: PriceRange | None = None, tags: Iterable[str] = ()) -> list[Record]:
    price = price or PriceRange()
    return _ordered(
        r for r in store.hotels
        if r.city.lower() == city.lower() and price.contains(r.price) and _has_tags(r, tags)
    )


def recommend_restaurants(
    store: Store,
    city: str,
    cuisines: Iterable[str] = (),
    price: PriceRange | None = None,
    tags: Iterable[str] = (),
) -> list[Record]:
    price, wanted = price or PriceRange(), {c.lower() for c in cuisines}
    return _ordered(
        r for r in store.restaurants
        if r.city.lower() == city.lower()
        and (not wanted or (r.cuisine or "").lower() in wanted)
        and price.contains(r.price)
        and _has_tags(r, tags)
    )


def price_span(rows: Iterable[Record]) -> tuple[float, float] | None:
    prices = [r.price for r in rows if r.price is not None]
    return (min(prices), max(prices)) if prices else None
