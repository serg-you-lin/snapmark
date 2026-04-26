"""
Test Suite per snapmark.sequence.sequence_system

Test puri sui componenti della sequenza — non richiedono file DXF.

Lancia:
    python -m unittest tests/test_sequence.py -v
"""

import unittest
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from snapmark.sequence.sequence_system import (
    LiteralComponent,
    FileNameComponent,
    FolderNameComponent,
    FilePartComponent,
    CustomComponent,
    SequenceBuilder,
    ComposedSequence,
    from_file_name,
    from_splitted_text,
    from_literal,
)


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════

FOLDER = r"C:\Batches\LOT2024A\drawings"
FILE   = "PART_123_A_SP5_Q2.dxf"


# ═══════════════════════════════════════════════════════════
# LiteralComponent
# ═══════════════════════════════════════════════════════════

class TestLiteralComponent(unittest.TestCase):

    def test_001_returns_fixed_text(self):
        """Restituisce il testo fisso."""
        comp = LiteralComponent("REV1")
        print(f"\n[Literal] result={comp.extract(FOLDER, FILE)}")
        self.assertEqual(comp.extract(FOLDER, FILE), "REV1")

    def test_002_empty_string(self):
        """Gestisce stringa vuota."""
        comp = LiteralComponent("")
        self.assertEqual(comp.extract(FOLDER, FILE), "")

    def test_003_ignores_folder_and_file(self):
        """Il testo non dipende da folder o file."""
        comp = LiteralComponent("FIXED")
        self.assertEqual(comp.extract("qualsiasi", "cosa.dxf"), "FIXED")


# ═══════════════════════════════════════════════════════════
# FileNameComponent
# ═══════════════════════════════════════════════════════════

class TestFileNameComponent(unittest.TestCase):

    def test_001_returns_name_without_extension(self):
        """Restituisce il nome file senza estensione."""
        comp = FileNameComponent()
        print(f"\n[FileName] result={comp.extract(FOLDER, FILE)}")
        self.assertEqual(comp.extract(FOLDER, FILE), "PART_123_A_SP5_Q2")

    def test_002_trim_start(self):
        """Taglia i caratteri iniziali."""
        comp = FileNameComponent(trim_start=5)
        self.assertEqual(comp.extract(FOLDER, FILE), "123_A_SP5_Q2")

    def test_003_trim_end(self):
        """Taglia i caratteri finali."""
        comp = FileNameComponent(trim_end=3)
        self.assertEqual(comp.extract(FOLDER, FILE), "PART_123_A_SP5")

    def test_004_trim_both(self):
        """Taglia inizio e fine."""
        comp = FileNameComponent(trim_start=5, trim_end=3)
        self.assertEqual(comp.extract(FOLDER, FILE), "123_A_SP5")

    def test_005_trim_exceeds_length_returns_full(self):
        """Se trim supera la lunghezza, restituisce il nome completo."""
        comp = FileNameComponent(trim_start=100, trim_end=100)
        self.assertEqual(comp.extract(FOLDER, FILE), "PART_123_A_SP5_Q2")

    def test_006_negative_trim_raises(self):
        """Trim negativo solleva ValueError."""
        comp = FileNameComponent(trim_start=-1)
        with self.assertRaises(ValueError):
            comp.extract(FOLDER, FILE)


# ═══════════════════════════════════════════════════════════
# FolderNameComponent
# ═══════════════════════════════════════════════════════════

class TestFolderNameComponent(unittest.TestCase):

    def test_001_immediate_parent(self):
        """Restituisce la cartella immediata."""
        comp = FolderNameComponent()
        print(f"\n[FolderName] level=0 result={comp.extract(FOLDER, FILE)}")
        self.assertEqual(comp.extract(FOLDER, FILE), "drawings")

    def test_002_grandparent(self):
        """Restituisce la cartella nonno."""
        comp = FolderNameComponent(level=1)
        print(f"[FolderName] level=1 result={comp.extract(FOLDER, FILE)}")
        self.assertEqual(comp.extract(FOLDER, FILE), "LOT2024A")

    def test_003_great_grandparent(self):
        """Restituisce la cartella bisnonno."""
        comp = FolderNameComponent(level=2)
        self.assertEqual(comp.extract(FOLDER, FILE), "Batches")

    def test_004_num_chars(self):
        """Limita i caratteri restituiti."""
        comp = FolderNameComponent(num_chars=4, level=1)
        self.assertEqual(comp.extract(FOLDER, FILE), "LOT2")

    def test_005_level_too_deep_raises(self):
        """Level troppo profondo solleva ValueError."""
        comp = FolderNameComponent(level=99)
        with self.assertRaises(ValueError):
            comp.extract(FOLDER, FILE)


# ═══════════════════════════════════════════════════════════
# FilePartComponent
# ═══════════════════════════════════════════════════════════

class TestFilePartComponent(unittest.TestCase):

    def test_001_first_part(self):
        """Restituisce la prima parte."""
        comp = FilePartComponent(separator="_", part_index=0)
        print(f"\n[FilePart] part=0 result={comp.extract(FOLDER, FILE)}")
        self.assertEqual(comp.extract(FOLDER, FILE), "PART")

    def test_002_second_part(self):
        """Restituisce la seconda parte."""
        comp = FilePartComponent(separator="_", part_index=1)
        self.assertEqual(comp.extract(FOLDER, FILE), "123")

    def test_003_third_part(self):
        """Restituisce la terza parte."""
        comp = FilePartComponent(separator="_", part_index=2)
        self.assertEqual(comp.extract(FOLDER, FILE), "A")

    def test_004_trim_start(self):
        """Taglia i caratteri iniziali della parte."""
        comp = FilePartComponent(separator="_", part_index=3, trim_start=2)
        self.assertEqual(comp.extract(FOLDER, FILE), "5")

    def test_005_trim_end(self):
        """Taglia i caratteri finali della parte."""
        comp = FilePartComponent(separator="_", part_index=3, trim_end=1)
        self.assertEqual(comp.extract(FOLDER, FILE), "SP")

    def test_006_index_out_of_range_raises(self):
        """Index fuori range solleva ValueError."""
        comp = FilePartComponent(separator="_", part_index=99)
        with self.assertRaises(ValueError):
            comp.extract(FOLDER, FILE)

    def test_007_negative_trim_raises(self):
        """Trim negativo solleva ValueError."""
        comp = FilePartComponent(separator="_", part_index=0, trim_start=-1)
        with self.assertRaises(ValueError):
            comp.extract(FOLDER, FILE)

    def test_008_trim_exceeds_length_returns_full(self):
        """Se trim supera la lunghezza, restituisce la parte completa."""
        comp = FilePartComponent(separator="_", part_index=0, trim_start=100, trim_end=100)
        self.assertEqual(comp.extract(FOLDER, FILE), "PART")


# ═══════════════════════════════════════════════════════════
# CustomComponent
# ═══════════════════════════════════════════════════════════

class TestCustomComponent(unittest.TestCase):

    def test_001_custom_function(self):
        """Esegue la funzione custom."""
        comp = CustomComponent(lambda folder, f: f.upper())
        print(f"\n[Custom] result={comp.extract(FOLDER, FILE)}")
        self.assertEqual(comp.extract(FOLDER, FILE), FILE.upper())

    def test_002_receives_folder_and_file(self):
        """La funzione riceve folder e file_name corretti."""
        received = {}
        def capture(folder, file_name):
            received['folder'] = folder
            received['file_name'] = file_name
            return "ok"
        comp = CustomComponent(capture)
        comp.extract(FOLDER, FILE)
        self.assertEqual(received['folder'], FOLDER)
        self.assertEqual(received['file_name'], FILE)


# ═══════════════════════════════════════════════════════════
# SequenceBuilder + ComposedSequence
# ═══════════════════════════════════════════════════════════

class TestSequenceBuilder(unittest.TestCase):

    def test_001_file_name(self):
        """Builder con solo file_name."""
        seq = SequenceBuilder().file_name().build()
        print(f"\n[Builder] file_name={seq.get_sequence_text(FOLDER, FILE)}")
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "PART_123_A_SP5_Q2")

    def test_002_literal(self):
        """Builder con solo literal."""
        seq = SequenceBuilder().literal("MFG").build()
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "MFG")

    def test_003_file_part(self):
        """Builder con file_part."""
        seq = SequenceBuilder().file_part(separator="_", part_index=0).build()
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "PART")

    def test_004_folder(self):
        """Builder con folder."""
        seq = SequenceBuilder().folder().build()
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "DRAWINGS")

    def test_005_folder_level(self):
        """Builder con folder level=1."""
        seq = SequenceBuilder().folder(level=1).build()
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "LOT2024A")

    def test_006_composition(self):
        """Builder con più componenti."""
        seq = (SequenceBuilder()
               .literal("MFG")
               .file_part(separator="_", part_index=1)
               .build())
        print(f"[Builder] composition={seq.get_sequence_text(FOLDER, FILE)}")
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "MFG-123")

    def test_007_custom_separator(self):
        """Separatore personalizzato."""
        seq = (SequenceBuilder()
               .literal("A")
               .literal("B")
               .set_separator("_")
               .build())
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "A_B")

    def test_008_result_is_uppercase(self):
        """Il risultato è sempre uppercase."""
        seq = SequenceBuilder().literal("test").build()
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "TEST")

    def test_009_empty_parts_ignored(self):
        """Le parti vuote non aggiungono separatori."""
        seq = (SequenceBuilder()
               .literal("A")
               .custom(lambda f, n: "")
               .literal("B")
               .build())
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "A-B")

    def test_010_custom_component(self):
        """Builder con custom function."""
        seq = SequenceBuilder().custom(lambda folder, f: "CUSTOM").build()
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "CUSTOM")


# ═══════════════════════════════════════════════════════════
# Shortcuts
# ═══════════════════════════════════════════════════════════

class TestShortcuts(unittest.TestCase):

    def test_001_from_file_name(self):
        """from_file_name equivale a SequenceBuilder().file_name().build()."""
        seq = from_file_name()
        expected = SequenceBuilder().file_name().build()
        print(f"\n[Shortcut] from_file_name={seq.get_sequence_text(FOLDER, FILE)}")
        self.assertEqual(
            seq.get_sequence_text(FOLDER, FILE),
            expected.get_sequence_text(FOLDER, FILE)
        )

    def test_002_from_file_name_trim(self):
        """from_file_name con trim."""
        seq = from_file_name(trim_start=5)
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "123_A_SP5_Q2")

    def test_003_from_splitted_text(self):
        """from_splitted_text restituisce la parte corretta."""
        seq = from_splitted_text(separator="_", part_index=0)
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "PART")

    def test_004_from_literal(self):
        """from_literal restituisce il testo fisso."""
        seq = from_literal("FIXED")
        self.assertEqual(seq.get_sequence_text(FOLDER, FILE), "FIXED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
