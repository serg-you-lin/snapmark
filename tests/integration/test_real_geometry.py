"""
Test su geometrie reali — flange, pezzi stretti, forme con cerchi.
Testa l'algoritmo su casi che si trovano in produzione.

Lancia:
    python -m unittest tests/integration/test_real_geometries.py -v
"""

import unittest
from pathlib import Path
import sys
import math

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import ezdxf
import snapmark as sm


FOLDER = r"C:\test"
FILE = "FTDP00132C_P1_S235JR_SP5_Q2.DXF"

material_map = {"S235JR": "FE-DECAPATO"}

def parse_filename(name):
    import os
    base = os.path.splitext(name)[0]
    parts = base.split("_")
    return {
        "quantity": next((p[1:] for p in parts if p.startswith("Q")), None),
        "material": next((p for p in parts if p.startswith("S") and not p.startswith("SP")), None),
        "thickness": next((p[2:] for p in parts if p.startswith("SP")), None),
    }


def make_flange_doc():
    """
    Flangia reale con cerchi — geometria circolare.
    Cerchio esterno r=72.5, cerchio interno r=54.5,
    tre fori r=3.5 e uno r=3.5 offset.
    """
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    msp.add_circle((0, 0), radius=72.5)
    msp.add_circle((0, 0), radius=54.5)
    msp.add_circle((56.291651246, -32.5), radius=3.5)
    msp.add_circle((-56.291651246, -32.5), radius=3.5)
    msp.add_circle((0, 65), radius=3.5)

    return doc


def make_narrow_tall_doc(width=10, height=200):
    """Pezzo stretto e alto — forza il tentativo 2 (rotazione)."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    pts = [(0, 0), (width, 0), (width, height), (0, height)]
    for i in range(4):
        msp.add_line(pts[i], pts[(i + 1) % 4])
    return doc


def make_rect_with_avoid_layer(width=100, height=60, avoid_layer='MARCATURA'):
    """Rettangolo con una linea sul layer da evitare al centro."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    pts = [(0, 0), (width, 0), (width, height), (0, height)]
    for i in range(4):
        msp.add_line(pts[i], pts[(i + 1) % 4])
    # linea orizzontale al centro sul layer da evitare
    msp.add_line((0, height/2), (width, height/2),
                 dxfattribs={'layer': avoid_layer})
    return doc


def make_mark_op():
    return sm.AddMark(
        sm.SequenceBuilder().file_part(trim_start=5).build(),
        scale_factor=100,
        align='c',
        max_height=12,
        min_height=8,
        down_to=5,
    )


def make_text_op(avoid_layers=None):
    return sm.AddText(
        text_sequence=(
            sm.TextBuilder()
            .line(lambda folder, f: f"Material:{material_map.get(parse_filename(f)['material'], parse_filename(f)['material'])}")
            .line(lambda folder, f: f"Thickness:{parse_filename(f)['thickness']}")
            .line(lambda folder, f: f"Quantity:{parse_filename(f)['quantity']}")
            .build()
        ),
        min_char=5,
        down_to=0.5,
        text_layer="TEXT",
        avoid_layers=avoid_layers,
        text_bbbox=False,
    )


def make_mark_op_narrow():
    return sm.AddMark(
        sm.SequenceBuilder().literal("123").build(),
        scale_factor=50,
        align='c',
        max_height=8,
        min_height=3,
        down_to=2,
    )
# ═══════════════════════════════════════════════════════════
# Flangia — geometria circolare
# ═══════════════════════════════════════════════════════════

class TestFlangia(unittest.TestCase):

    def test_001_addmark_trova_spazio(self):
        """AddMark trova spazio sulla flangia."""
        doc = make_flange_doc()
        op = make_mark_op()
        op.execute(doc, FOLDER, FILE)
        print(f"\n[Flangia] mark sequence={len(op.sequence_position.sequence)}")
        self.assertGreater(len(op.sequence_position.sequence), 0)

    def test_002_addtext_trova_spazio(self):
        """AddText cerca spazio sulla flangia — può non trovarlo se piena."""
        doc = make_flange_doc()
        make_mark_op().execute(doc, FOLDER, FILE)
        op = make_text_op()
        op.execute(doc, FOLDER, FILE)
        print(f"[Flangia] text_position={op.text_position}")
        # sulla flangia lo spazio è limitato — accettiamo anche None
        # il test verifica solo che non crashi

    def test_003_mark_e_text_non_si_sovrappongono(self):
        """Mark e Text trovano posizioni diverse."""
        doc = make_flange_doc()
        mark_op = make_mark_op()
        text_op = make_text_op()
        mark_op.execute(doc, FOLDER, FILE)
        text_op.execute(doc, FOLDER, FILE)

        if not mark_op.sequence_position.sequence or text_op.text_position is None:
            self.skipTest("Uno dei due non ha trovato spazio")

        mark_x = mark_op.sequence_position.sequence[0][1][0]
        text_x, text_y = text_op.text_position
        print(f"[Flangia] mark_x={mark_x:.2f} text_x={text_x:.2f}")
        self.assertNotAlmostEqual(mark_x, text_x, places=1)

    def test_004_entita_nel_dxf(self):
        """Dopo le due operazioni il DXF contiene LINE dalla marcatura."""
        doc = make_flange_doc()
        make_mark_op().execute(doc, FOLDER, FILE)
        make_text_op().execute(doc, FOLDER, FILE)
        msp = doc.modelspace()
        lines = list(msp.query('LINE'))
        print(f"[Flangia] LINE={len(lines)}")
        self.assertGreater(len(lines), 0)


# ═══════════════════════════════════════════════════════════
# Pezzo stretto e alto — forza tentativo 2
# ═══════════════════════════════════════════════════════════

class TestNarrowTall(unittest.TestCase):
    """
    Un pezzo stretto e alto non ha spazio orizzontale per la marcatura.
    L'algoritmo deve ruotare il sistema di riferimento (tentativo 2)
    e trovare spazio lungo l'asse verticale.
    """

    def test_001_addmark_fallback_tentativo2(self):
        """Pezzo stretto — AddMark usa il tentativo 2 e trova spazio."""
        doc = make_narrow_tall_doc(width=10, height=150)
        op = make_mark_op_narrow()
        op.execute(doc, FOLDER, FILE)
        print(f"\n[NarrowTall] sequence={len(op.sequence_position.sequence)}")
        self.assertGreater(len(op.sequence_position.sequence), 0)

    def test_002_sequenza_ruotata(self):
        """La sequenza trovata col tentativo 2 ha posizione non banale."""
        doc = make_narrow_tall_doc(width=10, height=150)
        op = make_mark_op_narrow()
        op.execute(doc, FOLDER, FILE)
        if not op.sequence_position.sequence:
            self.skipTest("Nessuno spazio trovato")
        pos = op.sequence_position.sequence[0][1]
        print(f"[NarrowTall] primo carattere pos={pos}")
        # la posizione non deve essere all'origine
        self.assertFalse(pos[0] == 0 and pos[1] == 0)


# ═══════════════════════════════════════════════════════════
# Avoid layers
# ═══════════════════════════════════════════════════════════

class TestAvoidLayers(unittest.TestCase):

    def test_001_addmark_evita_avoid_layer(self):
        """AddMark non piazza la marcatura sopra il layer MARCATURA."""
        doc = make_rect_with_avoid_layer(100, 60, 'MARCATURA')
        op = sm.AddMark(
            sm.SequenceBuilder().literal("TEST").build(),
            scale_factor=50,
            min_height=5,
            max_height=15,
            avoid_layers=['MARCATURA'],
        )
        op.execute(doc, FOLDER, FILE)
        if not op.sequence_position.sequence:
            self.skipTest("Nessuno spazio trovato")

        # la marcatura non deve cadere a y=30 (la linea di avoid)
        pos_y = op.sequence_position.sequence[0][1][1]
        print(f"[AvoidLayers] mark y={pos_y:.2f} avoid_y=30")
        self.assertNotAlmostEqual(pos_y, 30, delta=5)

    def test_002_addtext_evita_avoid_layer(self):
        """AddText non piazza il testo sopra il layer MARCATURA."""
        doc = make_rect_with_avoid_layer(100, 60, 'MARCATURA')
        op = make_text_op(avoid_layers=['MARCATURA'])
        op.execute(doc, FOLDER, FILE)
        if op.text_position is None:
            self.skipTest("Nessuno spazio trovato")
        _, text_y = op.text_position
        print(f"[AvoidLayers] text y={text_y:.2f} avoid_y=30")
        self.assertNotAlmostEqual(text_y, 30, delta=5)

    def test_003_senza_avoid_layers_trova_comunque_spazio(self):
        """Senza avoid_layers, AddMark trova spazio normalmente."""
        doc = make_rect_with_avoid_layer(100, 60, 'MARCATURA')
        op = sm.AddMark(
            sm.SequenceBuilder().literal("TEST").build(),
            scale_factor=50,
            min_height=5,
            max_height=15,
        )
        op.execute(doc, FOLDER, FILE)
        self.assertGreater(len(op.sequence_position.sequence), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)