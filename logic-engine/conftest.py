import os
import pytest
from latency_helpers import LatencyLogger, LatencyRecorder


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="session")
def latency_logger():
    logger = LatencyLogger(os.path.join(BASE_DIR, "latency.csv"))
    yield logger
    logger.flush()


@pytest.fixture(scope="function")
def latency_recorder():
    return LatencyRecorder()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    print("\n" + "="*30)
    print("      TEST SAMMANFATTNING")
    print("="*30)

    passed = terminalreporter.stats.get('passed', [])
    failed = terminalreporter.stats.get('failed', [])
    skipped = terminalreporter.stats.get('skipped', [])

    print(f"{'Testnamn':<40} | {'Resultat':<10}")
    print("-" * 55)

    for test in passed:
        # Rensar bort filnamnet för att bara visa funktionen
        name = test.nodeid.split("::")[-1]
        print(f"{name:<40} | ✅ PASSED")

    for test in failed:
        name = test.nodeid.split("::")[-1]
        print(f"{name:<40} | ❌ FAILED")

    for test in skipped:
        name = test.nodeid.split("::")[-1]
        print(f"{name:<40} | SKIPPED")

    print("="*55)

    csv_path = os.path.join(BASE_DIR, "latency.csv")
    if os.path.exists(csv_path):
        print("\n" + "="*30)
        print("      LATENS (ms)")
        print("="*30)
        print(f"{'Test':<32} | {'dispatch→setpoint':<18} | {'setpoint→motion':<16} | {'total':<8}")
        print("-" * 90)
        import csv as _csv
        with open(csv_path) as f:
            for row in _csv.DictReader(f):
                print(f"{row['test']:<32} | "
                      f"{str(row['dispatch_to_setpoint_ms']):<18} | "
                      f"{str(row['setpoint_to_motion_ms']):<16} | "
                      f"{str(row['total_dispatch_to_motion_ms']):<8}")
        print("="*90)