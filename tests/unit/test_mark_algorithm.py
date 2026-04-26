"""
Test Suite per snapmark.mark_algorithm.mark_algorithm
"""

import unittest
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from snapmark.mark_algorithm.segmenter import (
    find_x_intercept_raw,
    find_x_intercept,
    find_intermediate_y,
    GeometryContext,
)
from snapmark.mark_algorithm.placer import (
    find_shared_spaces,
    find_space_between_interceptions,
)
from snapmark.mark_algorithm.sequence import (
    sequence_dim,
    SequenceText,
)


def make_ctx(segs=None):
    """Crea un GeometryContext minimale senza doc reale — solo per la cache."""
    ctx = GeometryContext.__new__(GeometryContext)
    ctx.x_intercept_cache = {}
    ctx.segs = segs or []
    ctx.min_x = 0
    ctx.min_y = 0
    ctx.max_x = 100
    ctx.max_y = 100
    ctx.avoid_segs = None
    return ctx


# ═══════════════════════════════════════════════════════════
# find_x_intercept_raw
# ═══════════════════════════════════════════════════════════

class TestFindXInterceptRaw(unittest.TestCase):

    def setUp(self):
        self.rect = [
            (0, 0, 100, 0),
            (100, 0, 100, 100),
            (100, 100, 0, 100),
            (0, 100, 0, 0),
        ]

    def test_001_intercept_vertical_segments(self):
        """Trova intercette sui lati verticali del rettangolo."""
        result = find_x_intercept_raw(50, self.rect)
        print(f"\n[find_x_intercept_raw] y=50 rect → {result}")
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], 100.0)

    def test_002_no_intercept_outside(self):
        """Nessuna intercetta fuori dal rettangolo."""
        result = find_x_intercept_raw(200, self.rect)
        print(f"[find_x_intercept_raw] y=200 → {result}")
        self.assertEqual(result, [])

    def test_003_intercept_at_bottom(self):
        """Intercetta sul bordo inferiore (y=0)."""
        result = find_x_intercept_raw(0, self.rect)
        print(f"[find_x_intercept_raw] y=0 → {result}")
        self.assertIsInstance(result, list)

    def test_004_result_is_sorted(self):
        """Il risultato è sempre ordinato."""
        segs = [(100, 0, 100, 100), (0, 0, 0, 100)]
        result = find_x_intercept_raw(50, segs)
        print(f"[find_x_intercept_raw] sorted check → {result}")
        self.assertEqual(result, sorted(result))

    def test_005_diagonal_segment(self):
        """Intercetta su segmento diagonale."""
        segs = [(0, 0, 100, 100)]
        result = find_x_intercept_raw(50, segs)
        print(f"[find_x_intercept_raw] diagonal y=50 → {result}")
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0], 50.0)

    def test_006_empty_segs(self):
        """Lista segmenti vuota restituisce lista vuota."""
        result = find_x_intercept_raw(50, [])
        self.assertEqual(result, [])


# ═══════════════════════════════════════════════════════════
# find_x_intercept (con cache)
# ═══════════════════════════════════════════════════════════

class TestFindXIntercept(unittest.TestCase):

    def setUp(self):
        self.rect = [
            (0, 0, 100, 0),
            (100, 0, 100, 100),
            (100, 100, 0, 100),
            (0, 100, 0, 0),
        ]
        self.ctx = make_ctx(self.rect)

    def test_001_same_result_as_raw(self):
        """find_x_intercept restituisce lo stesso risultato di find_x_intercept_raw."""
        raw = find_x_intercept_raw(50, self.rect)
        cached = find_x_intercept(50, self.rect, self.ctx)
        print(f"\n[find_x_intercept] raw={raw} cached={cached}")
        self.assertEqual(raw, cached)

    def test_002_cache_populated_after_call(self):
        """Dopo la chiamata, il valore è in cache."""
        find_x_intercept(50, self.rect, self.ctx)
        print(f"[find_x_intercept] cache keys={list(self.ctx.x_intercept_cache.keys())}")
        self.assertIn(50.0, self.ctx.x_intercept_cache)

    def test_003_cache_returns_same_value(self):
        """La seconda chiamata usa la cache e restituisce lo stesso valore."""
        first = find_x_intercept(50, self.rect, self.ctx)
        second = find_x_intercept(50, self.rect, self.ctx)
        print(f"[find_x_intercept] first={first} second={second}")
        self.assertEqual(first, second)

    def test_004_cache_is_not_stale_after_clear(self):
        """Dopo clear(), la cache viene ricalcolata correttamente."""
        find_x_intercept(50, self.rect, self.ctx)
        self.ctx.x_intercept_cache.clear()
        self.assertNotIn(50.0, self.ctx.x_intercept_cache)
        result = find_x_intercept(50, self.rect, self.ctx)
        self.assertIn(50.0, self.ctx.x_intercept_cache)
        self.assertEqual(len(result), 2)

    def test_005_different_y_different_cache_entry(self):
        """Y diverse producono entry di cache separate."""
        find_x_intercept(30, self.rect, self.ctx)
        find_x_intercept(70, self.rect, self.ctx)
        print(f"[find_x_intercept] cache keys={list(self.ctx.x_intercept_cache.keys())}")
        self.assertIn(30.0, self.ctx.x_intercept_cache)
        self.assertIn(70.0, self.ctx.x_intercept_cache)


# ═══════════════════════════════════════════════════════════
# find_intermediate_y
# ═══════════════════════════════════════════════════════════

class TestFindIntermediateY(unittest.TestCase):

    def test_001_basic(self):
        """Trova i valori intermedi tra 0 e 10 con step=2."""
        result = find_intermediate_y(0, 10, int_step=2)
        print(f"\n[find_intermediate_y] 0→10 step=2 → {result}")
        self.assertIn(2, result)
        self.assertIn(4, result)
        self.assertIn(6, result)
        self.assertIn(8, result)

    def test_002_no_values_if_range_too_small(self):
        """Nessun valore se il range è più piccolo dello step."""
        result = find_intermediate_y(0, 1, int_step=2)
        print(f"[find_intermediate_y] 0→1 step=2 → {result}")
        self.assertEqual(result, [])

    def test_003_does_not_include_top(self):
        """Il valore top non è incluso."""
        result = find_intermediate_y(0, 10, int_step=2)
        self.assertNotIn(10, result)

    def test_004_does_not_include_bottom(self):
        """Il valore bottom non è incluso."""
        result = find_intermediate_y(0, 10, int_step=2)
        self.assertNotIn(0, result)

    def test_005_step_1(self):
        """Step=1 produce tutti i valori interi intermedi."""
        result = find_intermediate_y(0, 5, int_step=1)
        print(f"[find_intermediate_y] 0→5 step=1 → {result}")
        self.assertIn(1, result)
        self.assertIn(2, result)
        self.assertIn(3, result)
        self.assertIn(4, result)


# ═══════════════════════════════════════════════════════════
# find_shared_spaces
# ═══════════════════════════════════════════════════════════

class TestFindSharedSpaces(unittest.TestCase):

    def test_001_perfect_overlap(self):
        """Sovrapposizione perfetta — uno spazio condiviso."""
        top = [0, 100]
        bot = [0, 100]
        result = find_shared_spaces(top, bot)
        print(f"\n[find_shared_spaces] perfect overlap → {result}")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], (0, 100))

    def test_002_partial_overlap(self):
        """Sovrapposizione parziale."""
        top = [20, 100]
        bot = [0, 80]
        result = find_shared_spaces(top, bot)
        print(f"[find_shared_spaces] partial overlap → {result}")
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][0], 20)
        self.assertAlmostEqual(result[0][1], 80)

    def test_003_no_overlap(self):
        """Nessuna sovrapposizione."""
        top = [0, 40]
        bot = [60, 100]
        result = find_shared_spaces(top, bot)
        print(f"[find_shared_spaces] no overlap → {result}")
        self.assertEqual(result, [])

    def test_004_multiple_spaces(self):
        """Forma con foro — due spazi condivisi."""
        top = [0, 30, 70, 100]
        bot = [0, 30, 70, 100]
        result = find_shared_spaces(top, bot)
        print(f"[find_shared_spaces] with hole → {result}")
        self.assertEqual(len(result), 2)

    def test_005_result_is_list_of_tuples(self):
        """Il risultato è una lista di tuple."""
        result = find_shared_spaces([0, 100], [0, 100])
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], tuple)


# ═══════════════════════════════════════════════════════════
# find_space_between_interceptions
# ═══════════════════════════════════════════════════════════

class TestFindSpaceBetweenInterceptions(unittest.TestCase):

    def setUp(self):
        self.rect = [
            (0, 0, 100, 0),
            (100, 0, 100, 100),
            (100, 100, 0, 100),
            (0, 100, 0, 0),
        ]
        self.ctx = make_ctx(self.rect)

    def test_001_fits_in_space(self):
        """Sequenza corta che entra nello spazio."""
        result = find_space_between_interceptions(
            x_left=0, x_right=100,
            lenght_sequence=20, height_sequence=10,
            segs=self.rect, margin=1, y=10,
            ctx=self.ctx
        )
        print(f"\n[find_space_between] fits → {result}")
        self.assertTrue(result)

    def test_002_does_not_fit_width(self):
        """Sequenza troppo larga per lo spazio."""
        result = find_space_between_interceptions(
            x_left=0, x_right=10,
            lenght_sequence=50, height_sequence=10,
            segs=self.rect, margin=1, y=10,
            ctx=self.ctx
        )
        print(f"[find_space_between] too wide → {result}")
        self.assertFalse(result)

    def test_003_blocked_by_internal_segment(self):
        """Sequenza bloccata da un segmento interno."""
        segs_with_obstacle = self.rect + [(50, 0, 50, 100)]
        ctx = make_ctx(segs_with_obstacle)
        result = find_space_between_interceptions(
            x_left=0, x_right=100,
            lenght_sequence=80, height_sequence=10,
            segs=segs_with_obstacle, margin=1, y=10,
            ctx=ctx
        )
        print(f"[find_space_between] blocked by internal seg → {result}")
        self.assertFalse(result)

    def test_004_margin_respected(self):
        """Con margin elevato, una sequenza che entrerebbe viene rifiutata."""
        result = find_space_between_interceptions(
            x_left=0, x_right=30,
            lenght_sequence=20, height_sequence=10,
            segs=self.rect, margin=10, y=10,
            ctx=self.ctx
        )
        print(f"[find_space_between] margin too large → {result}")
        self.assertFalse(result)

    def test_005_avoid_segs_horizontal_blocks(self):
        """Una linea orizzontale in avoid_segs blocca il posizionamento."""
        avoid = [(0, 15, 100, 15)]
        result = find_space_between_interceptions(
            x_left=0, x_right=100,
            lenght_sequence=20, height_sequence=10,
            segs=self.rect, margin=1, y=10,
            avoid_segs=avoid,
            ctx=self.ctx
        )
        print(f"[find_space_between] avoid horizontal → {result}")
        self.assertFalse(result)


# ═══════════════════════════════════════════════════════════
# sequence_dim
# ═══════════════════════════════════════════════════════════

class TestSequenceDim(unittest.TestCase):

    def _make_sequence(self, n_chars, width=2.0, height=5.0):
        seq = SequenceText()
        for _ in range(n_chars):
            segments = [[0.0, 0.0], [width, height]]
            seq.add_number(segments, [0.0, 0.0])
        return seq

    def test_001_single_char_dimensions(self):
        """Dimensioni corrette per un singolo carattere."""
        seq = self._make_sequence(1, width=2.0, height=5.0)
        length, height = sequence_dim(seq, 0, 0, space=1.5)
        print(f"\n[sequence_dim] 1 char → length={length:.2f} height={height:.2f}")
        self.assertGreater(length, 0)
        self.assertAlmostEqual(height, 5.0)

    def test_002_multiple_chars_length_grows(self):
        """Più caratteri → lunghezza maggiore."""
        seq1 = self._make_sequence(1, width=2.0, height=5.0)
        seq3 = self._make_sequence(3, width=2.0, height=5.0)
        len1, _ = sequence_dim(seq1, 0, 0, space=1.5)
        len3, _ = sequence_dim(seq3, 0, 0, space=1.5)
        print(f"[sequence_dim] 1 char len={len1:.2f} vs 3 char len={len3:.2f}")
        self.assertGreater(len3, len1)

    def test_003_space_factor_affects_length(self):
        """Space factor maggiore → lunghezza maggiore."""
        seq = self._make_sequence(2, width=2.0, height=5.0)
        len_tight, _ = sequence_dim(seq, 0, 0, space=1.0)
        len_wide, _ = sequence_dim(seq, 0, 0, space=2.0)
        print(f"[sequence_dim] space=1.0 len={len_tight:.2f} vs space=2.0 len={len_wide:.2f}")
        self.assertGreater(len_wide, len_tight)

    def test_004_empty_sequence_returns_zero(self):
        """Sequenza vuota → dimensioni zero."""
        seq = SequenceText()
        length, height = sequence_dim(seq, 0, 0, space=1.5)
        print(f"[sequence_dim] empty → length={length} height={height}")
        self.assertEqual(length, 0.0)
        self.assertEqual(height, 0.0)

    def test_005_positions_updated(self):
        """Le posizioni dei caratteri vengono aggiornate in base a x_pos."""
        seq = self._make_sequence(2, width=2.0, height=5.0)
        sequence_dim(seq, x_pos=10, y_pos=0, space=1.5)
        first_x = seq.sequence[0][1][0]
        print(f"[sequence_dim] first char x_pos={first_x}")
        self.assertAlmostEqual(first_x, 10.0)


# ═══════════════════════════════════════════════════════════
# GeometryContext
# ═══════════════════════════════════════════════════════════

def make_rect_doc(width=100, height=60):
    """DXF sintetico con rettangolo — usato nei test di GeometryContext."""
    import ezdxf
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    pts = [(0, 0), (width, 0), (width, height), (0, height)]
    for i in range(4):
        msp.add_line(pts[i], pts[(i + 1) % 4])
    return doc


def make_3d_doc():
    """DXF sintetico con geometria 3D — usato per test_005."""
    import ezdxf
    doc = ezdxf.new('R2010')
    doc.modelspace().add_line((0, 0, 0), (100, 0, 5))
    return doc


class TestGeometryContext(unittest.TestCase):

    def test_001_popola_segs_da_doc(self):
        """Context estratto da un rettangolo ha segs non vuoti."""
        ctx = GeometryContext(make_rect_doc())
        self.assertGreater(len(ctx.segs), 0)

    def test_002_bounding_box_corretto(self):
        """min/max x e y corrispondono al rettangolo."""
        ctx = GeometryContext(make_rect_doc(100, 60))
        self.assertAlmostEqual(ctx.min_x, 0)
        self.assertAlmostEqual(ctx.max_x, 100)
        self.assertAlmostEqual(ctx.min_y, 0)
        self.assertAlmostEqual(ctx.max_y, 60)

    def test_003_cache_inizialmente_vuota(self):
        """x_intercept_cache è vuota alla creazione."""
        ctx = GeometryContext(make_rect_doc())
        self.assertEqual(ctx.x_intercept_cache, {})

    def test_004_avoid_segs_none_se_no_avoid_layers(self):
        """avoid_segs è None se avoid_layers non specificato."""
        ctx = GeometryContext(make_rect_doc())
        self.assertIsNone(ctx.avoid_segs)

    def test_005_raises_se_geometria_3d(self):
        """Solleva ValueError se il DXF contiene geometria 3D."""
        with self.assertRaises(ValueError):
            GeometryContext(make_3d_doc())

if __name__ == "__main__":
    unittest.main(verbosity=2)