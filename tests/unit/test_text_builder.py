"""
Test Suite per snapmark.sequence.sequence_system — TextBuilder

Test puri su TextBuilder e ComposedText — non richiedono file DXF.

Lancia:
    python -m unittest tests/test_text_builder.py -v
"""

import unittest
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from snapmark.sequence.sequence_system import (
    TextBuilder,
    ComposedText,
    StaticLine,
    DynamicLine,
)


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════

FOLDER = r"C:\Batches\LOT2024A\drawings"
FILE   = "PART_123_S235_SP5_Q2.dxf"


# ═══════════════════════════════════════════════════════════
# StaticLine
# ═══════════════════════════════════════════════════════════

class TestStaticLine(unittest.TestCase):

    def test_001_returns_fixed_text(self):
        """Restituisce il testo fisso."""
        line = StaticLine("REV:1")
        print(f"\n[StaticLine] result={line.resolve(FOLDER, FILE)}")
        self.assertEqual(line.resolve(FOLDER, FILE), "REV:1")

    def test_002_ignores_folder_and_file(self):
        """Non dipende da folder o file."""
        line = StaticLine("FIXED")
        self.assertEqual(line.resolve("qualsiasi", "cosa.dxf"), "FIXED")

    def test_003_empty_string(self):
        """Gestisce stringa vuota."""
        line = StaticLine("")
        self.assertEqual(line.resolve(FOLDER, FILE), "")


# ═══════════════════════════════════════════════════════════
# DynamicLine
# ═══════════════════════════════════════════════════════════

class TestDynamicLine(unittest.TestCase):

    def test_001_calls_function(self):
        """Chiama la funzione e restituisce il risultato."""
        line = DynamicLine(lambda folder, f: f"File:{f}")
        print(f"\n[DynamicLine] result={line.resolve(FOLDER, FILE)}")
        self.assertEqual(line.resolve(FOLDER, FILE), f"File:{FILE}")

    def test_002_receives_correct_args(self):
        """La funzione riceve folder e file_name corretti."""
        received = {}
        def capture(folder, file_name):
            received['folder'] = folder
            received['file_name'] = file_name
            return "ok"
        line = DynamicLine(capture)
        line.resolve(FOLDER, FILE)
        self.assertEqual(received['folder'], FOLDER)
        self.assertEqual(received['file_name'], FILE)

    def test_003_uses_folder(self):
        """La funzione può usare il folder."""
        import os
        line = DynamicLine(lambda folder, f: os.path.basename(folder))
        self.assertEqual(line.resolve(FOLDER, FILE), "drawings")


# ═══════════════════════════════════════════════════════════
# TextBuilder
# ═══════════════════════════════════════════════════════════

class TestTextBuilder(unittest.TestCase):

    def test_001_static_line(self):
        """Builder con una riga statica."""
        tb = TextBuilder().static("REV:1").build()
        print(f"\n[TextBuilder] static={tb.get_lines(FOLDER, FILE)}")
        self.assertEqual(tb.get_lines(FOLDER, FILE), ["REV:1"])

    def test_002_dynamic_line(self):
        """Builder con una riga dinamica."""
        tb = TextBuilder().line(lambda folder, f: f"File:{f}").build()
        result = tb.get_lines(FOLDER, FILE)
        print(f"[TextBuilder] dynamic={result}")
        self.assertEqual(result, [f"File:{FILE}"])

    def test_003_multiple_static(self):
        """Builder con più righe statiche."""
        tb = (TextBuilder()
              .static("Mat:S235")
              .static("Sp:5")
              .static("Q:2")
              .build())
        result = tb.get_lines(FOLDER, FILE)
        print(f"[TextBuilder] multiple static={result}")
        self.assertEqual(result, ["Mat:S235", "Sp:5", "Q:2"])

    def test_004_mixed_static_and_dynamic(self):
        """Builder con mix di righe statiche e dinamiche."""
        tb = (TextBuilder()
              .static("REV:1")
              .line(lambda folder, f: f"File:{f}")
              .build())
        result = tb.get_lines(FOLDER, FILE)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "REV:1")
        self.assertEqual(result[1], f"File:{FILE}")

    def test_005_order_preserved(self):
        """L'ordine delle righe è preservato."""
        tb = (TextBuilder()
              .static("A")
              .static("B")
              .static("C")
              .build())
        self.assertEqual(tb.get_lines(FOLDER, FILE), ["A", "B", "C"])

    def test_006_empty_builder_raises(self):
        """Builder senza righe solleva ValueError."""
        with self.assertRaises(ValueError):
            TextBuilder().build()

    def test_007_build_returns_composed_text(self):
        """build() restituisce un'istanza di ComposedText."""
        tb = TextBuilder().static("test").build()
        self.assertIsInstance(tb, ComposedText)

    def test_008_dynamic_with_filename_parsing(self):
        """Caso reale: parsing del filename."""
        import os
        def parse(name):
            base = os.path.splitext(name)[0]
            parts = base.split("_")
            return {
                "quantity": next((p[1:] for p in parts if p.startswith("Q")), None),
                "thickness": next((p[2:] for p in parts if p.startswith("SP")), None),
            }

        tb = (TextBuilder()
              .line(lambda folder, f: f"Sp:{parse(f)['thickness']}")
              .line(lambda folder, f: f"Q:{parse(f)['quantity']}")
              .build())

        result = tb.get_lines(FOLDER, FILE)
        print(f"[TextBuilder] parsed={result}")
        self.assertEqual(result, ["Sp:5", "Q:2"])

    def test_009_material_map_normalization(self):
        """Caso reale: normalizzazione materiale tramite mappa esterna."""
        import os
        material_map = {"S235": "FE-DECAPATO", "INOX": "X5CrNi18-10"}

        def parse_material(name):
            base = os.path.splitext(name)[0]
            parts = base.split("_")
            return next((p for p in parts if p in material_map), None)

        tb = (TextBuilder()
              .line(lambda folder, f: f"Mat:{material_map.get(parse_material(f), 'N/D')}")
              .build())

        result = tb.get_lines(FOLDER, FILE)
        print(f"[TextBuilder] normalized material={result}")
        self.assertEqual(result, ["Mat:FE-DECAPATO"])

    def test_010_get_lines_called_multiple_times(self):
        """get_lines può essere chiamato più volte con risultati coerenti."""
        tb = TextBuilder().static("stabile").build()
        self.assertEqual(tb.get_lines(FOLDER, FILE), tb.get_lines(FOLDER, FILE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
