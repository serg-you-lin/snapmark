"""
Test di integrazione per snapmark.core.IterationManager

Usa cartelle temporanee e DXF sintetici — non richiedono file reali.
Testa il pipeline end-to-end: loop su file, salvataggio, gestione errori.

Lancia:
    python -m unittest tests/integration/test_iteration_manager.py -v
"""

import unittest
from pathlib import Path
import sys
import tempfile
import os

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import ezdxf

import snapmark as sm
from snapmark.core import IterationManager
from snapmark.operations.counter import CountFiles
from snapmark.utils.helpers import find_circle_by_radius


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def write_rectangle_dxf(path, width=100, height=60):
    """Scrive un DXF con un rettangolo semplice su disco."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    pts = [(0,0), (width,0), (width,height), (0,height), (0,0)]
    for i in range(4):
        msp.add_line(pts[i], pts[i+1])
    doc.saveas(path)


def write_circle_dxf(path, radius=5):
    """Scrive un DXF con un cerchio su disco."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    msp.add_circle((50, 30), radius)
    msp.add_line((0, 0), (100, 0))
    msp.add_line((100, 0), (100, 60))
    msp.add_line((100, 60), (0, 60))
    msp.add_line((0, 60), (0, 0))
    doc.saveas(path)


def count_entities_on_layer(path, layer):
    """Legge un DXF da disco e conta le entità su un layer."""
    doc = ezdxf.readfile(path)
    return len([e for e in doc.modelspace() if e.dxf.layer == layer])


# ═══════════════════════════════════════════════════════════
# IterationManager — comportamento base
# ═══════════════════════════════════════════════════════════

class TestIterationManagerBase(unittest.TestCase):

    def test_001_processes_all_dxf_files(self):
        """Il manager processa tutti i DXF nella cartella."""
        with tempfile.TemporaryDirectory() as tmpdir:
            write_rectangle_dxf(os.path.join(tmpdir, "a.dxf"))
            write_rectangle_dxf(os.path.join(tmpdir, "b.dxf"))
            write_rectangle_dxf(os.path.join(tmpdir, "c.dxf"))

            counter = CountFiles()
            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(counter)
            stats = manager.execute()

            print(f"\n[IterationManager] processed={stats['processed']} counter={counter.counter}")
            self.assertEqual(stats['processed'], 3)
            self.assertEqual(counter.counter, 3)

    def test_002_ignores_non_dxf_files(self):
        """Il manager ignora i file non DXF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            write_rectangle_dxf(os.path.join(tmpdir, "a.dxf"))
            open(os.path.join(tmpdir, "note.txt"), 'w').close()
            open(os.path.join(tmpdir, "data.csv"), 'w').close()

            counter = CountFiles()
            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(counter)
            manager.execute()

            print(f"[IterationManager] ignores non-dxf counter={counter.counter}")
            self.assertEqual(counter.counter, 1)

    def test_003_empty_folder_returns_zero(self):
        """Cartella vuota — nessun file processato."""
        with tempfile.TemporaryDirectory() as tmpdir:
            counter = CountFiles()
            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(counter)
            stats = manager.execute()

            print(f"[IterationManager] empty folder processed={stats['processed']}")
            self.assertEqual(stats['processed'], 0)

    def test_004_no_operations_returns_zero(self):
        """Nessuna operazione aggiunta — nessun file processato."""
        with tempfile.TemporaryDirectory() as tmpdir:
            write_rectangle_dxf(os.path.join(tmpdir, "a.dxf"))
            manager = IterationManager(tmpdir, use_backup_system=False)
            stats = manager.execute()

            print(f"[IterationManager] no ops processed={stats['processed']}")
            self.assertEqual(stats['processed'], 0)

    def test_005_multiple_operations_applied_in_order(self):
        """Più operazioni vengono applicate nell'ordine in cui sono state aggiunte."""
        with tempfile.TemporaryDirectory() as tmpdir:
            write_rectangle_dxf(os.path.join(tmpdir, "a.dxf"))

            order = []

            class OpA(sm.operations.basic_operations.Operation):
                def execute(self, doc, folder, file_name):
                    order.append('A')
                    return False
                def message(self, file_name): pass

            class OpB(sm.operations.basic_operations.Operation):
                def execute(self, doc, folder, file_name):
                    order.append('B')
                    return False
                def message(self, file_name): pass

            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(OpA(), OpB())
            manager.execute()

            print(f"[IterationManager] order={order}")
            self.assertEqual(order, ['A', 'B'])


# ═══════════════════════════════════════════════════════════
# IterationManager — salvataggio file
# ═══════════════════════════════════════════════════════════

class TestIterationManagerSave(unittest.TestCase):

    def test_001_saves_file_if_operation_returns_true(self):
        """Il file viene salvato se almeno una operation restituisce True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "a.dxf")
            write_rectangle_dxf(filepath)

            seq = sm.SequenceBuilder().literal("TEST").build()
            mark_op = sm.AddMark(seq, scale_factor=50, min_height=5, max_height=15)

            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(mark_op)
            stats = manager.execute()

            print(f"\n[IterationManager save] modified={stats['modified']}")
            self.assertEqual(stats['modified'], 1)

            # Verifica che la marcatura sia stata scritta su disco
            n = count_entities_on_layer(filepath, 'MARK')
            print(f"[IterationManager save] MARK entities on disk={n}")
            self.assertGreater(n, 0)

    def test_002_does_not_save_if_no_operation_modifies(self):
        """Il file non viene salvato se nessuna operation restituisce True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "a.dxf")
            write_rectangle_dxf(filepath)
            mtime_before = os.path.getmtime(filepath)

            import time
            time.sleep(0.05)

            counter = CountFiles()
            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(counter)
            manager.execute()

            mtime_after = os.path.getmtime(filepath)
            print(f"[IterationManager save] mtime changed={mtime_before != mtime_after}")
            self.assertEqual(mtime_before, mtime_after)


# ═══════════════════════════════════════════════════════════
# IterationManager — pipeline AddMark + AddText
# ═══════════════════════════════════════════════════════════

class TestIterationManagerPipeline(unittest.TestCase):

    def test_001_mark_and_text_pipeline(self):
        """Pipeline AddMark + AddText scrive entrambe le operazioni su disco."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "PART_S235_SP5_Q2.dxf")
            write_rectangle_dxf(filepath)

            seq = sm.SequenceBuilder().literal("TEST").build()
            mark_op = sm.AddMark(seq, scale_factor=50, min_height=5, max_height=15)

            text_op = sm.AddText(
                sm.TextBuilder().static("Mat:S235").static("Sp:5").build(),
                min_char=3,
                max_char=8,
            )

            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(mark_op, text_op)
            stats = manager.execute()

            print(f"\n[Pipeline] modified={stats['modified']}")
            self.assertEqual(stats['modified'], 1)

            mark_count = count_entities_on_layer(filepath, 'MARK')
            mtext_count = len(list(
                ezdxf.readfile(filepath).modelspace().query('MTEXT')
            ))
            print(f"[Pipeline] MARK={mark_count} MTEXT={mtext_count}")
            self.assertGreater(mark_count, 0)
            self.assertGreater(mtext_count, 0)

    def test_002_multiple_files_pipeline(self):
        """Pipeline applicata a più file — tutti modificati."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["a.dxf", "b.dxf", "c.dxf"]:
                write_rectangle_dxf(os.path.join(tmpdir, name))

            seq = sm.SequenceBuilder().literal("X").build()
            mark_op = sm.AddMark(seq, scale_factor=50, min_height=5, max_height=15)

            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(mark_op)
            stats = manager.execute()

            print(f"[Pipeline] multi-file modified={stats['modified']}")
            self.assertEqual(stats['modified'], 3)

            for name in ["a.dxf", "b.dxf", "c.dxf"]:
                n = count_entities_on_layer(os.path.join(tmpdir, name), 'MARK')
                self.assertGreater(n, 0)


# ═══════════════════════════════════════════════════════════
# IterationManager — gestione errori
# ═══════════════════════════════════════════════════════════

class TestIterationManagerErrors(unittest.TestCase):

    def test_001_invalid_dxf_goes_to_errors(self):
        """Un file DXF corrotto viene registrato negli errori."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = os.path.join(tmpdir, "bad.dxf")
            with open(bad_path, 'w') as f:
                f.write("questo non è un dxf valido")

            counter = CountFiles()
            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(counter)
            stats = manager.execute()

            print(f"\n[IterationManager errors] errors={stats['errors']}")
            self.assertEqual(len(stats['errors']), 1)

    def test_002_error_in_one_file_does_not_stop_others(self):
        """Un errore su un file non blocca gli altri."""
        with tempfile.TemporaryDirectory() as tmpdir:
            write_rectangle_dxf(os.path.join(tmpdir, "good.dxf"))
            with open(os.path.join(tmpdir, "bad.dxf"), 'w') as f:
                f.write("non è un dxf")

            counter = CountFiles()
            manager = IterationManager(tmpdir, use_backup_system=False)
            manager.add_operation(counter)
            stats = manager.execute()

            print(f"[IterationManager errors] processed={stats['processed']} errors={len(stats['errors'])}")
            self.assertEqual(stats['processed'], 1)
            self.assertEqual(len(stats['errors']), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
