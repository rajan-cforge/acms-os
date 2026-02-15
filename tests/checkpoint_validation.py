#!/usr/bin/env python3
"""Checkpoint validation for ACMS build."""

import subprocess
import sys
import os

def run_command(cmd, timeout=5):
    """Run command and return success status."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=isinstance(cmd, str)
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def validate_checkpoint_0():
    """Validate Phase 0: ACMS-Lite functional."""
    tests = {}

    print("\n" + "="*60)
    print("CHECKPOINT 0: ACMS-Lite Bootstrap")
    print("="*60)

    # Test 1: acms_lite.py exists
    tests['acms_lite_exists'] = os.path.exists('acms_lite.py')
    print(f"{'✅' if tests['acms_lite_exists'] else '❌'} acms_lite.py exists")

    # Test 2: Can execute
    success, _, _ = run_command(['python3', 'acms_lite.py', 'stats'])
    tests['executable'] = success
    print(f"{'✅' if tests['executable'] else '❌'} ACMS-Lite executable")

    # Test 3: Can store
    success, _, _ = run_command([
        'python3', 'acms_lite.py', 'store', 'Checkpoint test', '--tag', 'test'
    ])
    tests['store_works'] = success
    print(f"{'✅' if tests['store_works'] else '❌'} Store command works")

    # Test 4: Can query
    success, output, _ = run_command([
        'python3', 'acms_lite.py', 'query', 'Checkpoint test'
    ])
    tests['query_works'] = success and 'Checkpoint test' in output
    print(f"{'✅' if tests['query_works'] else '❌'} Query command works")

    # Test 5: Can list
    success, _, _ = run_command(['python3', 'acms_lite.py', 'list', '--limit', '5'])
    tests['list_works'] = success
    print(f"{'✅' if tests['list_works'] else '❌'} List command works")

    # Test 6: Stats works
    success, output, _ = run_command(['python3', 'acms_lite.py', 'stats'])
    tests['stats_works'] = success and 'Total:' in output
    print(f"{'✅' if tests['stats_works'] else '❌'} Stats command works")

    # Test 7: Sufficient memories stored
    if tests['stats_works']:
        success, output, _ = run_command(['python3', 'acms_lite.py', 'stats'])
        # Extract total from output
        try:
            total_line = [l for l in output.split('\n') if 'Total:' in l][0]
            total = int(total_line.split(':')[1].strip())
            tests['sufficient_memories'] = total >= 30
            print(f"{'✅' if tests['sufficient_memories'] else '❌'} Sufficient memories stored (found: {total}, need: 30+)")
        except:
            tests['sufficient_memories'] = False
            print("❌ Could not parse memory count")
    else:
        tests['sufficient_memories'] = False
        print("❌ Cannot check memory count (stats failed)")

    # Test 8: Key instruction docs present
    success, output, _ = run_command([
        'python3', 'acms_lite.py', 'list', '--tag', 'instruction_doc', '--limit', '10'
    ])
    tests['instruction_docs'] = success and output.count('#') >= 1
    print(f"{'✅' if tests['instruction_docs'] else '❌'} Instruction documents stored")

    # Test 9: Master plan stored
    success, output, _ = run_command([
        'python3', 'acms_lite.py', 'list', '--tag', 'master_plan', '--limit', '10'
    ])
    tests['master_plan'] = success and output.count('#') >= 7
    print(f"{'✅' if tests['master_plan'] else '❌'} Master plan stored (7 phases)")

    print("\n" + "="*60)
    passed = sum(tests.values())
    total = len(tests)
    print(f"RESULT: {passed}/{total} tests passed")
    print("="*60 + "\n")

    return all(tests.values()), tests

if __name__ == '__main__':
    checkpoint = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    if checkpoint == 0:
        passed, tests = validate_checkpoint_0()
        sys.exit(0 if passed else 1)
    else:
        print(f"Checkpoint {checkpoint} validation not yet implemented")
        sys.exit(1)
