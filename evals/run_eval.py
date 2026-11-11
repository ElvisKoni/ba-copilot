"""Run every eval case, score the outputs and append a row to evals/results.md.

    python -m evals.run_eval                 # one run per case, reuses saved outputs
    python -m evals.run_eval --runs 3        # three runs per case, reports the average
    python -m evals.run_eval --fresh         # regenerates every output
    python -m evals.run_eval --only 02       # runs only cases whose id starts with 02

LLM output varies between calls, so compare prompt versions with --runs 3 or more.

Outputs are saved per model and prompt version in evals/outputs/<model>_<prompt>/
(run 1 as <case>.json, later runs as <case>__run<n>.json), so an interrupted run
continues where it stopped. A row is added to results.md only when every run of
every case has been scored.
"""

import argparse
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

from ba_copilot.checks import content_checks, structural_checks
from ba_copilot.schema import Analysis

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"
OUTPUTS = HERE / "outputs"
RESULTS = HERE / "results.md"


def output_path(run_dir: Path, case_id: str, run: int) -> Path:
    return run_dir / (f"{case_id}.json" if run == 1 else f"{case_id}__run{run}.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1, help="how many times to run each case")
    parser.add_argument("--fresh", action="store_true", help="ignore saved outputs and call the model again")
    parser.add_argument("--only", default="", help="run only cases whose id starts with this text")
    parser.add_argument("--verbose", action="store_true", help="print every check of every run")
    parser.add_argument("--note", default="", help="short note for the results table, e.g. what you changed")
    args = parser.parse_args()

    from ba_copilot.generator import analyse, current_model, current_prompt_version

    model, prompt_version = current_model(), current_prompt_version()
    run_dir = OUTPUTS / f"{model}_{prompt_version}"
    run_dir.mkdir(parents=True, exist_ok=True)

    cases = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(CASES.glob("*.json"))]
    cases = [c for c in cases if c["id"].startswith(args.only)]

    # check name -> list of pass/fail across runs, per case
    content_hits: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    struct_hits: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    run_content_pct: dict[int, tuple[int, int]] = {}
    failed: list[str] = []

    for run in range(1, args.runs + 1):
        passed = total = 0
        for case in cases:
            out_file = output_path(run_dir, case["id"], run)
            label = f"{case['id']} (run {run}/{args.runs})"

            if out_file.exists() and not args.fresh:
                print(f"using saved output for {label}")
                analysis = Analysis.model_validate_json(out_file.read_text(encoding="utf-8"))
            else:
                print(f"running {label} with {model} ...")
                try:
                    analysis = analyse(case["requirement"])
                except Exception as e:
                    print(f"  FAILED: {str(e)[:200]}")
                    failed.append(label)
                    continue
                out_file.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
                time.sleep(5)  # stay under free-tier per-minute limits

            content = content_checks(analysis, case["expectations"])
            struct = structural_checks(analysis)
            for name, ok, _ in content:
                content_hits[case["id"]][name].append(ok)
            for name, ok, _ in struct:
                struct_hits[case["id"]][name].append(ok)
            passed += sum(ok for _, ok, _ in content)
            total += len(content)

            if args.verbose:
                print(f"  == {case['title']} ==")
                for name, ok, detail in struct + content:
                    print(f"    {'PASS' if ok else 'FAIL'}  {name}  {detail}")
        if total:
            run_content_pct[run] = (passed, total)

    if not content_hits:
        print("Nothing was scored.")
        return

    # per-check report: shows which expectations are reliable and which are flaky
    for case in cases:
        if case["id"] not in content_hits:
            continue
        print(f"\n== {case['title']} ==")
        for hits in (struct_hits[case["id"]], content_hits[case["id"]]):
            for name, results in hits.items():
                n, k = len(results), sum(results)
                status = "PASS " if k == n else ("FAIL " if k == 0 else "FLAKY")
                print(f"  {status} {k}/{n}  {name}")

    all_content = [ok for c in content_hits.values() for r in c.values() for ok in r]
    all_struct = [ok for c in struct_hits.values() for r in c.values() for ok in r]
    content_pct = round(100 * sum(all_content) / len(all_content))
    struct_pct = round(100 * sum(all_struct) / len(all_struct))
    per_run = [round(100 * p / t) for p, t in run_content_pct.values()]
    spread = f" (runs: {min(per_run)}-{max(per_run)}%)" if len(per_run) > 1 else ""

    print(f"\nContent: {content_pct}%{spread}   Structure: {struct_pct}%   Runs: {len(per_run)}")

    if failed or args.only:
        if failed:
            print(f"\nNot finished: {failed}. Run the same command again later; saved outputs are reused.")
        print("No row added to results.md until all runs of all cases are scored.")
        return

    content_cell = f"{content_pct}%" + (f" ({min(per_run)}-{max(per_run)})" if len(per_run) > 1 else "")
    if RESULTS.exists() and "| Runs |" not in RESULTS.read_text(encoding="utf-8"):
        RESULTS.replace(RESULTS.with_name("results_single_runs.md"))  # older table format
    if not RESULTS.exists():
        RESULTS.write_text(
            "# Eval results\n\n| Date | Prompt | Model | Runs | Content | Structure | Note |\n"
            "|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(f"| {date.today()} | {prompt_version} | {model} | {len(per_run)} | {content_cell} "
                f"| {struct_pct}% | {args.note} |\n")


if __name__ == "__main__":
    main()
