"""
Test suite runner for Quantitative Market Data & Historical Replay Infrastructure.
"""

import sys
import unittest

def main():
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print("TEST EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Tests Run:  {result.testsRun}")
    print(f"Failures:   {len(result.failures)}")
    print(f"Errors:     {len(result.errors)}")
    print(f"Skipped:    {len(result.skipped)}")
    print(f"Successful: {result.wasSuccessful()}")
    print("=" * 60)

    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    main()
