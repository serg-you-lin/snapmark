"""
Test di integrazione per snapmark.utils.backup_manager.BackupManager

Usa file temporanei su disco — testa il comportamento reale del filesystem.

Lancia:
    python -m unittest tests/integration/test_backup_system.py -v
"""

import unittest
from pathlib import Path
import sys
import tempfile
import os
import shutil

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import ezdxf
from snapmark.utils.backup_manager import BackupManager


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def write_dxf(path, marker="original"):
    """Scrive un DXF minimale con un testo identificativo nel layer."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0), dxfattribs={'layer': marker})
    doc.saveas(path)


def get_layers(path):
    """Legge i layer usati nel modelspace di un DXF."""
    doc = ezdxf.readfile(path)
    return {e.dxf.layer for e in doc.modelspace()}


# ═══════════════════════════════════════════════════════════
# create_backup
# ═══════════════════════════════════════════════════════════

class TestCreateBackup(unittest.TestCase):

    def test_001_creates_bak_file(self):
        """create_backup crea il file .dxf.bak."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)
            bak = path + ".bak"
            print(f"\n[create_backup] bak exists={os.path.exists(bak)}")
            self.assertTrue(os.path.exists(bak))

    def test_002_backup_content_matches_original(self):
        """Il contenuto del backup è identico all'originale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path, marker="original")
            BackupManager.create_backup(path)
            bak = path + ".bak"
            layers = get_layers(bak)
            print(f"[create_backup] bak layers={layers}")
            self.assertIn("original", layers)

    def test_003_does_not_overwrite_existing_backup(self):
        """Se il backup esiste già, non lo sovrascrive (force=False)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path, marker="original")
            BackupManager.create_backup(path)

            # Modifica il file originale
            write_dxf(path, marker="modified")
            BackupManager.create_backup(path, force=False)

            # Il backup deve ancora contenere "original"
            bak = path + ".bak"
            layers = get_layers(bak)
            print(f"[create_backup] no overwrite layers={layers}")
            self.assertIn("original", layers)
            self.assertNotIn("modified", layers)

    def test_004_force_overwrites_existing_backup(self):
        """Con force=True, il backup esistente viene sovrascritto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path, marker="original")
            BackupManager.create_backup(path)

            write_dxf(path, marker="modified")
            BackupManager.create_backup(path, force=True)

            bak = path + ".bak"
            layers = get_layers(bak)
            print(f"[create_backup] force overwrite layers={layers}")
            self.assertIn("modified", layers)

    def test_005_returns_true_if_created(self):
        """Restituisce True se il backup viene creato."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            result = BackupManager.create_backup(path)
            self.assertTrue(result)

    def test_006_returns_false_if_already_exists(self):
        """Restituisce False se il backup esiste già."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)
            result = BackupManager.create_backup(path)
            self.assertFalse(result)

    def test_007_skips_non_dxf_files(self):
        """Ignora file non DXF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "note.txt")
            with open(path, 'w') as f:
                f.write("testo")
            result = BackupManager.create_backup(path)
            self.assertFalse(result)
            self.assertFalse(os.path.exists(path + ".bak"))


# ═══════════════════════════════════════════════════════════
# restore_backup
# ═══════════════════════════════════════════════════════════

class TestRestoreBackup(unittest.TestCase):

    def test_001_restores_original_content(self):
        """restore_backup ripristina il contenuto originale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path, marker="original")
            BackupManager.create_backup(path)

            # Modifica il file
            write_dxf(path, marker="modified")
            self.assertIn("modified", get_layers(path))

            # Ripristina
            BackupManager.restore_backup(path)
            layers = get_layers(path)
            print(f"\n[restore_backup] restored layers={layers}")
            self.assertIn("original", layers)
            self.assertNotIn("modified", layers)

    def test_002_backup_still_exists_after_restore(self):
        """Il backup rimane dopo il ripristino (delete_backup=False)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)
            BackupManager.restore_backup(path, delete_backup=False)
            bak = path + ".bak"
            print(f"[restore_backup] bak still exists={os.path.exists(bak)}")
            self.assertTrue(os.path.exists(bak))

    def test_003_backup_deleted_if_requested(self):
        """Il backup viene eliminato se delete_backup=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)
            BackupManager.restore_backup(path, delete_backup=True)
            bak = path + ".bak"
            print(f"[restore_backup] bak deleted={not os.path.exists(bak)}")
            self.assertFalse(os.path.exists(bak))

    def test_004_returns_false_if_no_backup(self):
        """Restituisce False se non esiste backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            result = BackupManager.restore_backup(path)
            print(f"[restore_backup] no backup result={result}")
            self.assertFalse(result)

    def test_005_returns_true_if_restored(self):
        """Restituisce True se il ripristino va a buon fine."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)
            result = BackupManager.restore_backup(path)
            self.assertTrue(result)


# ═══════════════════════════════════════════════════════════
# has_backup
# ═══════════════════════════════════════════════════════════

class TestHasBackup(unittest.TestCase):

    def test_001_true_if_backup_exists(self):
        """True se il backup esiste."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)
            print(f"\n[has_backup] after create={BackupManager.has_backup(path)}")
            self.assertTrue(BackupManager.has_backup(path))

    def test_002_false_if_no_backup(self):
        """False se il backup non esiste."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            self.assertFalse(BackupManager.has_backup(path))

    def test_003_false_after_delete(self):
        """False dopo che il backup è stato eliminato."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)
            os.remove(path + ".bak")
            self.assertFalse(BackupManager.has_backup(path))


# ═══════════════════════════════════════════════════════════
# ensure_original
# ═══════════════════════════════════════════════════════════

class TestEnsureOriginal(unittest.TestCase):

    def test_001_creates_backup_if_none_exists(self):
        """Se non esiste backup, lo crea."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.ensure_original(path)
            print(f"\n[ensure_original] backup created={BackupManager.has_backup(path)}")
            self.assertTrue(BackupManager.has_backup(path))

    def test_002_restores_from_backup_if_exists(self):
        """Se il backup esiste, ripristina l'originale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path, marker="original")
            BackupManager.create_backup(path)

            # Simula una modifica
            write_dxf(path, marker="modified")
            self.assertIn("modified", get_layers(path))

            # ensure_original deve ripristinare
            BackupManager.ensure_original(path)
            layers = get_layers(path)
            print(f"[ensure_original] restored layers={layers}")
            self.assertIn("original", layers)
            self.assertNotIn("modified", layers)

    def test_003_backup_preserved_after_ensure(self):
        """Il backup non viene eliminato dopo ensure_original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)
            write_dxf(path, marker="modified")
            BackupManager.ensure_original(path)
            print(f"[ensure_original] backup still exists={BackupManager.has_backup(path)}")
            self.assertTrue(BackupManager.has_backup(path))

    def test_004_idempotent(self):
        """Chiamate multiple producono lo stesso risultato."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path, marker="original")

            BackupManager.ensure_original(path)
            BackupManager.ensure_original(path)
            BackupManager.ensure_original(path)

            layers = get_layers(path)
            print(f"[ensure_original] idempotent layers={layers}")
            self.assertIn("original", layers)


# ═══════════════════════════════════════════════════════════
# restore_all_in_folder
# ═══════════════════════════════════════════════════════════

class TestRestoreAllInFolder(unittest.TestCase):

    def test_001_restores_all_files_in_folder(self):
        """Ripristina tutti i file nella cartella."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["a.dxf", "b.dxf", "c.dxf"]:
                path = os.path.join(tmpdir, name)
                write_dxf(path, marker="original")
                BackupManager.create_backup(path)
                write_dxf(path, marker="modified")

            result = BackupManager.restore_all_in_folder(tmpdir)
            print(f"\n[restore_all] restored={result['restored']}")
            self.assertEqual(result['restored'], 3)

            for name in ["a.dxf", "b.dxf", "c.dxf"]:
                path = os.path.join(tmpdir, name)
                self.assertIn("original", get_layers(path))

    def test_002_returns_correct_stats(self):
        """Restituisce le statistiche corrette."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "a.dxf")
            write_dxf(path)
            BackupManager.create_backup(path)

            result = BackupManager.restore_all_in_folder(tmpdir)
            self.assertIn('restored', result)
            self.assertIn('not_found', result)
            self.assertIn('folder', result)

    def test_003_single_file_mode(self):
        """Funziona anche su un singolo file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.dxf")
            write_dxf(path, marker="original")
            BackupManager.create_backup(path)
            write_dxf(path, marker="modified")

            result = BackupManager.restore_all_in_folder(path)
            print(f"[restore_all] single file restored={result['restored']}")
            self.assertEqual(result['restored'], 1)
            self.assertIn("original", get_layers(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
