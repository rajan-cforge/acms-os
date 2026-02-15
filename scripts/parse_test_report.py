#!/usr/bin/env python3
"""Parse test report and display human-readable summary"""

import json
import sys
from pathlib import Path

def parse_report(report_path: str = ".ai/test-results/latest.json"):
    """Parse and display test report"""

    try:
        with open(report_path) as f:
            report = json.load(f)
    except FileNotFoundError:
        print(f"❌ Test report not found: {report_path}")
        print("   Run: bash scripts/run_tests_with_report.sh")
        sys.exit(1)

    print("\n" + "="*60)
    print("ACMS TEST REPORT SUMMARY")
    print("="*60)

    # Summary
    summary = report.get('summary', {})
    print(f"\n📊 Overall Results:")
    print(f"  Total Tests: {summary.get('total', 0)}")
    print(f"  ✅ Passed: {summary.get('passed', 0)}")
    print(f"  ❌ Failed: {summary.get('failed', 0)}")
    print(f"  ⏭️  Skipped: {summary.get('skipped', 0)}")
    print(f"  ⏱️  Duration: {report.get('duration', 0):.2f}s")

    # Coverage
    try:
        with open(".ai/test-results/coverage.json") as cf:
            coverage = json.load(cf)
            total_coverage = coverage['totals']['percent_covered']
            print(f"\n📈 Coverage: {total_coverage:.1f}%")
    except:
        pass

    # Failed tests details
    if summary.get('failed', 0) > 0:
        print(f"\n❌ Failed Tests:")
        for test in report.get('tests', []):
            if test.get('outcome') == 'failed':
                print(f"  - {test.get('nodeid')}")
                if 'call' in test and 'longrepr' in test['call']:
                    print(f"    Error: {test['call']['longrepr'][:100]}...")

    # Slowest tests
    tests_by_duration = sorted(
        report.get('tests', []),
        key=lambda t: t.get('duration', 0),
        reverse=True
    )[:5]

    print(f"\n⏱️  Slowest Tests:")
    for test in tests_by_duration:
        duration = test.get('duration', 0)
        name = test.get('nodeid', 'Unknown').split('::')[-1]
        print(f"  - {name}: {duration:.2f}s")

    print("\n" + "="*60)
    print(f"Full report: .ai/test-results/latest.html")
    print("="*60 + "\n")

if __name__ == "__main__":
    report_path = sys.argv[1] if len(sys.argv) > 1 else ".ai/test-results/latest.json"
    parse_report(report_path)
