# scripted-chat-agent

A Java chat agent with **no LLM**: the user picks from scripted choices, and every answer is a row read from a data table.
I built it as a deliberate counterpart to a cloud lab on Amazon Bedrock AgentCore (a Hotel Agent and a Restaurant Agent,
each in its own runtime, reading from S3), to compare the two designs on correctness, cost, flexibility and operations.

Java 17+ standard library only. Synthetic data. No build tool, no downloads.

## Run

```
javac -d out src/*.java
java -cp out ChatEngineTest     # 9 checks, exit code 1 on failure
java -cp out Main               # interactive chat
```

## How it maps to the lab

| Lab (AgentCore + S3 + LLM) | This project | Backend concept |
|---|---|---|
| Hotel Agent / Restaurant Agent runtimes | `ScriptedAgent` instances, one per domain | Service boundary per domain |
| S3 bucket holding the data | `CsvTable` (swap `select()` for JDBC to use a real DB) | Storage adapter |
| LLM interprets free text | Fixed menu; each choice maps to a predicate | Intent parsing replaced by a closed set of intents |
| LLM writes the answer | Answer is formatted rows from the table | Deterministic output |
| Supervisor combines agents | `ChatEngine` "Plan a trip" merges both agents per city | Scatter-gather orchestration |
| One agent down | Router reports "unavailable" and still answers with the rest | Graceful degradation |

## Scripted vs LLM-backed: what changes

| | Scripted (this repo) | LLM + AgentCore + S3 |
|---|---|---|
| Correctness | Answers are exactly the rows queried. Tests compare replies to an independent query. | Fluent but can misstate or invent details unless grounded and evaluated |
| Flexibility | Only the questions in the menu | Free-form questions, follow-ups, vague requests |
| Cost / latency | Effectively zero, microseconds | Per-token model cost plus network hops |
| Testing | Exact assertions | Evals and statistical checks |
| Ops | One process | Managed runtimes, IAM, observability |
| Failure modes | Missing data, bad input | Hallucination, tool misuse, prompt injection, plus the above |

The useful takeaway: an LLM agent is this same skeleton (data access, routing, merging, failure handling) with the fixed menu
replaced by a model that chooses queries and phrases answers. The skeleton is where correctness comes from.

## Intent of this project

A learning experiment, not a product. The scripted design is deliberately limited: it trades flexibility for guaranteed-correct answers.

## Possible next steps
- [ ] Replace `CsvTable` with SQLite/H2 via JDBC
- [ ] Add a model-backed router that maps free text to one of the existing options (the menu becomes the tool list)
- [ ] Per-call timing log
