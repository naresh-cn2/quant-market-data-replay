"""Integration tests for CLI subcommands."""

import os
import subprocess
import sys
import tempfile
import unittest


class TestCliWorkflows(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name

    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

    def _run_cli(self, args):
        cmd = [sys.executable, "-m", "src.cli.main"] + args
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        return res

    def test_cli_validate(self):
        csv_file = os.path.join(self.fixtures_dir, "sample_trades.csv")
        res = self._run_cli(["validate", "--file", csv_file])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Total Records Processed: 5", res.stdout)
        self.assertIn("Accepted Clean Events:   5", res.stdout)

    def test_cli_ingest_and_replay(self):
        csv_file = os.path.join(self.fixtures_dir, "sample_trades.csv")
        ingest_res = self._run_cli(["ingest", "--file", csv_file, "--db", self.temp_db])
        self.assertEqual(ingest_res.returncode, 0)
        self.assertIn("Ingestion Complete", ingest_res.stdout)

        replay_res = self._run_cli(["replay", "--db", self.temp_db, "--symbol", "AAPL"])
        self.assertEqual(replay_res.returncode, 0)
        self.assertIn("AAPL", replay_res.stdout)
        self.assertIn("150.25", replay_res.stdout)


if __name__ == "__main__":
    unittest.main()
