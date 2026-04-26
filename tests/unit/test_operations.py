"""
Test Suite per snapmark operations — logica pura.

Usa documenti DXF sintetici costruiti in memoria con ezdxf.
Non richiedono file su disco né l'algoritmo di posizionamento.

Lancia:
    python -m unittest tests/test_operations.py -v
"""

import unittest
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import ezdxf

from snapmark.operations.counter import CountFiles, CountHoles
from snapmark.operations.modify import SubstituteCircle, RemoveCircle, AddX, RemoveLayer
from snapmark.utils.helpers import find_circle_by_radius


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

FOLDER = r"C:\test"
FILE   = "test.dxf"


def make_doc():
    """Crea un documento DXF vuoto in memoria."""
    return ezdxf.new('R2010')


def add_circles(doc, specs):
    """
    Aggiunge cerchi al modelspace.
    specs: lista di (cx, cy, radius)
    """
    msp = doc.modelspace()
    for cx, cy, r in specs:
        msp.add_circle((cx, cy), r)
    return doc


def add_lines(doc, specs):
    """
    Aggiunge linee al modelspace.
    specs: lista di ((x1,y1), (x2,y2))
    """
    msp = doc.modelspace()
    for start, end in specs:
        msp.add_line(start, end)
    return doc


def count_circles(doc):
    """Conta i cerchi nel modelspace."""
    return len(list(doc.modelspace().query('CIRCLE')))


def get_circle_radii(doc):
    """Restituisce la lista dei raggi dei cerchi."""
    return sorted([e.dxf.radius for e in doc.modelspace().query('CIRCLE')])


# ═══════════════════════════════════════════════════════════
# CountFiles
# ═══════════════════════════════════════════════════════════

class TestCountFiles(unittest.TestCase):

    def test_001_increments_counter(self):
        """Execute incrementa il counter di 1."""
        op = CountFiles()
        doc = make_doc()
        op.execute(doc, FOLDER, FILE)
        print(f"\n[CountFiles] counter={op.counter}")
        self.assertEqual(op.counter, 1)

    def test_002_multiple_executions(self):
        """Esecuzioni multiple incrementano correttamente."""
        op = CountFiles()
        doc = make_doc()
        op.execute(doc, FOLDER, FILE)
        op.execute(doc, FOLDER, FILE)
        op.execute(doc, FOLDER, FILE)
        print(f"[CountFiles] 3x counter={op.counter}")
        self.assertEqual(op.counter, 3)

    def test_003_does_not_modify_file(self):
        """Execute restituisce False — non modifica il file."""
        op = CountFiles()
        doc = make_doc()
        result = op.execute(doc, FOLDER, FILE)
        self.assertFalse(result)

    def test_004_counter_starts_at_zero(self):
        """Il counter parte da zero."""
        op = CountFiles()
        self.assertEqual(op.counter, 0)


# ═══════════════════════════════════════════════════════════
# CountHoles
# ═══════════════════════════════════════════════════════════

class TestCountHoles(unittest.TestCase):

    def setUp(self):
        self.find_fn = find_circle_by_radius(min_diam=4, max_diam=20)

    def test_001_counts_circles_in_range(self):
        """Conta i cerchi nel range specificato."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5), (10, 0, 5), (20, 0, 5)])  # raggio 5 → diam 10, in range
        op = CountHoles(self.find_fn)
        op.execute(doc, FOLDER, FILE)
        print(f"\n[CountHoles] 3 cerchi r=5 → counter={op.counter}")
        self.assertEqual(op.counter, 3)

    def test_002_ignores_circles_outside_range(self):
        """Ignora cerchi fuori dal range."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 1), (10, 0, 50)])  # diam 2 e 100 — entrambi fuori range
        op = CountHoles(self.find_fn)
        op.execute(doc, FOLDER, FILE)
        print(f"[CountHoles] cerchi fuori range → counter={op.counter}")
        self.assertEqual(op.counter, 0)

    def test_003_mixed_circles(self):
        """Conta solo i cerchi nel range, ignora gli altri."""
        doc = make_doc()
        add_circles(doc, [
            (0, 0, 5),   # diam 10 → in range
            (10, 0, 1),  # diam 2 → fuori
            (20, 0, 7),  # diam 14 → in range
        ])
        op = CountHoles(self.find_fn)
        op.execute(doc, FOLDER, FILE)
        print(f"[CountHoles] mixed → counter={op.counter}")
        self.assertEqual(op.counter, 2)

    def test_004_does_not_modify_file(self):
        """Execute restituisce False."""
        doc = make_doc()
        op = CountHoles(self.find_fn)
        result = op.execute(doc, FOLDER, FILE)
        self.assertFalse(result)

    def test_005_accumulates_across_files(self):
        """Il counter si accumula su più file."""
        doc1 = make_doc()
        doc2 = make_doc()
        add_circles(doc1, [(0, 0, 5), (10, 0, 5)])
        add_circles(doc2, [(0, 0, 5)])
        op = CountHoles(self.find_fn)
        op.execute(doc1, FOLDER, "file1.dxf")
        op.execute(doc2, FOLDER, "file2.dxf")
        print(f"[CountHoles] 2+1 across files → counter={op.counter}")
        self.assertEqual(op.counter, 3)

    def test_006_empty_file(self):
        """File senza cerchi → counter rimane a zero."""
        doc = make_doc()
        op = CountHoles(self.find_fn)
        op.execute(doc, FOLDER, FILE)
        self.assertEqual(op.counter, 0)


# ═══════════════════════════════════════════════════════════
# SubstituteCircle
# ═══════════════════════════════════════════════════════════

class TestSubstituteCircle(unittest.TestCase):

    def setUp(self):
        self.find_fn = find_circle_by_radius(min_diam=4, max_diam=20)

    def test_001_replaces_radius(self):
        """I cerchi vengono sostituiti con il nuovo raggio."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5), (10, 0, 5)])
        op = SubstituteCircle(self.find_fn, new_radius=3)
        op.execute(doc, FOLDER, FILE)
        radii = get_circle_radii(doc)
        print(f"\n[SubstituteCircle] radii after={radii}")
        self.assertEqual(radii, [3.0, 3.0])

    def test_002_replaces_diameter(self):
        """Accetta new_diameter e lo converte in raggio."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5)])
        op = SubstituteCircle(self.find_fn, new_diameter=6)
        op.execute(doc, FOLDER, FILE)
        radii = get_circle_radii(doc)
        print(f"[SubstituteCircle] new_diameter=6 → radii={radii}")
        self.assertEqual(radii, [3.0])

    def test_003_count_preserved(self):
        """Il numero di cerchi rimane uguale."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5), (10, 0, 5), (20, 0, 5)])
        op = SubstituteCircle(self.find_fn, new_radius=2)
        op.execute(doc, FOLDER, FILE)
        print(f"[SubstituteCircle] count={count_circles(doc)}")
        self.assertEqual(count_circles(doc), 3)

    def test_004_ignores_out_of_range(self):
        """I cerchi fuori range non vengono toccati."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5), (10, 0, 50)])  # solo il primo in range
        op = SubstituteCircle(self.find_fn, new_radius=2)
        op.execute(doc, FOLDER, FILE)
        radii = get_circle_radii(doc)
        print(f"[SubstituteCircle] with out-of-range → radii={radii}")
        self.assertIn(2.0, radii)
        self.assertIn(50.0, radii)

    def test_005_no_radius_or_diameter_raises(self):
        """Senza new_radius né new_diameter solleva ValueError."""
        with self.assertRaises(ValueError):
            SubstituteCircle(self.find_fn)

    def test_006_modifies_file(self):
        """Execute restituisce True — modifica il file."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5)])
        op = SubstituteCircle(self.find_fn, new_radius=2)
        result = op.execute(doc, FOLDER, FILE)
        self.assertTrue(result)


# ═══════════════════════════════════════════════════════════
# RemoveCircle
# ═══════════════════════════════════════════════════════════

class TestRemoveCircle(unittest.TestCase):

    def setUp(self):
        self.find_fn = find_circle_by_radius(min_diam=4, max_diam=20)

    def test_001_removes_circles_in_range(self):
        """Rimuove i cerchi nel range."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5), (10, 0, 5)])
        op = RemoveCircle(self.find_fn)
        op.execute(doc, FOLDER, FILE)
        print(f"\n[RemoveCircle] after removal count={count_circles(doc)}")
        self.assertEqual(count_circles(doc), 0)

    def test_002_preserves_out_of_range(self):
        """Preserva i cerchi fuori range."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5), (10, 0, 50)])
        op = RemoveCircle(self.find_fn)
        op.execute(doc, FOLDER, FILE)
        radii = get_circle_radii(doc)
        print(f"[RemoveCircle] preserved radii={radii}")
        self.assertEqual(radii, [50.0])

    def test_003_empty_file(self):
        """File senza cerchi — nessun crash."""
        doc = make_doc()
        op = RemoveCircle(self.find_fn)
        op.execute(doc, FOLDER, FILE)
        self.assertEqual(count_circles(doc), 0)

    def test_004_modifies_file(self):
        """Execute restituisce True."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5)])
        op = RemoveCircle(self.find_fn)
        result = op.execute(doc, FOLDER, FILE)
        self.assertTrue(result)


# ═══════════════════════════════════════════════════════════
# AddX
# ═══════════════════════════════════════════════════════════

class TestAddX(unittest.TestCase):

    def setUp(self):
        self.find_fn = find_circle_by_radius(min_diam=4, max_diam=20)

    def test_001_removes_circles_by_default(self):
        """Con delete_hole=True (default) i cerchi vengono rimossi."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5), (10, 0, 5)])
        op = AddX(self.find_fn, delete_hole=True)
        op.execute(doc, FOLDER, FILE)
        print(f"\n[AddX] circles after={count_circles(doc)}")
        self.assertEqual(count_circles(doc), 0)

    def test_002_preserves_circles_if_delete_false(self):
        """Con delete_hole=False i cerchi rimangono."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5), (10, 0, 5)])
        op = AddX(self.find_fn, delete_hole=False)
        op.execute(doc, FOLDER, FILE)
        print(f"[AddX] circles preserved={count_circles(doc)}")
        self.assertEqual(count_circles(doc), 2)

    def test_003_adds_lines(self):
        """Aggiunge linee al modelspace (le X sono fatte di linee)."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5)])
        lines_before = len(list(doc.modelspace().query('LINE')))
        op = AddX(self.find_fn)
        op.execute(doc, FOLDER, FILE)
        lines_after = len(list(doc.modelspace().query('LINE')))
        print(f"[AddX] lines before={lines_before} after={lines_after}")
        self.assertGreater(lines_after, lines_before)

    def test_004_modifies_file(self):
        """Execute restituisce True."""
        doc = make_doc()
        add_circles(doc, [(0, 0, 5)])
        op = AddX(self.find_fn)
        result = op.execute(doc, FOLDER, FILE)
        self.assertTrue(result)


# ═══════════════════════════════════════════════════════════
# RemoveLayer
# ═══════════════════════════════════════════════════════════

class TestRemoveLayer(unittest.TestCase):

    def test_001_removes_entities_on_layer(self):
        """Le entità sul layer specificato vengono rimosse."""
        doc = make_doc()
        msp = doc.modelspace()
        msp.add_line((0, 0), (10, 0), dxfattribs={'layer': 'MARK'})
        msp.add_line((0, 0), (10, 0), dxfattribs={'layer': 'MARK'})
        msp.add_line((0, 0), (10, 0), dxfattribs={'layer': '0'})

        op = RemoveLayer('MARK')
        op.execute(doc, FOLDER, FILE)

        lines = list(msp.query('LINE'))
        layers = [l.dxf.layer for l in lines]
        print(f"\n[RemoveLayer] remaining layers={layers}")
        self.assertNotIn('MARK', layers)

    def test_002_preserves_other_layers(self):
        """Le entità su altri layer vengono preservate."""
        doc = make_doc()
        msp = doc.modelspace()
        msp.add_line((0, 0), (10, 0), dxfattribs={'layer': 'MARK'})
        msp.add_line((0, 0), (10, 0), dxfattribs={'layer': '0'})

        op = RemoveLayer('MARK')
        op.execute(doc, FOLDER, FILE)

        lines = list(msp.query('LINE'))
        print(f"[RemoveLayer] remaining count={len(lines)}")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].dxf.layer, '0')

    def test_003_empty_layer_no_crash(self):
        """Layer inesistente o vuoto non causa crash."""
        doc = make_doc()
        op = RemoveLayer('NONEXISTENT')
        op.execute(doc, FOLDER, FILE)  # non deve sollevare eccezioni

    def test_004_modifies_file(self):
        """Execute restituisce True."""
        doc = make_doc()
        op = RemoveLayer('MARK')
        result = op.execute(doc, FOLDER, FILE)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
