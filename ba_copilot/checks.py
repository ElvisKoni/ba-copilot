"""Scoring: structural checks (traceability) and content checks (did it catch what a good BA would)."""

from collections import Counter

from .schema import Analysis


def structural_checks(a: Analysis) -> list[tuple[str, bool, str]]:
    """Return (name, passed, detail) for checks that apply to every output."""
    ac_ids = [ac.id for s in a.stories for ac in s.acceptance_criteria]
    all_ids = (
        [r.id for r in a.business_rules]
        + [q.id for q in a.open_questions]
        + [r.id for r in a.risks]
        + [s.id for s in a.stories]
        + ac_ids
        + [t.id for t in a.uat_cases]
    )
    dupes = [i for i, n in Counter(all_ids).items() if n > 1]

    covered = {ac for t in a.uat_cases for ac in t.covers}
    uncovered = [ac for ac in ac_ids if ac not in covered]
    dangling = sorted({ac for t in a.uat_cases for ac in t.covers if ac not in ac_ids})
    types = {t.type for t in a.uat_cases}

    return [
        ("IDs are unique", not dupes, f"duplicates: {dupes}" if dupes else ""),
        ("Every AC is covered by a UAT case", not uncovered, f"uncovered: {uncovered}" if uncovered else ""),
        ("UAT cases reference existing ACs", not dangling, f"unknown: {dangling}" if dangling else ""),
        ("Has negative UAT cases", "negative" in types, ""),
        ("Has boundary UAT cases", "boundary" in types, ""),
        ("Raises open questions", len(a.open_questions) > 0, ""),
    ]


def _section_text(a: Analysis, section: str) -> str:
    parts: dict[str, list[str]] = {
        "business_rules": [f"{r.rule} {r.source_quote}" for r in a.business_rules],
        "open_questions": [f"{q.question} {q.why_it_matters}" for q in a.open_questions],
        "risks": [r.description for r in a.risks],
        "stories": [f"{s.as_a} {s.i_want} {s.so_that}" for s in a.stories],
        "acceptance_criteria": [
            f"{ac.given} {ac.when} {ac.then}" for s in a.stories for ac in s.acceptance_criteria
        ],
        "uat_cases": [
            f"{t.title} {t.preconditions} {' '.join(t.steps)} {t.expected_result}" for t in a.uat_cases
        ],
    }
    if section == "any":
        return " ".join(" ".join(v) for v in parts.values()).lower()
    return " ".join(parts[section]).lower()


def content_checks(a: Analysis, expectations: list[dict]) -> list[tuple[str, bool, str]]:
    """Each expectation passes if any of its keywords appears in any of its sections.

    Keyword matching is a cheap first pass. It can be fooled by synonyms, which is
    why a model-graded check is the planned next step (see README).
    """
    results = []
    for e in expectations:
        sections = e["sections"]
        text = " ".join(_section_text(a, s) for s in sections)
        hit = next((k for k in e["any_of"] if k.lower() in text), None)
        results.append((f'{e["id"]}: {e["description"]}', hit is not None, f"matched '{hit}'" if hit else ""))
    return results
