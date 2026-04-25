

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