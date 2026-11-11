"""Export an Analysis to a CSV that Jira's CSV importer can map."""

import csv
from pathlib import Path

from .schema import Analysis


def to_jira_csv(a: Analysis, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Summary", "Issue Type", "Priority", "Description", "Labels", "External ID"])
        priority = {"Must": "High", "Should": "Medium", "Could": "Low"}
        for s in a.stories:
            acs = "\n".join(f"*{ac.id}* Given {ac.given}, when {ac.when}, then {ac.then}" for ac in s.acceptance_criteria)
            desc = (
                f"As a {s.as_a}, I want {s.i_want}, so that {s.so_that}.\n\n"
                f"h3. Acceptance criteria\n{acs}\n\nSource: _{s.source_quote}_"
            )
            w.writerow([f"{s.id} {s.i_want}"[:250], "Story", priority[s.priority], desc, "ba-copilot", s.id])
        for t in a.uat_cases:
            steps = "\n".join(f"# {step}" for step in t.steps)
            desc = (
                f"Covers: {', '.join(t.covers)}\nType: {t.type}\n\n"
                f"h3. Preconditions\n{t.preconditions}\n\nh3. Steps\n{steps}\n\n"
                f"h3. Expected result\n{t.expected_result}"
            )
            w.writerow([f"{t.id} {t.title}"[:250], "Task", "Medium", desc, "ba-copilot uat", t.id])
