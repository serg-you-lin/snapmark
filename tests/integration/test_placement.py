"""
Test di integrazione per place_sequence e find_position

Usa DXF sintetici costruiti in memoria — non richiedono file reali.
Testa il pipeline end-to-end: posizionamento, fallback, rotazione.

Lancia:
    python -m unittest tests/integration/test_placement.py -v
"""

import unittest
from pathlib import Path
import sys
import math

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import ezdxf
import snapmark.mark_algorithm as ma
from snapmark.mark_algorithm import (
    place_sequence,
    place_text,
    comp_sf,
    SequenceText,
)
from snapmark.mark_algorithm.segment_text_geometry import rotate_segment_text_sequence

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def make_rectangle_doc(width=200, height=100):
    """DXF sintetico con rettangolo — caso base per Tentativo 1."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    pts = [(0, 0), (width, 0), (width, height), (0, height)]
    for i in range(4):
        msp.add_line(pts[i], pts[(i + 1) % 4])
    return doc


def make_rotated_doc(angle_deg=45, width=200, height=100):
    """DXF sintetico con rettangolo ruotato — forza il Tentativo 2."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    angle = math.radians(angle_deg)
    cx, cy = width / 2, height / 2
    corners = [(-width/2, -height/2), (width/2, -height/2),
               (width/2,  height/2), (-width/2,  height/2)]
    rotated = [
        (cx + x * math.cos(angle) - y * math.sin(angle),
         cy + x * math.sin(angle) + y * math.cos(angle))
        for x, y in corners
    ]
    for i in range(4):
        msp.add_line(rotated[i], rotated[(i + 1) % 4])
    return doc


def sequence_is_inside_doc(sequence, doc, tolerance=5.0):
    """Verifica che tutti i punti di ancoraggio della sequenza siano dentro il bounding box."""
    msp = doc.modelspace()
    all_x, all_y = [], []
    for e in msp:
        try:
            all_x += [e.dxf.start.x, e.dxf.end.x]
            all_y += [e.dxf.start.y, e.dxf.end.y]
        except Exception:
            pass

    min_x = min(all_x) - tolerance
    max_x = max(all_x) + tolerance
    min_y = min(all_y) - tolerance
    max_y = max(all_y) + tolerance

    for _, position in sequence.sequence:
        if not (min_x <= position[0] <= max_x):
            return False
        if not (min_y <= position[1] <= max_y):
            return False
    return True


def call_place_sequence(doc, text="123"):
    """Chiama place_sequence con i parametri standard di AddMark."""
    scale_factor = comp_sf(doc, scale_factor=50)
    return place_sequence(
        doc, text, scale_factor,
        excluded_layers=None, avoid_layers=None,
        space=1.5, min_char=5, max_char=20,
        arbitrary_x=None, arbitrary_y=None,
        align='c', start_y=1, step=2, margin=1, down_to=None
    )


# ═══════════════════════════════════════════════════════════
# place_sequence — Tentativo 1
# ═══════════════════════════════════════════════════════════

class TestPlaceSequenceTentativo1(unittest.TestCase):

    def test_001_returns_nonempty_sequence(self):
        """Rettangolo grande — place_sequence trova spazio al Tentativo 1."""
        doc = make_rectangle_doc(200, 100)
        result = call_place_sequence(doc, "123")
        print(f"\n[place_sequence T1] len={len(result.sequence)}")
        self.assertGreater(len(result.sequence), 0)

    def test_002_sequence_inside_bounding_box(self):
        """La sequenza è posizionata dentro il bounding box del disegno."""
        doc = make_rectangle_doc(200, 100)
        result = call_place_sequence(doc, "123")
        self.assertTrue(sequence_is_inside_doc(result, doc))

    def test_003_empty_text_raises(self):
        """Testo vuoto solleva eccezione."""
        doc = make_rectangle_doc(200, 100)
        with self.assertRaises(Exception):
            call_place_sequence(doc, "")

    def test_004_returns_empty_ns_if_no_space(self):
        """Rettangolo troppo piccolo — ritorna SegmentText() vuoto."""
        doc = make_rectangle_doc(2, 2)
        result = call_place_sequence(doc, "123456789")
        print(f"[place_sequence T1] no space len={len(result.sequence)}")
        self.assertEqual(len(result.sequence), 0)


# ═══════════════════════════════════════════════════════════
# place_sequence — Tentativo 2 (fallback ruotato)
# ═══════════════════════════════════════════════════════════

class TestPlaceSequenceTentativo2(unittest.TestCase):

    def test_001_rotated_doc_finds_space(self):
        """Disegno ruotato — il fallback trova comunque spazio."""
        doc = make_rotated_doc(angle_deg=45)
        result = call_place_sequence(doc, "123")
        print(f"\n[place_sequence T2] rotated len={len(result.sequence)}")
        self.assertGreater(len(result.sequence), 0)

    def test_002_rotated_sequence_inside_bounding_box(self):
        """La sequenza ruotata è dentro il bounding box del disegno."""
        doc = make_rotated_doc(angle_deg=45)
        result = call_place_sequence(doc, "123")
        self.assertTrue(sequence_is_inside_doc(result, doc))


# ═══════════════════════════════════════════════════════════
# rotate_ns_sequence — gestione None
# ═══════════════════════════════════════════════════════════

class TestRotateNsSequence(unittest.TestCase):

    def test_001_none_in_segments_does_not_crash(self):
        """None nei segmenti del font non causa crash durante la rotazione."""
        seq = SequenceText()
        seq.add_number([[0.0, 0.0], None, [1.0, 1.0]], [0.0, 0.0])
        try:
            rotate_segment_text_sequence(seq, (0.0, 0.0), math.pi / 4)
        except TypeError:
            self.fail("rotate_segment_text_sequence ha crashato su None")

    def test_002_rotation_moves_positions(self):
        """La rotazione di 90° cambia le posizioni."""
        seq = SequenceText()
        seq.add_number([[1.0, 0.0]], [10.0, 0.0])
        rotate_segment_text_sequence(seq, (0.0, 0.0), math.pi / 2)
        _, position = seq.sequence[0]
        print(f"\n[rotate_segment_text] position after 90° → {position}")
        self.assertAlmostEqual(position[0], 0.0, places=5)
        self.assertAlmostEqual(position[1], 10.0, places=5)


# ═══════════════════════════════════════════════════════════
# find_position — usato da AddText
# ═══════════════════════════════════════════════════════════

# class TestFindPosition(unittest.TestCase):

#     def setUp(self):
#         ma.x_intercept_cache.clear()
#         ma.segments_cache = None

#     def test_001_returns_valid_coordinates(self):
#         """Rettangolo grande — find_position ritorna coordinate valide."""
#         doc = make_rectangle_doc(200, 100)
#         x, y = place_text(doc, width=30, height=10)
#         print(f"\n[find_position] x={x} y={y}")
#         self.assertIsNotNone(x)
#         self.assertIsNotNone(y)

#     def test_002_returns_none_if_no_space(self):
#         """Rettangolo troppo piccolo — find_position ritorna None, None."""
#         doc = make_rectangle_doc(2, 2)
#         x, y = place_text(doc, width=100, height=50)
#         print(f"[find_position] no space x={x} y={y}")
#         self.assertIsNone(x)
#         self.assertIsNone(y)

#     def test_003_position_inside_bounding_box(self):
#         """La posizione trovata è dentro il bounding box."""
#         doc = make_rectangle_doc(200, 100)
#         x, y = place_text(doc, width=30, height=10)
#         self.assertGreaterEqual(x, 0)
#         self.assertLessEqual(x, 200)
#         self.assertGreaterEqual(y, 0)
#         self.assertLessEqual(y, 100)

class TestFindPosition(unittest.TestCase):

    def test_001_returns_valid_coordinates(self):
        """Rettangolo grande — place_text ritorna coordinate valide."""
        doc = make_rectangle_doc(200, 100)
        x, y, w, h = place_text(doc, texts=["ABC"], min_char=5)
        self.assertIsNotNone(x)
        self.assertIsNotNone(y)

    def test_002_returns_none_if_no_space(self):
        doc = make_rectangle_doc(2, 2)
        msp = doc.modelspace()
        lines = list(msp.query('LINE'))
        for l in lines:
            print(f"line: {l.dxf.start} -> {l.dxf.end}")
        x, y, w, h = place_text(doc, texts=["ABC"], min_char=5)
        self.assertIsNone(x)
        self.assertIsNone(y)

    def test_003_position_inside_bounding_box(self):
        """La posizione trovata è dentro il bounding box."""
        doc = make_rectangle_doc(200, 100)
        x, y, w, h = place_text(doc, texts=["ABC"], min_char=5)
        self.assertGreaterEqual(x, 0)
        self.assertLessEqual(x, 200)
        self.assertGreaterEqual(y, 0)
        self.assertLessEqual(y, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)