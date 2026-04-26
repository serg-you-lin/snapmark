"""
Test di integrazione per AddText.execute()

Pattern: DXF sintetico → execute() → verifica entità nel DXF prodotto.
I bug che sfuggono ai test unitari vivono tra "trovata posizione" e 
"scritto nel file" — qui li catturiamo.

Lancia:
    python -m unittest tests/integration/test_add_text.py -v
"""

import unittest
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import ezdxf
import snapmark.mark_algorithm as ma
from snapmark.operations.placement import AddText  
from snapmark.mark_algorithm.segmenter import comp_segs_and_limits


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def make_rect_doc(width=200, height=100):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    pts = [(0, 0), (width, 0), (width, height), (0, height)]
    for i in range(4):
        msp.add_line(pts[i], pts[(i + 1) % 4])
    return doc


def make_text_sequence(lines):
    """
    Stub minimo di ComposedText: get_lines() torna sempre le righe fisse.
    Isola AddText dai dettagli di TextBuilder.
    """
    class _FakeComposedText:
        def get_lines(self, folder, file_name):
            return lines
        def __repr__(self):
            return f"FakeComposedText({lines})"
    return _FakeComposedText()


def run_execute(doc, lines, **kwargs):
    """Chiama AddText.execute() con parametri standard e torna l'op."""
    params = {
        "text_sequence": make_text_sequence(lines),
        "min_char": 5,
        "max_char": 20,
        "text_layer": "TEXT",
        "text_color": 30,
    }

    params.update(kwargs)  # ← qui override pulito

    op = AddText(**params)
    op.execute(doc, folder=Path('.'), file_name='test.dxf')
    return op


def get_mtext_entities(doc):
    msp = doc.modelspace()
    return list(msp.query('MTEXT'))


# ═══════════════════════════════════════════════════════════
# Entità prodotte nel DXF
# ═══════════════════════════════════════════════════════════

class TestAddTextDXFOutput(unittest.TestCase):


    def test_001_mtext_added_to_modelspace(self):
        """Una riga di testo → almeno un MTEXT nel modelspace."""
        doc = make_rect_doc(200, 100)
        run_execute(doc, ['HELLO'])
        entities = get_mtext_entities(doc)
        print(f"\n[AddText] MTEXT count={len(entities)}")
        self.assertGreater(len(entities), 0)

    def test_002_multiline_produces_one_mtext_per_line(self):
        """N righe → N entità MTEXT (una per riga)."""
        doc = make_rect_doc(200, 100)
        lines = ['ABC', 'DEF', 'GHI']
        run_execute(doc, lines)
        entities = get_mtext_entities(doc)
        print(f"[AddText] 3 righe → {len(entities)} MTEXT")
        self.assertEqual(len(entities), len(lines))

    def test_003_mtext_on_correct_layer(self):
        """Il layer delle entità MTEXT corrisponde a text_layer."""
        doc = make_rect_doc(200, 100)
        run_execute(doc, ['X'], text_layer='MY_LAYER')
        for e in get_mtext_entities(doc):
            self.assertEqual(e.dxf.layer, 'MY_LAYER')

    def test_004_mtext_has_correct_color(self):
        """Il colore delle entità MTEXT corrisponde a text_color."""
        doc = make_rect_doc(200, 100)
        run_execute(doc, ['X'], text_color=5)
        for e in get_mtext_entities(doc):
            self.assertEqual(e.dxf.color, 5)

    def test_005_mtext_char_height_equals_min_char(self):
        """char_height di ogni MTEXT == min_char."""
        doc = make_rect_doc(200, 100)
        run_execute(doc, ['X'], char_height=7)
        for e in get_mtext_entities(doc):
            self.assertAlmostEqual(e.dxf.char_height, 7)

    def test_006_mtext_position_inside_bounding_box(self):
        """La posizione di ogni MTEXT è dentro il bounding box del disegno."""
        doc = make_rect_doc(200, 100)
        run_execute(doc, ['TEST'])
        for e in get_mtext_entities(doc):
            x, y = e.dxf.insert.x, e.dxf.insert.y
            self.assertGreaterEqual(x, -1)
            self.assertLessEqual(x, 201)
            self.assertGreaterEqual(y, -1)
            self.assertLessEqual(y, 101)


# ═══════════════════════════════════════════════════════════
# text_position aggiornato dopo execute()
# ═══════════════════════════════════════════════════════════

class TestAddTextPosition(unittest.TestCase):


    def test_001_text_position_set_after_execute(self):
        """text_position non è None dopo un execute() riuscito."""
        doc = make_rect_doc(200, 100)
        op = run_execute(doc, ['HELLO'])
        print(f"\n[AddText] text_position={op.text_position}")
        self.assertIsNotNone(op.text_position)

    def test_002_text_position_is_tuple_of_two(self):
        """text_position è una tupla (x, y)."""
        doc = make_rect_doc(200, 100)
        op = run_execute(doc, ['HELLO'])
        self.assertIsInstance(op.text_position, tuple)
        self.assertEqual(len(op.text_position), 2)

    def test_003_text_position_none_if_no_space(self):
        """Rettangolo troppo piccolo → text_position rimane None."""
        doc = make_rect_doc(2, 2)
        op = run_execute(doc, ['LONGTEXT123'])
        print(f"[AddText] no space → text_position={op.text_position}")
        self.assertIsNone(op.text_position)

    def test_004_text_position_none_if_empty_lines(self):
        """get_lines() vuoto → text_position rimane None, nessun crash."""
        doc = make_rect_doc(200, 100)
        op = run_execute(doc, [])  # texts=[]
        self.assertIsNone(op.text_position)


# ═══════════════════════════════════════════════════════════
# Fallback e casi limite
# ═══════════════════════════════════════════════════════════

class TestAddTextEdgeCases(unittest.TestCase):


    def test_001_no_mtext_if_empty_lines(self):
        """get_lines() vuoto → nessun MTEXT aggiunto."""
        doc = make_rect_doc(200, 100)
        run_execute(doc, [])
        self.assertEqual(len(get_mtext_entities(doc)), 0)

    def test_002_no_mtext_if_no_space(self):
        """Nessuno spazio → nessun MTEXT aggiunto."""
        doc = make_rect_doc(2, 2)
        run_execute(doc, ['ABC'])
        self.assertEqual(len(get_mtext_entities(doc)), 0)

    def test_003_execute_returns_create_new(self):
        """execute() torna sempre self.create_new (contratto dell'operazione)."""
        doc = make_rect_doc(200, 100)
        op = AddText(text_sequence=make_text_sequence(['X']), min_char=5)
        result = op.execute(doc, folder=Path('.'), file_name='test.dxf')
        self.assertEqual(result, op.create_new)

    def test_004_debug_bbox_adds_entity(self):
        """Con text_bbbox=True viene aggiunta un'entità DEBUG_TEXTBOX."""
        doc = make_rect_doc(200, 100)
        run_execute(doc, ['HELLO'], text_bbbox=True)
        msp = doc.modelspace()
        debug_entities = [
            e for e in msp
            if hasattr(e.dxf, 'layer') and e.dxf.layer == 'DEBUG_TEXTBOX'
        ]
        print(f"[AddText] debug entities={len(debug_entities)}")
        self.assertGreater(len(debug_entities), 0)

    def test_005_multiline_y_spacing_increases(self):
        """Le righe multiple hanno y crescente (stacking verticale corretto)."""
        doc = make_rect_doc(200, 150)
        run_execute(doc, ['LINE1', 'LINE2', 'LINE3'], min_char=5)
        entities = get_mtext_entities(doc)
        if len(entities) < 2:
            self.skipTest("Nessuno spazio trovato")
        ys = sorted([e.dxf.insert.y for e in entities])
        # Le y devono essere tutte diverse (nessuna sovrapposizione)
        self.assertEqual(len(ys), len(set(round(y, 3) for y in ys)))


if __name__ == '__main__':
    unittest.main(verbosity=2)