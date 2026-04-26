"""
Test Suite per snapmark placement operations — AddMark, AddText, Aligner.

Usa documenti DXF sintetici costruiti in memoria con ezdxf.
Non richiedono file su disco.

Lancia:
    python -m unittest tests/test_placement_operations.py -v
"""

import unittest
from pathlib import Path
import sys
import math

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import ezdxf

import snapmark as sm
from snapmark.operations.aligner import Aligner


# ═══════════════════════════════════════════════════════════
# HELPERS / FIXTURES
# ═══════════════════════════════════════════════════════════

FOLDER = r"C:\test"
FILE   = "test.dxf"


def make_rectangle(width=100, height=60, layer='0'):
    """
    Crea un doc DXF con un rettangolo semplice.
    Base per AddMark e AddText — spazio interno garantito.
    """
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    pts = [(0,0), (width,0), (width,height), (0,height), (0,0)]
    for i in range(4):
        msp.add_line(pts[i], pts[i+1], dxfattribs={'layer': layer})
    return doc


def make_inclined_rectangle(angle_deg=30, width=100, height=60):
    """
    Crea un doc DXF con un rettangolo inclinato.
    Usato per Aligner — la linea più lunga non è orizzontale.
    """
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    angle = math.radians(angle_deg)

    def rot(x, y):
        return (x * math.cos(angle) - y * math.sin(angle),
                x * math.sin(angle) + y * math.cos(angle))

    corners = [(0,0), (width,0), (width,height), (0,height)]
    rotated = [rot(x, y) for x, y in corners]
    rotated.append(rotated[0])

    for i in range(4):
        msp.add_line(rotated[i], rotated[i+1])

    return doc


def make_narrow_rectangle(width=8, height=60):
    """
    Crea un doc DXF con un rettangolo stretto.
    Forza il fallback di find_position — la sequenza non ci sta alla prima.
    """
    return make_rectangle(width=width, height=height)


def get_entities_on_layer(doc, layer):
    """Restituisce tutte le entità su un dato layer."""
    return [e for e in doc.modelspace() if e.dxf.layer == layer]


def get_longest_line_angle(doc):
    """
    Restituisce l'angolo in gradi della linea più lunga nel modelspace.
    Usato per verificare che Aligner abbia allineato correttamente.
    """
    lines = list(doc.modelspace().query('LINE'))
    if not lines:
        return None

    def length(l):
        dx = l.dxf.end.x - l.dxf.start.x
        dy = l.dxf.end.y - l.dxf.start.y
        return math.sqrt(dx*dx + dy*dy)

    def angle_deg(l):
        dx = l.dxf.end.x - l.dxf.start.x
        dy = l.dxf.end.y - l.dxf.start.y
        return math.degrees(math.atan2(dy, dx))

    longest = max(lines, key=length)
    return abs(angle_deg(longest))


# ═══════════════════════════════════════════════════════════
# AddMark
# ═══════════════════════════════════════════════════════════

class TestAddMark(unittest.TestCase):

    def _make_op(self, **kwargs):
        defaults = dict(
            scale_factor=50,
            min_char=5,
            max_char=15,
            mark_layer='MARK',
        )
        defaults.update(kwargs)
        seq = sm.SequenceBuilder().literal("TEST").build()
        return sm.AddMark(seq, **defaults)

    def test_001_adds_entities_to_mark_layer(self):
        """AddMark aggiunge entità nel layer MARK."""
        doc = make_rectangle()
        op = self._make_op()
        op.execute(doc, FOLDER, FILE)
        entities = get_entities_on_layer(doc, 'MARK')
        print(f"\n[AddMark] entities on MARK={len(entities)}")
        self.assertGreater(len(entities), 0)

    def test_002_returns_true(self):
        """Execute restituisce True — modifica il file."""
        doc = make_rectangle()
        op = self._make_op()
        result = op.execute(doc, FOLDER, FILE)
        self.assertTrue(result)

    def test_003_sequence_position_set(self):
        """sequence_position viene popolato dopo execute."""
        doc = make_rectangle()
        op = self._make_op()
        op.execute(doc, FOLDER, FILE)
        print(f"[AddMark] sequence_position={op.sequence_position.sequence}")
        self.assertGreater(len(op.sequence_position.sequence), 0)

    def test_004_respects_excluded_layers(self):
        """Le entità su excluded_layers non vengono considerate per il posizionamento."""
        doc = make_rectangle(layer='EXCLUDED')
        # Aggiunge un secondo rettangolo su layer normale
        msp = doc.modelspace()
        pts = [(0,0), (100,0), (100,60), (0,60), (0,0)]
        for i in range(4):
            msp.add_line(pts[i], pts[i+1], dxfattribs={'layer': '0'})

        op = self._make_op(excluded_layers=['EXCLUDED'])
        result = op.execute(doc, FOLDER, FILE)
        self.assertTrue(result)

    def test_005_empty_sequence_no_crash(self):
        """Sequenza con solo literal funziona senza crash."""
        doc = make_rectangle()
        seq = sm.SequenceBuilder().literal("123").build()
        op = sm.AddMark(seq, scale_factor=50, min_char=5, max_char=15)
        op.execute(doc, FOLDER, FILE)  # non deve sollevare eccezioni


# ═══════════════════════════════════════════════════════════
# AddText
# ═══════════════════════════════════════════════════════════

class TestAddText(unittest.TestCase):

    def _make_op(self, **kwargs):
        defaults = dict(
            min_char=3,
            max_char=8,
            text_layer='TEXT',
            text_color=3,
        )
        defaults.update(kwargs)
        text_seq = (sm.TextBuilder()
                    .static("Mat:S235")
                    .static("Sp:5")
                    .static("Q:2")
                    .build())
        return sm.AddText(text_seq, **defaults)

    def test_001_adds_mtext_to_text_layer(self):
        """AddText aggiunge MTEXT nel layer TEXT."""
        doc = make_rectangle()
        op = self._make_op()
        op.execute(doc, FOLDER, FILE)
        mtexts = list(doc.modelspace().query('MTEXT'))
        print(f"\n[AddText] MTEXT count={len(mtexts)}")
        self.assertGreater(len(mtexts), 0)

    def test_002_correct_number_of_lines(self):
        """Aggiunge tante MTEXT quante sono le righe."""
        doc = make_rectangle()
        op = self._make_op()
        op.execute(doc, FOLDER, FILE)
        mtexts = list(doc.modelspace().query('MTEXT'))
        print(f"[AddText] lines expected=3 got={len(mtexts)}")
        self.assertEqual(len(mtexts), 3)

    def test_003_returns_true(self):
        """Execute restituisce True."""
        doc = make_rectangle()
        op = self._make_op()
        result = op.execute(doc, FOLDER, FILE)
        self.assertTrue(result)

    def test_004_text_position_set(self):
        """text_position viene popolato dopo execute."""
        doc = make_rectangle()
        op = self._make_op()
        op.execute(doc, FOLDER, FILE)
        print(f"[AddText] text_position={op.text_position}")
        self.assertIsNotNone(op.text_position)

    def test_005_dynamic_lines_resolved(self):
        """Le righe dinamiche vengono risolte correttamente."""
        doc = make_rectangle()
        text_seq = (sm.TextBuilder()
                    .line(lambda folder, f: f"File:{f}")
                    .build())
        op = sm.AddText(text_seq, min_char=3, max_char=8)
        op.execute(doc, FOLDER, FILE)
        mtexts = list(doc.modelspace().query('MTEXT'))
        texts = [mt.text for mt in mtexts]
        print(f"[AddText] dynamic texts={texts}")
        self.assertIn(f"File:{FILE}", texts)

    def test_006_no_space_sets_position_none(self):
        """Se non trova spazio, text_position è None."""
        # Rettangolo minuscolo — nessuno spazio per il testo
        doc = make_rectangle(width=2, height=2)
        op = self._make_op(min_char=10, max_char=20)
        op.execute(doc, FOLDER, FILE)
        print(f"[AddText] no space → text_position={op.text_position}")
        self.assertIsNone(op.text_position)


# ═══════════════════════════════════════════════════════════
# Aligner
# ═══════════════════════════════════════════════════════════

class TestAligner(unittest.TestCase):

    def test_001_aligns_inclined_rectangle(self):
        """Dopo Aligner, la linea più lunga è orizzontale (angolo ≈ 0°)."""
        doc = make_inclined_rectangle(angle_deg=30)
        angle_before = get_longest_line_angle(doc)
        op = Aligner()
        op.execute(doc, FOLDER, FILE)
        angle_after = get_longest_line_angle(doc)
        print(f"\n[Aligner] angle before={angle_before:.1f}° after={angle_after:.1f}°")
        self.assertLess(angle_after, 5.0)  # tolleranza 5°

    def test_002_horizontal_rectangle_unchanged(self):
        """Un rettangolo già orizzontale rimane orizzontale."""
        doc = make_rectangle()
        angle_before = get_longest_line_angle(doc)
        op = Aligner()
        op.execute(doc, FOLDER, FILE)
        angle_after = get_longest_line_angle(doc)
        print(f"[Aligner] already horizontal: before={angle_before:.1f}° after={angle_after:.1f}°")
        self.assertLess(angle_after, 5.0)

    def test_003_returns_true(self):
        """Execute restituisce True."""
        doc = make_inclined_rectangle(angle_deg=45)
        op = Aligner()
        result = op.execute(doc, FOLDER, FILE)
        self.assertTrue(result)

    def test_004_entity_count_preserved(self):
        """Il numero di entità non cambia dopo l'allineamento."""
        doc = make_inclined_rectangle(angle_deg=30)
        count_before = len(list(doc.modelspace()))
        op = Aligner()
        op.execute(doc, FOLDER, FILE)
        count_after = len(list(doc.modelspace()))
        print(f"[Aligner] entities before={count_before} after={count_after}")
        self.assertEqual(count_before, count_after)


# ═══════════════════════════════════════════════════════════
# find_position fallback
# ═══════════════════════════════════════════════════════════

class TestFindPositionFallback(unittest.TestCase):
    """
    Testa il comportamento di find_position quando lo spazio è insufficiente.
    Il sistema deve ridurre progressivamente le dimensioni e cercare
    sulla longer entity come fallback.
    """

    def test_001_finds_space_in_narrow_piece(self):
        """
        Pezzo stretto — la sequenza si riduce e trova comunque spazio.
        """
        doc = make_narrow_rectangle(width=15, height=80)
        seq = sm.SequenceBuilder().literal("TEST").build()
        op = sm.AddMark(
            seq,
            scale_factor=50,
            min_char=3,
            max_char=10,
            down_to=2,
        )
        op.execute(doc, FOLDER, FILE)
        print(f"\n[Fallback] narrow piece → sequence={op.sequence_position.sequence[:1]}")
        self.assertGreater(len(op.sequence_position.sequence), 0)

    def test_002_no_space_returns_empty_sequence(self):
        """
        Pezzo microscopico — nessuno spazio trovato neanche col fallback.
        sequence_position rimane vuota.
        """
        doc = make_rectangle(width=2, height=2)
        seq = sm.SequenceBuilder().literal("TEST").build()
        op = sm.AddMark(
            seq,
            scale_factor=50,
            min_char=5,
            max_char=15,
            down_to=4,
        )
        op.execute(doc, FOLDER, FILE)
        print(f"[Fallback] tiny piece → sequence empty={len(op.sequence_position.sequence)==0}")
        self.assertEqual(len(op.sequence_position.sequence), 0)

    def test_003_addtext_fallback_narrow(self):
        """
        AddText su pezzo stretto — trova spazio riducendo le dimensioni.
        """
        doc = make_narrow_rectangle(width=20, height=80)
        text_seq = (sm.TextBuilder()
                    .static("Mat:S235")
                    .static("Sp:5")
                    .build())
        op = sm.AddText(
            text_seq,
            min_char=2,
            max_char=5,
            down_to=1,
        )
        op.execute(doc, FOLDER, FILE)
        print(f"[Fallback] AddText narrow → position={op.text_position}")
        self.assertIsNotNone(op.text_position)

    def test_004_addtext_no_space(self):
        """
        AddText su pezzo microscopico — nessuno spazio, text_position è None.
        """
        doc = make_rectangle(width=2, height=2)
        text_seq = sm.TextBuilder().static("Mat:S235").build()
        op = sm.AddText(
            text_seq,
            min_char=10,
            max_char=20,
            down_to=8,
        )
        op.execute(doc, FOLDER, FILE)
        print(f"[Fallback] AddText tiny → position={op.text_position}")
        self.assertIsNone(op.text_position)


if __name__ == "__main__":
    unittest.main(verbosity=2)
