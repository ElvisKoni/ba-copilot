"""Analyse one requirement from the command line.

    python analyse.py requirement.txt
    python analyse.py requirement.txt --jira out.csv
"""

import argparse
from pathlib import Path

from ba_copilot.export import to_jira_csv
from ba_copilot.generator import analyse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("requirement_file", type=Path)
    parser.add_argument("--out", type=Path, default=Path("analysis.json"))
    parser.add_argument("--jira", type=Path, help="also write a Jira import CSV")
    args = parser.parse_args()

    analysis = analyse(args.requirement_file.read_text(encoding="utf-8"))
    args.out.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
    print(f"{len(analysis.stories)} stories, {len(analysis.uat_cases)} UAT cases, "
          f"{len(analysis.open_questions)} open questions -> {args.out}")

    if args.jira:
        to_jira_csv(analysis, args.jira)
        print(f"Jira CSV -> {args.jira}")


if __name__ == "__main__":
    main()
