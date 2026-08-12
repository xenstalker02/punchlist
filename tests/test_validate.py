import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate.py"


class ValidatorIntegrationTests(unittest.TestCase):
    def copy_repo(self, destination: Path) -> Path:
        root = destination / "punchlist"
        shutil.copytree(
            REPO_ROOT,
            root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        return root

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_repository_passes_validation(self) -> None:
        result = self.run_validator(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("50 defects", result.stdout)

    def test_broken_entry_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            taxonomy_path = root / "taxonomy" / "behavior.json"
            entries = json.loads(taxonomy_path.read_text(encoding="utf-8"))
            entries[0].pop("example")
            entries[0]["refs"] = {"wcag": [], "other": []}
            taxonomy_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("example", result.stdout)
        self.assertIn("public-standard reference", result.stdout)

    def test_wrong_category_count_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            taxonomy_path = root / "taxonomy" / "content.json"
            entries = json.loads(taxonomy_path.read_text(encoding="utf-8"))
            taxonomy_path.write_text(json.dumps(entries[:-1], indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected 16 entries", result.stdout)

    def test_missing_internal_reference_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            readme_path = root / "README.md"
            readme_path.write_text(
                readme_path.read_text(encoding="utf-8")
                + "\nSee [`missing.json`](examples/missing.json).\n",
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("examples/missing.json", result.stdout)


if __name__ == "__main__":
    unittest.main()
