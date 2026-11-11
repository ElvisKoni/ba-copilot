# BA Copilot for Lending Products

Turns a vague business requirement for a banking lending product into documentation a delivery team can use: open questions for stakeholders, business rules, risks, user stories with Given/When/Then acceptance criteria, and UAT test cases, all traceable to each other and exportable to Jira.

The part that matters most is the **evaluation**: every change to the prompt is scored against a set of fictional requirements with the points a good Business Analyst would be expected to catch.

> All data in this repository is fictional. "Demo Bank" is not a real bank.

## Why

As a Product Owner for consumer loans, overdrafts and credit cards, most delivery problems I saw started with requirements that left out eligibility rules, limits, consent, rejection paths or what happens outside working hours. This tool asks those questions first, then writes the stories and tests.

## How it works

```
requirement text
      │
      ▼
LLM: Gemini (default, free tier) or Claude
      │   system prompt in prompts/vN.md
      │   output must match the Pydantic schema in ba_copilot/schema.py
      │   (Gemini: JSON schema mode, Claude: forced tool call)
      ▼
Analysis  ──►  structural checks (IDs unique, every AC tested, negative + boundary tests)
          ──►  content checks (did it catch what a BA should?)
          ──►  Jira CSV export
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # add your GEMINI_API_KEY (free at aistudio.google.com)

python analyse.py examples/requirement.txt --jira jira.csv
python -m evals.run_eval --runs 3 --note "first run"
pytest                         # offline tests, no API key needed
```

## Evaluation

Each file in `evals/cases/` holds one fictional requirement and a list of expectations, for example *"asks how bad credit history is defined"* or *"has a boundary test at exactly 3x salary"*. Every run appends a row to `evals/results.md`, so the effect of each prompt change is visible.

LLM output changes from one call to the next, so each prompt version is run **3 times per case** and the average is reported, together with the range across runs. Each check is reported as PASS (every run), FAIL (no run) or FLAKY (some runs).

### Results (gemini-3.8-flash, 3 cases, 29 content checks, 3 runs each)

| Prompt | Content (average) | Range across runs | Structure |
|---|---|---|---|
| v1: role and step-by-step instructions | 72% | 62-79% | 100% |
| v2: v1 + explicit BA checklist | **84%** | 79-86% | 100% |

The v2 checklist asks the model to define every number it sees and test at, above and below each limit, to write a negative test for every eligibility condition, to ask about repetition and retries, and to always assess fraud.

| Check that v1 never passed or rarely passed | v1 | v2 |
|---|---|---|
| Overdraft: UAT case above 3x salary | 0/3 | 3/3 |
| Consumer loan: UAT case for a customer without salary at the bank | 0/3 | 2/3 |
| Virtual card: fraud risk raised | 1/3 | 3/3 |
| Overdraft: asks which salary figure is used | 2/3 | 3/3 |
| Overdraft: asks how often an increase can be requested | 2/3 | 3/3 |

**What I learned**

- One run is not enough. The same prompt scored anywhere from 62% to 79% on the same cases.
- Structure was never the problem: forcing a JSON schema gave 100% traceability from the first version. The gaps were in BA judgement, which is what the checklist targets.
- Still missed: whether an overdraft customer must have their salary paid into the bank (0/3), and v2 raised contract amendment less often than v1 (1/3 against 3/3).
- The v2 rules were written after seeing failures on these same 3 cases, so this result may be optimistic. The next step is held-out cases the prompt was not tuned on.

Switch providers with `LLM_PROVIDER=gemini` or `LLM_PROVIDER=claude` in `.env` to compare models on the same cases.

**Known limitations:** content checks use keyword matching, which can pass or fail on wording alone, so a model-graded check is planned. There are only 3 cases so far.

## Roadmap

- [x] Schema, prompt v1, CLI, Jira export
- [x] Gemini and Claude providers
- [x] 3 eval cases with structural and keyword checks
- [x] Run baseline, iterate the prompt to v2 and record results over 3 runs
- [ ] Held-out eval cases the prompt was not tuned on
- [ ] Model-graded content checks
- [ ] 10+ eval cases
- [ ] Simple web UI
- [ ] MCP server exposing fictional loan-application data
