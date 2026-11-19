import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("scan_artifact", Path(__file__).resolve().parents[1] / "scripts/scan_artifact.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArchiveSafety(unittest.TestCase):
    def test_rejects_traversal_absolute_and_windows_paths(self):
        for name in ("../outside", "/outside", "dir/../../outside", "..\\outside"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / "package.zip"
                target = Path(temporary) / "extracted"
                with zipfile.ZipFile(source, "w") as archive:
                    archive.writestr(name, "bad")
                with self.assertRaises(ValueError):
                    module.extract_package(source, target)
                self.assertFalse(target.exists())

    def test_rejects_symbolic_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "package.zip"
            with zipfile.ZipFile(source, "w") as archive:
                entry = zipfile.ZipInfo("link")
                entry.external_attr = 0o120777 << 16
                archive.writestr(entry, "../../outside")
            with self.assertRaises(ValueError):
                module.extract_package(source, Path(temporary) / "target")

    def test_extracts_regular_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "package.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("app/main.py", "pass\n")
            target = Path(temporary) / "target"
            module.extract_package(source, target)
            self.assertEqual((target / "app/main.py").read_text(), "pass\n")
