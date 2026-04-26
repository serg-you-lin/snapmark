"""
Test Suite per snapmark.utils.geometry e snapmark.utils.helpers

Test puri sulle funzioni geometriche e helper — non richiedono file DXF.

Lancia:
    python -m unittest tests/test_geometry_and_helpers.py -v
"""

import unittest
from pathlib import Path
import sys
import math

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import ezdxf

from snapmark.utils.geometry import (
    rotate_point,
    rotate_segs,
    seg_length,
    seg_angle,
    find_longer_entity,
    lwpolylines_to_virtual_segments,
    VirtualSegment,
)
from snapmark.utils.helpers import (
    find_circle_by_radius,
    find_circle_centers,
    is_excluded_layer,
    count_holes,
)
from snapmark.mark_algorithm.segment_text_geometry import ref_angle_and_pivot

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def make_virtual_segment(x1, y1, x2, y2):
    return VirtualSegment(x1, y1, x2, y2)


def make_doc_with_lwpolyline(points, closed=False):
    """Crea un doc con una LWPOLYLINE."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    msp.add_lwpolyline(points, close=closed)
    return doc


def make_doc_with_circles(specs):
    """specs: lista di (cx, cy, radius)."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    for cx, cy, r in specs:
        msp.add_circle((cx, cy), r)
    return doc


# ═══════════════════════════════════════════════════════════
# rotate_point
# ═══════════════════════════════════════════════════════════

class TestRotatePoint(unittest.TestCase):

    def test_001_rotation_90_degrees(self):
        """Rotazione di 90° attorno all'origine."""
        rx, ry = rotate_point((1, 0), (0, 0), math.pi / 2)
        print(f"\n[rotate_point] 90° → ({rx:.4f}, {ry:.4f})")
        self.assertAlmostEqual(rx, 0.0, places=5)
        self.assertAlmostEqual(ry, 1.0, places=5)

    def test_002_rotation_180_degrees(self):
        """Rotazione di 180° attorno all'origine."""
        rx, ry = rotate_point((1, 0), (0, 0), math.pi)
        print(f"[rotate_point] 180° → ({rx:.4f}, {ry:.4f})")
        self.assertAlmostEqual(rx, -1.0, places=5)
        self.assertAlmostEqual(ry, 0.0, places=5)

    def test_003_rotation_around_pivot(self):
        """Rotazione attorno a un pivot non in origine."""
        rx, ry = rotate_point((2, 0), (1, 0), math.pi / 2)
        print(f"[rotate_point] pivot=(1,0) 90° → ({rx:.4f}, {ry:.4f})")
        self.assertAlmostEqual(rx, 1.0, places=5)
        self.assertAlmostEqual(ry, 1.0, places=5)

    def test_004_zero_rotation(self):
        """Rotazione di 0° — punto invariato."""
        rx, ry = rotate_point((3, 4), (0, 0), 0)
        self.assertAlmostEqual(rx, 3.0, places=5)
        self.assertAlmostEqual(ry, 4.0, places=5)

    def test_005_full_rotation(self):
        """Rotazione di 360° — punto torna alla posizione iniziale."""
        rx, ry = rotate_point((3, 4), (1, 1), 2 * math.pi)
        self.assertAlmostEqual(rx, 3.0, places=5)
        self.assertAlmostEqual(ry, 4.0, places=5)

    def test_006_accepts_tuple(self):
        """Accetta tuple come input."""
        rx, ry = rotate_point((1, 0), (0, 0), math.pi / 2)
        self.assertIsInstance(rx, float)


# ═══════════════════════════════════════════════════════════
# rotate_segs
# ═══════════════════════════════════════════════════════════

class TestRotateSegs(unittest.TestCase):

    def test_001_rotates_all_segments(self):
        """Tutti i segmenti vengono ruotati."""
        segs = [(0, 0, 1, 0), (1, 0, 1, 1)]
        rotated = rotate_segs(segs, (0, 0), math.pi / 2)
        print(f"\n[rotate_segs] rotated={[(round(x,3) for x in s) for s in rotated]}")
        self.assertEqual(len(rotated), 2)

    def test_002_count_preserved(self):
        """Il numero di segmenti non cambia."""
        segs = [(0, 0, 10, 0), (10, 0, 10, 10), (10, 10, 0, 10)]
        rotated = rotate_segs(segs, (0, 0), math.pi / 4)
        self.assertEqual(len(rotated), 3)

    def test_003_zero_angle_unchanged(self):
        """Angolo zero — segmenti invariati."""
        segs = [(0, 0, 10, 0)]
        rotated = rotate_segs(segs, (0, 0), 0)
        self.assertAlmostEqual(rotated[0][0], 0.0, places=5)
        self.assertAlmostEqual(rotated[0][2], 10.0, places=5)

    def test_004_horizontal_becomes_vertical(self):
        """Segmento orizzontale ruotato di 90° diventa verticale."""
        segs = [(0, 0, 10, 0)]
        rotated = rotate_segs(segs, (0, 0), math.pi / 2)
        x1, y1, x2, y2 = rotated[0]
        print(f"[rotate_segs] horizontal→vertical: ({x1:.2f},{y1:.2f}) ({x2:.2f},{y2:.2f})")
        self.assertAlmostEqual(x1, 0.0, places=4)
        self.assertAlmostEqual(y1, 0.0, places=4)
        self.assertAlmostEqual(x2, 0.0, places=4)
        self.assertAlmostEqual(y2, 10.0, places=4)


# ═══════════════════════════════════════════════════════════
# seg_length
# ═══════════════════════════════════════════════════════════

class TestSegLength(unittest.TestCase):

    def test_001_horizontal(self):
        """Lunghezza segmento orizzontale."""
        l = seg_length((0, 0), (10, 0))
        print(f"\n[seg_length] horizontal={l}")
        self.assertAlmostEqual(l, 10.0)

    def test_002_vertical(self):
        """Lunghezza segmento verticale."""
        l = seg_length((0, 0), (0, 5))
        self.assertAlmostEqual(l, 5.0)

    def test_003_diagonal(self):
        """Lunghezza segmento diagonale — teorema di Pitagora."""
        l = seg_length((0, 0), (3, 4))
        print(f"[seg_length] diagonal 3-4-5={l}")
        self.assertAlmostEqual(l, 5.0)

    def test_004_zero_length(self):
        """Punto — lunghezza zero."""
        l = seg_length((5, 5), (5, 5))
        self.assertAlmostEqual(l, 0.0)


# ═══════════════════════════════════════════════════════════
# seg_angle
# ═══════════════════════════════════════════════════════════

class TestSegAngle(unittest.TestCase):

    def test_001_horizontal_right(self):
        """Segmento orizzontale verso destra — angolo 0."""
        a = seg_angle((0, 0), (10, 0))
        print(f"\n[seg_angle] horizontal right={math.degrees(a):.1f}°")
        self.assertAlmostEqual(a, 0.0, places=5)

    def test_002_vertical_up(self):
        """Segmento verticale verso l'alto — angolo 90°."""
        a = seg_angle((0, 0), (0, 10))
        print(f"[seg_angle] vertical up={math.degrees(a):.1f}°")
        self.assertAlmostEqual(a, math.pi / 2, places=5)

    def test_003_diagonal_45(self):
        """Segmento diagonale a 45°."""
        a = seg_angle((0, 0), (10, 10))
        print(f"[seg_angle] diagonal={math.degrees(a):.1f}°")
        self.assertAlmostEqual(a, math.pi / 4, places=5)

    def test_004_normalizes_left_to_right(self):
        """Segmento verso sinistra viene normalizzato."""
        a_right = seg_angle((0, 0), (10, 0))
        a_left  = seg_angle((10, 0), (0, 0))
        print(f"[seg_angle] right={math.degrees(a_right):.1f}° left={math.degrees(a_left):.1f}°")
        self.assertAlmostEqual(a_right, a_left, places=5)


# ═══════════════════════════════════════════════════════════
# find_longer_entity
# ═══════════════════════════════════════════════════════════

class TestFindLongerEntity(unittest.TestCase):

    def test_001_finds_longest(self):
        """Trova il segmento più lungo."""
        segs = [
            make_virtual_segment(0, 0, 10, 0),   # len=10
            make_virtual_segment(0, 0, 50, 0),   # len=50 ← longest
            make_virtual_segment(0, 0, 5, 0),    # len=5
        ]
        longest, _ = find_longer_entity(segs)
        length = seg_length(
            (longest.dxf.start.x, longest.dxf.start.y),
            (longest.dxf.end.x, longest.dxf.end.y)
        )
        print(f"\n[find_longer_entity] longest length={length}")
        self.assertAlmostEqual(length, 50.0)

    def test_002_is_below_flag_true(self):
        """is_below=True quando il segmento più lungo è al bordo inferiore."""
        segs = [
            make_virtual_segment(0, 0, 100, 0),  # y=0, più lungo
            make_virtual_segment(0, 10, 50, 10), # y=10
        ]
        _, is_below = find_longer_entity(segs)
        print(f"[find_longer_entity] is_below={is_below}")
        self.assertTrue(is_below)

    def test_003_is_below_flag_false(self):
        """is_below=False quando il segmento più lungo è in alto."""
        segs = [
            make_virtual_segment(0, 0, 10, 0),   # y=0, corto
            make_virtual_segment(0, 10, 110, 10),# y=10, più lungo
        ]
        _, is_below = find_longer_entity(segs)
        print(f"[find_longer_entity] is_below={is_below}")
        self.assertFalse(is_below)

    def test_004_single_entity(self):
        """Con un solo segmento, lo restituisce."""
        segs = [make_virtual_segment(0, 0, 30, 0)]
        longest, _ = find_longer_entity(segs)
        self.assertIsNotNone(longest)


# ═══════════════════════════════════════════════════════════
# ref_angle_and_pivot
# ═══════════════════════════════════════════════════════════

class TestRefAngleAndPivot(unittest.TestCase):

    def test_001_horizontal_segment(self):
        """Segmento orizzontale — angolo=0, pivot=start."""
        seg = make_virtual_segment(5, 3, 15, 3)
        angle, pivot = ref_angle_and_pivot(seg)
        print(f"\n[ref_angle_and_pivot] angle={math.degrees(angle):.1f}° pivot={pivot}")
        self.assertAlmostEqual(angle, 0.0, places=5)
        self.assertEqual(pivot, (5, 3))

    def test_002_diagonal_segment(self):
        """Segmento a 45° — angolo=π/4."""
        seg = make_virtual_segment(0, 0, 10, 10)
        angle, pivot = ref_angle_and_pivot(seg)
        print(f"[ref_angle_and_pivot] diagonal angle={math.degrees(angle):.1f}°")
        self.assertAlmostEqual(angle, math.pi / 4, places=5)

    def test_003_pivot_is_start(self):
        """Il pivot è sempre il punto di start."""
        seg = make_virtual_segment(3, 7, 13, 7)
        _, pivot = ref_angle_and_pivot(seg)
        self.assertEqual(pivot, (3, 7))


# ═══════════════════════════════════════════════════════════
# lwpolylines_to_virtual_segments
# ═══════════════════════════════════════════════════════════

class TestLwpolylinesToVirtualSegments(unittest.TestCase):

    def test_001_open_polyline(self):
        """LWPOLYLINE aperta con 3 punti → 2 segmenti."""
        doc = make_doc_with_lwpolyline([(0,0), (10,0), (10,10)], closed=False)
        lwpolys = list(doc.modelspace().query('LWPOLYLINE'))
        segs = lwpolylines_to_virtual_segments(lwpolys)
        print(f"\n[lwpoly_to_virtual] open 3pts → {len(segs)} segs")
        self.assertEqual(len(segs), 2)

    def test_002_closed_polyline(self):
        """LWPOLYLINE chiusa con 3 punti → 3 segmenti."""
        doc = make_doc_with_lwpolyline([(0,0), (10,0), (10,10)], closed=True)
        lwpolys = list(doc.modelspace().query('LWPOLYLINE'))
        segs = lwpolylines_to_virtual_segments(lwpolys)
        print(f"[lwpoly_to_virtual] closed 3pts → {len(segs)} segs")
        self.assertEqual(len(segs), 3)

    def test_003_source_entity_set(self):
        """Ogni segmento porta il riferimento alla LWPOLYLINE originale."""
        doc = make_doc_with_lwpolyline([(0,0), (10,0), (10,10)], closed=False)
        lwpolys = list(doc.modelspace().query('LWPOLYLINE'))
        segs = lwpolylines_to_virtual_segments(lwpolys)
        print(f"[lwpoly_to_virtual] source_entity set={segs[0].source_entity is not None}")
        self.assertIsNotNone(segs[0].source_entity)

    def test_004_empty_list(self):
        """Lista vuota → nessun segmento."""
        segs = lwpolylines_to_virtual_segments([])
        self.assertEqual(segs, [])

    def test_005_virtual_segment_has_dxf_interface(self):
        """I VirtualSegment hanno l'interfaccia .dxf.start/.end."""
        doc = make_doc_with_lwpolyline([(0,0), (10,0)], closed=False)
        lwpolys = list(doc.modelspace().query('LWPOLYLINE'))
        segs = lwpolylines_to_virtual_segments(lwpolys)
        seg = segs[0]
        self.assertTrue(hasattr(seg.dxf, 'start'))
        self.assertTrue(hasattr(seg.dxf, 'end'))
        self.assertAlmostEqual(seg.dxf.start.x, 0.0)
        self.assertAlmostEqual(seg.dxf.end.x, 10.0)


# ═══════════════════════════════════════════════════════════
# is_excluded_layer
# ═══════════════════════════════════════════════════════════

class TestIsExcludedLayer(unittest.TestCase):

    def test_001_layer_in_list(self):
        """Layer presente nella lista → True."""
        result = is_excluded_layer('MARK', ['MARK', 'TEXT'])
        print(f"\n[is_excluded_layer] MARK in [MARK,TEXT]={result}")
        self.assertTrue(result)

    def test_002_layer_not_in_list(self):
        """Layer non presente → False."""
        result = is_excluded_layer('0', ['MARK', 'TEXT'])
        self.assertFalse(result)

    def test_003_case_insensitive(self):
        """Il confronto è case-insensitive."""
        result = is_excluded_layer('mark', ['MARK'])
        print(f"[is_excluded_layer] case insensitive={result}")
        self.assertTrue(result)

    def test_004_none_list(self):
        """Lista None → niente è escluso."""
        result = is_excluded_layer('MARK', None)
        self.assertFalse(result)

    def test_005_empty_list(self):
        """Lista vuota → niente è escluso."""
        result = is_excluded_layer('MARK', [])
        self.assertFalse(result)

    def test_006_whitespace_stripped(self):
        """Spazi extra vengono ignorati."""
        result = is_excluded_layer(' MARK ', [' MARK '])
        self.assertTrue(result)


# ═══════════════════════════════════════════════════════════
# find_circle_by_radius
# ═══════════════════════════════════════════════════════════

class TestFindCircleByRadius(unittest.TestCase):

    def test_001_returns_callable(self):
        """find_circle_by_radius restituisce una funzione."""
        fn = find_circle_by_radius(min_diam=4, max_diam=20)
        print(f"\n[find_circle_by_radius] callable={callable(fn)}")
        self.assertTrue(callable(fn))

    def test_002_finds_circles_in_range(self):
        """La funzione trova i cerchi nel range."""
        doc = make_doc_with_circles([(0, 0, 5), (10, 0, 5)])  # diam=10
        fn = find_circle_by_radius(min_diam=4, max_diam=20)
        result = list(fn(doc))
        print(f"[find_circle_by_radius] found={len(result)}")
        self.assertEqual(len(result), 2)

    def test_003_ignores_out_of_range(self):
        """Ignora i cerchi fuori dal range."""
        doc = make_doc_with_circles([(0, 0, 1), (10, 0, 50)])  # diam 2 e 100
        fn = find_circle_by_radius(min_diam=4, max_diam=20)
        result = list(fn(doc))
        self.assertEqual(len(result), 0)

    def test_004_boundary_values(self):
        """I valori al limite del range sono inclusi."""
        doc = make_doc_with_circles([(0, 0, 2), (10, 0, 10)])  # diam 4 e 20
        fn = find_circle_by_radius(min_diam=4, max_diam=20)
        result = list(fn(doc))
        print(f"[find_circle_by_radius] boundary={len(result)}")
        self.assertEqual(len(result), 2)


# ═══════════════════════════════════════════════════════════
# find_circle_centers
# ═══════════════════════════════════════════════════════════

class TestFindCircleCenters(unittest.TestCase):

    def test_001_returns_correct_centers(self):
        """Restituisce le coordinate corrette dei centri."""
        doc = make_doc_with_circles([(10, 20, 5), (30, 40, 5)])
        circles = list(doc.modelspace().query('CIRCLE'))
        centers = find_circle_centers(circles)
        print(f"\n[find_circle_centers] centers={centers}")
        self.assertIn((10.0, 20.0), centers)
        self.assertIn((30.0, 40.0), centers)

    def test_002_empty_list(self):
        """Lista vuota → nessun centro."""
        centers = find_circle_centers([])
        self.assertEqual(centers, [])

    def test_003_count_matches(self):
        """Il numero di centri corrisponde al numero di cerchi."""
        doc = make_doc_with_circles([(0, 0, 5), (10, 0, 5), (20, 0, 5)])
        circles = list(doc.modelspace().query('CIRCLE'))
        centers = find_circle_centers(circles)
        self.assertEqual(len(centers), 3)


# ═══════════════════════════════════════════════════════════
# count_holes
# ═══════════════════════════════════════════════════════════

class TestCountHoles(unittest.TestCase):

    def test_001_counts_list(self):
        """Conta correttamente gli elementi."""
        result = count_holes([1, 2, 3])
        print(f"\n[count_holes] list of 3={result}")
        self.assertEqual(result, 3)

    def test_002_empty_list(self):
        """Lista vuota → 0."""
        self.assertEqual(count_holes([]), 0)

    def test_003_accepts_generator(self):
        """Accetta anche un generatore."""
        result = count_holes(x for x in range(5))
        print(f"[count_holes] generator of 5={result}")
        self.assertEqual(result, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
