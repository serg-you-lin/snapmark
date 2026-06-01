import math
from snapmark.operations.basic_operations import Operation
from snapmark.utils.geometry import _line_length, _unit_vector, _point_along
from snapmark.entities.editor import add_line  



class TrimBendLines(Operation):
    """
    Trim bending lines on one or multiple layers.

    Backward compatible:
    - layer="MARCATURA"
    - layer=["MARCATURA", "BEND"]
    """
    def __init__(self, layers, start_length, end_length, center_length=None):
        super().__init__()

        if isinstance(layers, str):
            self.layers = [layers]
        else:
            self.layers = list(layers)

        self.start_length = start_length
        self.end_length = end_length
        self.center_length = center_length

    def execute(self, doc, folder, file_name):
        msp = doc.modelspace()

        bending_lines = [
            e for e in msp
            if e.dxftype() == "LINE" and e.dxf.layer in self.layers
        ]

        if not bending_lines:
            return False

        for line in bending_lines:
            _trim_single_line(
                msp,
                line,
                self.start_length,
                self.end_length,
                self.center_length,
            )

        return self.create_new

    def message(self, file_name):
        parts = [
            f"start={self.start_length}",
            f"end={self.end_length}",
        ]

        if self.center_length:
            parts.append(f"center={self.center_length}")

        self.message_text = (
            f"✓ Bending lines trimmate in {file_name} "
            f"({', '.join(parts)}, layers={self.layers})"
        )
        print(self.message_text)


#####################################################################


def _trim_single_line(msp, line, start_length, end_length, center_length):
    """
    Data una LINE ezdxf, aggiunge i segmenti trimmati e rimuove l'originale.

    Tratti aggiunti:
      - tratto iniziale: [start → start + start_length]
      - tratto finale:   [end - end_length → end]
      - tratto centrale (opzionale): [center - center_length/2 → center + center_length/2]
    """
    start = (line.dxf.start.x, line.dxf.start.y)
    end   = (line.dxf.end.x,   line.dxf.end.y)
    layer = line.dxf.layer
    color = line.dxf.color if line.dxf.hasattr("color") else None

    total_length = _line_length(start, end)
    uv = _unit_vector(start, end)

    segments = []

    # — tratto iniziale —
    p_start_end = _point_along(start, uv, min(start_length, total_length))
    segments.append((start, p_start_end))

    # — tratto finale —
    uv_inv = (-uv[0], -uv[1])
    p_end_start = _point_along(end, uv_inv, min(end_length, total_length))
    segments.append((p_end_start, end))

    # — tratto centrale (opzionale) —
    if center_length is not None and center_length > 0:
        half = center_length / 2.0
        center_pt = (
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2,
        )
        p_c1 = _point_along(center_pt, uv_inv, min(half, total_length / 2))
        p_c2 = _point_along(center_pt, uv,     min(half, total_length / 2))
        segments.append((p_c1, p_c2))

    # Rimuove l'originale e aggiunge i tratti
    msp.delete_entity(line)
    for p1, p2 in segments:
        add_line(msp, p1, p2, layer, color)