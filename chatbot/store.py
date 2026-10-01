"""Data layer: loads hotels.json / restaurants.json and derives the parser's vocabulary from them.

Nothing about cities, cuisines or tags is hard-coded. Point the bot at a different dataset and it
understands that dataset's cities, cuisines and tags. This is the role the S3 bucket plays in the lab.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# The one place to adapt if a dataset names its fields differently.
FIELD_ALIASES = {
    "name": ("name", "hotel_name", "restaurant_name", "title"),
    "city": ("city", "location"),
    "price": ("price", "price_per_night", "pricePerNight", "cost", "rate"),
    "cuisine": ("cuisine", "cuisine_type"),
    "tags": ("tags", "amenities", "features"),
}


class DataError(Exception):
    """A data file is missing or not in a shape this bot understands."""


@dataclass(frozen=True)
class Record:
    name: str
    city: str
    price: float | None = None
    cuisine: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Vocab:
    """Lowercase lookup key -> display form, for everything the parser can recognise."""

    cities: dict[str, str]
    cuisines: dict[str, str]
    hotel_tags: dict[str, str]
    restaurant_tags: dict[str, str]


def _pick(row: dict, field: str):
    for key in FIELD_ALIASES[field]:
        if key in row:
            return row[key]
    return None


def _number(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    digits = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(digits)
    except ValueError:
        return None


def _load_rows(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DataError(f"missing data file: {path}") from None
    except json.JSONDecodeError as exc:
        raise DataError(f"{path.name} is not valid JSON: {exc}") from None
    if isinstance(data, dict):  # tolerate {"hotels": [...]}
        lists = [v for v in data.values() if isinstance(v, list)]
        data = lists[0] if lists else []
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise DataError(f"{path.name} must contain a list of objects")
    return data


def _to_records(rows: list[dict], path: Path, restaurant: bool) -> list[Record]:
    records = []
    for i, row in enumerate(rows):
        name, city = _pick(row, "name"), _pick(row, "city")
        if not name or not city:
            raise DataError(f"{path.name} record {i}: need 'name' and 'city' (found keys: {sorted(row)})")
        tags = _pick(row, "tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        cuisine = _pick(row, "cuisine") if restaurant else None
        records.append(
            Record(
                name=str(name),
                city=str(city),
                price=_number(_pick(row, "price")),
                cuisine=str(cuisine) if cuisine else None,
                tags=tuple(str(t) for t in tags),
            )
        )
    return records


def _index(values) -> dict[str, str]:
    out: dict[str, str] = {}
    for value in values:
        key = value.strip().lower()
        if key:
            out.setdefault(key, value.strip())
    return out


class Store:
    def __init__(self, hotels: list[Record], restaurants: list[Record]):
        self.hotels = list(hotels)
        self.restaurants = list(restaurants)
        self.vocab = Vocab(
            cities=_index(r.city for r in self.hotels + self.restaurants),
            cuisines=_index(r.cuisine for r in self.restaurants if r.cuisine),
            hotel_tags=_index(t for r in self.hotels for t in r.tags),
            restaurant_tags=_index(t for r in self.restaurants for t in r.tags),
        )

    @classmethod
    def load(cls, data_dir: str | Path = "data") -> "Store":
        folder = Path(data_dir)
        hotels_path, restaurants_path = folder / "hotels.json", folder / "restaurants.json"
        return cls(
            _to_records(_load_rows(hotels_path), hotels_path, restaurant=False),
            _to_records(_load_rows(restaurants_path), restaurants_path, restaurant=True),
        )
