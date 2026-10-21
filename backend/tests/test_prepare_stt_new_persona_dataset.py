import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.scripts import prepare_stt_new_persona_dataset as m
class TestOverwriteSafety(unittest.TestCase):
    def test_project_root_rejected_before_recursive_delete(self):
        with patch.object(m.shutil, "rmtree") as rmtree:
            with self.assertRaises(ValueError):
                m.build_audio_and_manifests({}, {}, m.PROJECT_ROOT, overwrite=True)
        rmtree.assert_not_called()
