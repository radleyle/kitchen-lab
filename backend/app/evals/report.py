"""Print a human-readable eval report.

    docker compose exec backend python -m app.evals.report
"""

from app.evals.grader import grade
from app.evals.runner import run_scenario
from app.evals.scenarios import SCENARIOS


def main() -> int:
    passed = 0
    failed = 0
    print(f"KitchenLab eval harness -- {len(SCENARIOS)} scenarios\n")
    for scenario in SCENARIOS:
        result = run_scenario(scenario)
        report = grade(scenario.id, result, scenario.checks)
        mark = "PASS" if report.passed else "FAIL"
        print(f"[{mark}] {scenario.id}")
        print(f"       {scenario.title}")
        if not report.passed:
            failed += 1
            for f in report.failures:
                print(f"         - {f}")
        else:
            passed += 1
    print(f"\n{passed} passed, {failed} failed, {len(SCENARIOS)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
