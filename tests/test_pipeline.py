"""Offline tests: no API key needed."""

import json
from pathlib import Path

from ba_copilot.checks import content_checks, structural_checks
from ba_copilot.export import to_jira_csv
from ba_copilot.schema import Analysis, tool_input_schema

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = Analysis.model_validate_json((Path(__file__).parent / "fixtures" / "sample_analysis.json").read_text())


def test_tool_schema_is_self_contained():
    assert "$ref" not in json.dumps(tool_input_schema())


def test_structural_checks_find_uncovered_ac():
    results = {name: (ok, detail) for name, ok, detail in structural_checks(SAMPLE)}
    ok, detail = results["Every AC is covered by a UAT case"]
    assert not ok and "AC-2.2" in detail  # the sample deliberately has no rejection test
    assert results["IDs are unique"][0]


def test_content_checks_against_case_01():
    case = json.loads((ROOT / "evals" / "cases" / "01_online_consumer_loan.json").read_text())
    results = {name.split(":")[0]: ok for name, ok, _ in content_checks(SAMPLE, case["expectations"])}
    assert results["E1"]  # asks about age
    assert results["E9"]  # boundary test above 1,000,000
    assert not results["E10"]  # sample has no test for a customer without salary


def test_jira_export(tmp_path):
    out = tmp_path / "jira.csv"
    to_jira_csv(SAMPLE, out)
    lines = out.read_text().splitlines()
    assert lines[0].startswith("Summary,Issue Type")
    assert "US-1" in out.read_text() and "TC-3" in out.read_text()
