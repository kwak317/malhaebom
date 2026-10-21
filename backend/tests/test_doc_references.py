from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_doc_references import check_document, check_repository


class DocumentationReferenceTests(unittest.TestCase):
    def test_maintained_documents_resolve(self) -> None:
        self.assertEqual(check_repository(), [])

    def test_detects_broken_relative_link_and_inline_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "README.md"
            doc.write_text(
                "[Missing](docs/missing.md) and `skills/missing.md`\n",
                encoding="utf-8",
            )
            self.assertEqual(len(check_document(doc, root, check_skills=True)), 2)

    def test_ignores_external_links_and_code_samples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "README.md"
            doc.write_text(
                "[External](https://example.com) [Anchor](#section)\n"
                "```md\n"
                "[Example](missing.md)\n"
                "```\n",
                encoding="utf-8",
            )
            self.assertEqual(check_document(doc, root, check_skills=True), [])

    def test_rejects_personal_workstation_paths_in_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "README.md"
            doc.write_text(
                "Do not use C:\\Users\\example\\project in team guidance.\n"
                "Or /home/example/project paths.\n"
                "```bash\n"
                "echo C:\\Users\\example\\project\n"
                "```\n",
                encoding="utf-8",
            )
            self.assertEqual(
                len(check_document(doc, root, check_personal_paths=True)),
                2,
            )


if __name__ == "__main__":
    unittest.main()
