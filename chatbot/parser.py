"""Rule-based query parser: free text -> structured clauses. No model, no network.

Per request:
  1. split into clauses on 'and' / ',' / '&' / 'plus' (protecting 'between X and Y')
  2. per clause: price bounds, city, cuisine, tags (matched against the data's own vocabulary), intent
  3. any leftover word that is not filler is reported as 'ignored', never silently guessed at

Price semantics are explicit: under/below/less than are strict (<); up to/at most/max are inclusive (<=);
above/over/more than are strict (>); at least/min/from are inclusive (>=); 'between A and B' is inclusive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .store import Vocab

_NUM = r"[$€£]?\s*(\d[\d,]*(?:\.\d+)?)"
_NUM_RAW = r"[$€£]?\s*\d[\d,]*(?:\.\d+)?"
_L = r"(?<![a-z])"  # left word boundary that also works in front of symbols like '<'

_RANGE = re.compile(rf"{_L}(?:between|from)\s*{_NUM}\s*(?:to|-)\s*{_NUM}")
_RANGE_AND = re.compile(rf"((?:between|from)\s*{_NUM_RAW}\s*)and(\s*{_NUM_RAW})")
# Order matters: 'no more than' / 'no less than' must be consumed before 'more than' / 'less than'.
_PRICE_RULES = (
    (re.compile(rf"{_L}(?:up to|at most|no more than|not more than|maximum|max|within|<=)\s*{_NUM}"), "hi", True),
    (re.compile(rf"{_L}(?:at least|no less than|minimum|min|starting at|from|>=)\s*{_NUM}"), "lo", True),
    (re.compile(rf"{_L}(?:under|below|less than|cheaper than|lower than|<)\s*{_NUM}"), "hi", False),
    (re.compile(rf"{_L}(?:above|over|more than|greater than|higher than|>)\s*{_NUM}"), "lo", False),
)

HOTEL_RE = re.compile(
    r"(?<![a-z])(?:hotels?|stays?|rooms?|lodging|accommodations?|motels?|hostels?|inns?|resorts?|suites?)(?![a-z])"
)
RESTAURANT_RE = re.compile(
    r"(?<![a-z])(?:restaurants?|eat|eating|dine|dining|dinners?|lunch|breakfast|brunch|food|cafes?|bistros?|diners?|meals?|eateries)(?![a-z])"
)
_BACKREF = re.compile(r"(?<![a-z])(?:(?:same|that|this)\s+(?:city|place|area|town)|there)(?![a-z])")
_SPLIT = re.compile(r"\band\b|,|;|&|\bplus\b|\balso\b|\bthen\b")

STOP = {
    "a", "an", "the", "i", "me", "my", "we", "us", "you", "please", "find", "show", "get", "give", "list",
    "search", "recommend", "suggest", "want", "need", "looking", "look", "for", "in", "at", "on", "of", "to",
    "with", "some", "any", "there", "is", "are", "can", "could", "would", "like", "that", "have", "has", "do",
    "does", "same", "city", "place", "places", "spot", "spots", "option", "options", "one", "ones", "or",
    "what", "what's", "whats", "which", "where", "tell", "about", "per", "night", "nightly", "person", "pp",
    "dollars", "dollar", "euros", "euro", "usd", "eur", "gbp", "pounds", "bucks", "s",
}


def fmt_number(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


@dataclass
class PriceRange:
    lo: float | None = None
    lo_incl: bool = True
    hi: float | None = None
    hi_incl: bool = True

    @property
    def active(self) -> bool:
        return self.lo is not None or self.hi is not None

    def contains(self, price: float | None) -> bool:
        if not self.active:
            return True
        if price is None:
            return False
        if self.lo is not None and (price < self.lo or (price == self.lo and not self.lo_incl)):
            return False
        if self.hi is not None and (price > self.hi or (price == self.hi and not self.hi_incl)):
            return False
        return True

    def describe(self) -> str:
        parts = []
        if self.lo is not None:
            parts.append(f"price {'>=' if self.lo_incl else '>'} {fmt_number(self.lo)}")
        if self.hi is not None:
            parts.append(f"price {'<=' if self.hi_incl else '<'} {fmt_number(self.hi)}")
        return ", ".join(parts)


@dataclass
class Clause:
    kind: str  # "hotel" | "restaurant"
    cities: list[str] = field(default_factory=list)
    price: PriceRange = field(default_factory=PriceRange)
    cuisines: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    refers_back: bool = False


@dataclass
class Parsed:
    clauses: list[Clause]

    @property
    def ignored(self) -> list[str]:
        return [w for c in self.clauses for w in c.ignored]

    @property
    def status(self) -> str:
        """full | partial (some words ignored) | clarify (a clause has no usable city) | fallback (no intent)."""
        if not self.clauses:
            return "fallback"
        if any(not c.cities for c in self.clauses):
            return "clarify"
        return "partial" if self.ignored else "full"


def _num(text: str) -> float:
    return float(text.replace(",", ""))


def _blank(text: str, m: re.Match) -> str:
    return text[: m.start()] + " " * (m.end() - m.start()) + text[m.end():]


def _extract_price(text: str) -> tuple[PriceRange, str]:
    price = PriceRange()
    m = _RANGE.search(text)
    if m:
        price.lo, price.hi = sorted((_num(m.group(1)), _num(m.group(2))))
        text = _blank(text, m)
    for rx, side, inclusive in _PRICE_RULES:
        m = rx.search(text)
        if m:
            setattr(price, side, _num(m.group(1)))
            setattr(price, f"{side}_incl", inclusive)
            text = _blank(text, m)
    return price, text


def _term_pattern(key: str) -> re.Pattern:
    parts = re.split(r"[-\s]+", key.strip())
    return re.compile(r"(?<![a-z0-9])" + r"[-\s]+".join(re.escape(p) for p in parts) + r"(?![a-z0-9])")


def _find_terms(text: str, terms: dict[str, str]) -> tuple[list[str], str]:
    """Keys of `terms` found in `text` (in order of appearance) plus the text with those spans blanked."""
    hits: list[tuple[int, str]] = []
    for key in sorted(terms, key=len, reverse=True):  # longest first: 'new york' beats 'york'
        pattern = _term_pattern(key)
        m = pattern.search(text)
        while m:
            hits.append((m.start(), key))
            text = _blank(text, m)
            m = pattern.search(text)
    return [key for _, key in sorted(hits)], text


def _kind(text: str, vocab: Vocab) -> str | None:
    hotel, restaurant = HOTEL_RE.search(text), RESTAURANT_RE.search(text)
    if hotel and restaurant:
        return "hotel" if hotel.start() < restaurant.start() else "restaurant"
    if hotel:
        return "hotel"
    if restaurant or _find_terms(text, vocab.cuisines)[0]:
        return "restaurant"
    return None


def _parse_clause(chunk: str, vocab: Vocab) -> Clause:
    kind = _kind(chunk, vocab)
    refers_back = bool(_BACKREF.search(chunk))
    price, text = _extract_price(chunk)
    cities, text = _find_terms(text, vocab.cities)
    cuisines: list[str] = []
    if kind == "restaurant":
        cuisines, text = _find_terms(text, vocab.cuisines)
    tags, text = _find_terms(text, vocab.hotel_tags if kind == "hotel" else vocab.restaurant_tags)
    text = HOTEL_RE.sub(lambda m: " " * len(m.group()), text)
    text = RESTAURANT_RE.sub(lambda m: " " * len(m.group()), text)
    ignored = [w for w in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text) if w not in STOP]
    return Clause(kind, cities, price, cuisines, tags, ignored, refers_back)


def _inherit_cities(clauses: list[Clause]) -> None:
    """'... a Caribbean restaurant in the same city' reuses the city from a neighbouring clause.
    Only done when the clause points back ('same city') or has no unexplained words, so
    'hotels in Tokyo' never silently turns into hotels in some other city."""
    for i, clause in enumerate(clauses):
        if clause.cities or not (clause.refers_back or not clause.ignored):
            continue
        for j in list(range(i - 1, -1, -1)) + list(range(i + 1, len(clauses))):
            if clauses[j].cities:
                clause.cities = list(clauses[j].cities)
                break


def parse(text: str, vocab: Vocab) -> Parsed:
    lowered = text.lower().strip()
    lowered = _RANGE_AND.sub(r"\1to\2", lowered)  # keep 'between 100 and 200' in one piece
    chunks = [c.strip() for c in _SPLIT.split(lowered) if c.strip()]

    merged: list[str] = []
    pending = ""
    for chunk in chunks:
        if _kind(chunk, vocab) is None:  # no hotel/restaurant intent: belongs to a neighbouring clause
            if merged:
                merged[-1] += " " + chunk
            else:
                pending += " " + chunk
        else:
            merged.append((pending + " " + chunk).strip())
            pending = ""

    clauses = [_parse_clause(c, vocab) for c in merged]
    _inherit_cities(clauses)
    return Parsed(clauses)
