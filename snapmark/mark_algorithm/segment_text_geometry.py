import numpy as np
from snapmark.utils.geometry import rotate_point, seg_angle, comp_centroid

##############################################################################
# Rotating the TextSequence from local coordinates back to real drawing coordinates after placement.
##############################################################################

def rotate_segment_text_sequence(sequence, pivot, angle):
    """
    Rotates all points of a TextSequence around a pivot point.

    Called after place_sequence to rotate the found sequence from local coordinates back to real drawing coordinates.

    Rotation happens on two levels:
    - position: anchoring point of the character in the drawing
    - scaled_segments: segments points of the glyph, rotated around the origin (0,0) because they are already relative to position

    Args:
        sequence: TextSequence object with .sequence list of (scaled_segments, position) 
        pivot: Tuple (x, y) around which to rotate
        angle: Angle in radians

    Returns:
        The same text sequence modified in-place (for consistency with place_sequence)
    """
    for scaled_segments, position in sequence.sequence:
        # ruota il punto di ancoraggio nel disegno
        rx, ry = rotate_point(position, pivot, angle)
        position[0], position[1] = rx, ry

        # ruota i punti del glifo attorno all'origine —
        # sono coordinate relative, il pivot è (0, 0)
        for point in scaled_segments:
            if point is None:  # ← separatore di tratto, skip
                continue
            px, py = rotate_point((point[0], point[1]), (0.0, 0.0), angle)
            point[0], point[1] = px, py

    return sequence

##############################################################################
# Computation of start_y for rotated segment text sequence
##############################################################################

def comp_start_y_rotated(segs_rotated, min_y_rotated, pivot):
    # Costruisce array di punti dai segs ruotati
    points = np.array(
        [(x1, y1) for (x1, y1, x2, y2) in segs_rotated] +
        [(x2, y2) for (x1, y1, x2, y2) in segs_rotated]
    )
    
    _, y_centroide = comp_centroid(points)
    y_pivot = pivot[1]
    small_offset = 0.5
    
    if y_centroide > y_pivot:
        start_y = y_pivot - min_y_rotated + small_offset
    else:
        start_y = y_pivot - min_y_rotated - small_offset
    
    return start_y

def ref_angle_and_pivot(ref_segment):
    """
    Estrae angolo e pivot da un VirtualSegment di riferimento.

    Args:
        ref_segment: VirtualSegment (o qualsiasi oggetto con .dxf.start e .dxf.end)

    Returns:
        Tupla (angle, pivot) dove:
            angle: float in radianti
            pivot: tupla (x, y)
    """
    p1 = (ref_segment.dxf.start.x, ref_segment.dxf.start.y)
    p2 = (ref_segment.dxf.end.x, ref_segment.dxf.end.y)
    return seg_angle(p1, p2), p1
