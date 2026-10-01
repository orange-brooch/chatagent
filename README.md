# chatagent

A hotel and restaurant chatbot with **no LLM**: free-text questions are turned into structured tool calls by
rules, and every answer is a row read from JSON. Python standard library only (pytest for the tests).

I built it after an Educative Cloud Lab on Amazon Bedrock AgentCore (a Hotel Agent and a Restaurant Agent, each
exposing one tool, plus a supervisor that calls them). The question I wanted to answer: **if you remove the model,
what is left, and what exactly was the model doing?**

```
$ python -m chatbot "Find me a hotel in Miami under 100 and a Caribbean restaurant in the same city"
Hotels in Miami (price < 100):
  1. South Beach Hostelry - 95
  2. Biscayne Bay Motel - 99

Restaurants in Miami (cuisine: Caribbean):
  1. Island Spice Kitchen (Caribbean) - 26
  2. Calypso Grill (Caribbean) - 41
```

## Run

```
python -m chatbot                          # interactive
python -m chatbot "luxury hotels in Paris above 500"
python -m chatbot --data path/to/folder    # any folder with hotels.json + restaurants.json
pip install pytest && pytest -q            # 16 tests
python -m evals.phrasings                  # the phrasing probe described below
```

The data in `data/` is fictional. If you have the lab's own files, keep them local (for example in `data/lab/`,
which is git-ignored) and pass `--data data/lab`.

## How it works

| Piece | Role | Counterpart in an agent system |
|---|---|---|
| `store.py` | Loads the JSON, validates it, and **derives the vocabulary (cities, cuisines, tags) from the data** | The data source the tools read |
| `parser.py` | Splits a request into clauses, then extracts intent, city, price bounds, cuisine and tags | The part an LLM would do: free text to tool arguments |
| `tools.py` | `recommend_hotels(city, price, tags)` and `recommend_restaurants(city, cuisines, price, tags)` | The tools / sub-agents |
| `bot.py` | Parse, call tools, merge, format. Echoes every filter it applied and every word it ignored | The supervisor |

The tools take parameters and return rows, with no parsing or formatting inside them. A menu, a REST endpoint
or an LLM choosing arguments could call them unchanged.

### Price semantics (explicit on purpose)

| Phrase | Meaning |
|---|---|
| under, below, less than | strictly less than |
| up to, at most, max | less than or equal |
| above, over, more than | strictly greater than |
| at least, min, from | greater than or equal |
| between A and B | inclusive on both ends |

"Under 90" does not return a hotel priced exactly 90. That is tested.

## Where the rules stop

`evals/phrasings.py` runs 18 phrasings I wrote to find the edges of the grammar:
**10 fully understood, 4 partial, 2 needed a clarification, 2 fell back to help.**
It is my own probe, not a benchmark. What matters is how it fails: the bot says what it ignored instead of guessing.

| Phrasing | Result |
|---|---|
| "somewhere cheap to stay in Paris" | Answers, notes that it ignored "cheap" (no number to filter on) |
| "romantic dinner in Miami" | Answers, notes that it ignored "romantic" |
| "a hotel in Paris under ninety euros" | Number words are not parsed; the price is ignored and the reply says so |
| "hotel near the Eiffel Tower" | Asks for a city; there is no notion of distance |
| "hotels in Tokyo under 200" | Asks for a city from the data instead of guessing |
| "and something cheaper?" | Falls back to help; no conversation state |

**Known gap:** in "a hotel and a restaurant in Paris under 100" the price binds to the restaurant clause only.
The reply headers show which filters were applied, so it is visible, but it is wrong.

## What an LLM adds, and what it does not

The tool layer is identical in both designs. The difference is the front end:

- **Rules win** on determinism, cost (zero), latency (microseconds), exact testability, and never inventing a row.
- **A model wins** on paraphrase, vague or subjective asks ("cheap", "romantic"), several intents in one sentence,
  follow-ups, and writing a natural reply.
- **The risk a model adds:** fluent answers that are not in the data. The tests here assert that every returned
  row is a real row; an LLM version needs equivalent grounding checks.

A sensible hybrid is a model that only picks tool arguments, with these same tools underneath.

## Why Python here, and when I'd pick Java

I built only the Python version, so this is design reasoning, not measurement.

- **Python:** JSON and regex are in the standard library, so it is the least code and the fastest to a working
  version. Agent tooling and samples skew Python.
- **Java:** needs a JSON library, and is more verbose for text parsing. In return it gives compile-time checks on
  tool signatures and fits a team already running JVM services at scale.
- **At this data size neither is a performance question.** The deciding factors are team, ecosystem and how long the
  code will live. A Java menu-driven version of this idea is kept at the git tag `v0.1-java-menu`.

## Layout

```
chatbot/   store.py parser.py tools.py bot.py __main__.py
data/      hotels.json restaurants.json (fictional)
tests/     test_bot.py, fixtures/ (frozen copy of the data)
evals/     phrasings.py
```
