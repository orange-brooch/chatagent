# Eval notes

`phrasings.py` runs 18 hand-written phrasings through the parser and records the **status** each one gets.
Regenerate the table with `python3 -m evals.phrasings`. `tests/test_bot.py` fails if any status changes, so a
behaviour change is always a deliberate edit to `CASES`.

## Statuses

| Status | Meaning | What the user sees |
|---|---|---|
| full | Every word was understood and every filter applied | Results, with the applied filters in each header |
| partial | Answered, but some words had no meaning to the parser | Results plus a note listing the ignored words |
| clarify | A clause has no usable city | The answerable parts, then "Which city?" |
| fallback | No hotel or restaurant intent at all | The help text |

## Results (against `tests/fixtures`)

10 full, 4 partial, 2 clarify, 2 fallback, out of 18.

| Phrasing | Status | Ignored words | Why |
|---|---|---|---|
| Find me a hotel in Paris under 90 | full | - | example query 1 |
| Show me French restaurants in Miami | full | - | example query 2 |
| Find me a hotel in Miami under 100 and a Caribbean restaurant in the same city | full | - | example query 3 |
| Find me luxury hotels in Paris above 500 | full | - | example query 4 |
| hotels in Paris between 100 and 200 | full | - | inclusive range |
| paris hotels at most 150 | full | - | different word order and price phrase |
| I want Caribbean food in Miami | full | - | "food" implies restaurant |
| Find a hotel in Paris and a restaurant in Miami | full | - | two cities, one per clause |
| budget hotels in Miami with a pool | full | - | tags come from the data |
| a hotel and a restaurant in Paris under 100 | full | - | **known gap:** price binds to the restaurant only |
| somewhere cheap to stay in Paris | partial | somewhere, cheap | "cheap" has no number |
| romantic dinner in Miami | partial | romantic | a judgement, not a field |
| a hotel in Paris under ninety euros | partial | under, ninety | number words are not parsed |
| what's the cheapest hotel in Miami? | partial | cheapest | superlatives need ranking logic |
| hotel near the Eiffel Tower | clarify | near, eiffel, tower | no city, and no notion of distance |
| hotels in Tokyo under 200 | clarify | tokyo | city not in the data |
| and something cheaper? | fallback | - | follow-ups need conversation state |
| what's the weather in Paris? | fallback | - | out of scope |

## What the cases showed

1. **A partial answer can mislead.** "Under ninety euros" lists every Paris hotel with a note at the bottom. A user
   who skims past the note reads an unfiltered list as a filtered one. A better behaviour is to ask when the
   ignored word is a price keyword (under, over, below, above, between).
2. **Modifiers bind to their own clause.** In "a hotel and a restaurant in Paris under 100" the price reaches only
   the restaurant. The header makes this visible, but the result is still not what the user meant.
3. **Judgement words need a policy, not just a parser.** "Cheap" and "romantic" cannot be mapped to a field without
   a definition (cheap relative to what: the city, the dataset, the user's earlier budget?). A model would still
   need that definition or grounding, so this is a product decision, not only a technical one.

## What this eval does not tell you

- **"full" is not "correct".** It means every word was consumed. Whether the returned rows are right is asserted
  separately in `tests/test_bot.py` (for example, a hotel priced exactly 90 is excluded by "under 90").
- **Small and not representative.** 18 phrasings written during development to probe the grammar, not sampled from
  real users. Treat the 10/4/2/2 split as an illustration of how the parser fails, not as a score.
- **No model baseline yet.** Nothing here measures an LLM front end. Any claim about where a model helps is a
  hypothesis until the same phrasings are run through one.
- **Coupled to the fixtures.** The vocabulary comes from `tests/fixtures`. Adding a city or tag to that data can
  change statuses (for example, Tokyo would stop being unknown).

## Adding a case

Append `(phrasing, expected_status, note)` to `CASES` in `phrasings.py`, run `python3 -m evals.phrasings`, and
confirm the status is the one you intended. Candidates not yet covered: a typo in an intent word ("hotle in
paris"), a currency symbol ("under $90"), two cities in one clause, mixed case.

## Next for the evals

- Store the expected **structured call** (kind, city, price bounds, cuisine, tags) for each full case, not only a
  status, so that slot accuracy can be scored.
- Add a second front end (a model that extracts tool arguments) and score both on slot accuracy, latency and cost
  for the same phrasings.
- Grow the set with phrasings from people who did not write the parser.
