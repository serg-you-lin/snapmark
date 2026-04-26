"""
__init__.py

Public API of the mark_algorithm package, which includes functions for placing text and sequences in a DXF document, as well as the main algorithm to find space for a sequence based on the document's geometry.
"""

from .placer import find_space_for_sequence
from .segmenter import GeometryContext, comp_center_point, comp_start_point, comp_segs_and_limits
from .sequence import SequenceText, rescale_sequence, sequence_dim, comp_text_bbox, comp_sf
from .segment_text_geometry import rotate_segment_text_sequence, ref_angle_and_pivot, comp_start_y_rotated
from snapmark.utils.geometry import rotate_segs
from snapmark.utils.segments_dict import number_segments_dict


def place_text(doc, texts, min_char, excluded_layers=None, avoid_layers=None,
               align='l', start_y=1, step=2, margin=1, debug_bbox=True):
    """
        Finds an available position for real DXF text entities (using font metrics) 
        within the document, avoiding collisions with existing geometry.

        Args:
            doc: ezdxf document.
            texts: List of strings to be placed.
            min_char: Font height used for bounding box calculation.
            excluded_layers: Layers to ignore during collision check.
            avoid_layers: Specific layers to treat as obstacles.
            align: Horizontal alignment ('l', 'c', 'r').
            start_y: Initial Y coordinate for the search.
            step: Vertical increment for finding free space.
            margin: Safety buffer around the text bounding box.
            debug_bbox: If True, draws a rectangle on 'DEBUG_TEXTBOX' layer.

        Returns:
            tuple: (x, y, width, height) or (None, None, width, height) if no space is found.
        """

    if all(len(text) == 0 for text in texts):
        raise Exception('Empty text.')

    width, height = comp_text_bbox(texts, min_char)

    ctx = GeometryContext(doc, excluded_layers, avoid_layers)

    x, y = find_space_for_sequence(
        width, height, ctx, align, start_y, step, margin
    )

    if x is None or y is None:
        return None, None, width, height

    if debug_bbox:
        ctx.msp.add_lwpolyline([
            (x, y), (x + width, y),
            (x + width, y + height),
            (x, y + height), (x, y)
        ], dxfattribs={'layer': 'DEBUG_TEXTBOX', 'color': 1})

    return x, y, width, height


def place_sequence(doc, segment_text, scale_factor, excluded_layers=None, avoid_layers=None, space=1.5,
                   min_char=5, max_char=20, arbitrary_x=None, arbitrary_y=None, align='c',
                   start_y=1, step=2, margin=1, down_to=None, ref_entity=None,
                   forced_height=None, forced_width=None):

    """
        Finds an available position for segment texts representing an alphanumeric sequence (using custom geometry)
        within the document, avoiding collisions with existing geometry.
    
        Args:
            doc: ezdxf document.
            text: String to be placed.
            scale_factor: Factor by which to scale the sequence.
            excluded_layers: Layers to ignore during collision check.
            avoid_layers: Specific layers to treat as obstacles.
            align: Horizontal alignment ('l', 'c', 'r').
            start_y: Initial Y coordinate for the search.
            step: Vertical increment for finding free space.
            margin: Safety buffer around the text bounding box.
            down_to: Minimum Y limit for the search.
            debug_bbox: If True, draws a rectangle on 'DEBUG_TEXTBOX' layer.

        Returns:
            tuple: (x, y, width, height) or (None, None, width, height) if no space is found.
        """

    if len(segment_text) == 0:
        raise Exception('Empty sequence.')

    ctx = GeometryContext(doc, excluded_layers, avoid_layers
                          )
    msp = ctx.msp
    segs = ctx.segs
    is_2d = ctx.is_2d

    sequence = SequenceText()
    height_sequence = 0.0

    x_pos = 0 if arbitrary_x is None else arbitrary_x
    y_pos = 0 if arbitrary_y is None else arbitrary_y

    for char in segment_text:
        if char in number_segments_dict:
            segments = number_segments_dict[char]
            scaled_segments = [
                None if pt is None else [pt[0] * scale_factor, pt[1] * scale_factor]
                for pt in segments
            ]
            valid = [pt for pt in scaled_segments if pt is not None]
            if not valid:
                continue
            ys = [pt[1] for pt in valid]
            number_height = max(ys) - min(ys)
            height_sequence = max(number_height, height_sequence)

    if height_sequence < min_char:
        scale_factor = scale_factor / height_sequence * min_char
        sequence = rescale_sequence(segment_text, scale_factor, x_pos, y_pos)
    elif height_sequence > max_char:
        scale_factor = scale_factor / height_sequence * max_char
        sequence = rescale_sequence(segment_text, scale_factor, x_pos, y_pos)
    else:
        sequence = rescale_sequence(segment_text, scale_factor, x_pos, y_pos)

    lenght_sequence, height_sequence = sequence_dim(sequence, x_pos, y_pos, space)

    # 🔴 FAIL FAST GEOMETRICO
    available_width = ctx.max_x - ctx.min_x
    available_height = ctx.max_y - ctx.min_y

    if (lenght_sequence + 2 * margin) > available_width:
        return SequenceText()  # non piazzabile

    if (height_sequence + 2 * margin) > available_height:
        return SequenceText()  # non piazzabile

    if forced_height is not None:
        height_sequence = forced_height
    if forced_width is not None:
        lenght_sequence = forced_width

    if arbitrary_x is not None and arbitrary_y is not None:
        for scaled_segments, position in sequence.sequence:
            position[0] += arbitrary_x
            position[1] += arbitrary_y
        return sequence

    if down_to is None:
        down_to = min_char

    # ── ATTEMPT 1: original system ────────────────────────────────
    x, y = find_space_for_sequence(
        lenght_sequence, height_sequence, ctx, align, start_y, step, margin
    )

    while x is None or y is None:
        rescale_factor = 0.8
        new_height_sequence = height_sequence * rescale_factor
        if new_height_sequence < down_to:
            break
        scale_factor = scale_factor * rescale_factor
        sequence = rescale_sequence(segment_text, scale_factor, x_pos, y_pos)
        lenght_sequence, height_sequence = sequence_dim(sequence, x_pos, y_pos, space)

        # 🔴 BLOCCO GEOMETRICO DURANTE SCALING
        if (lenght_sequence + 2 * margin) > available_width:
            break

        if (height_sequence + 2 * margin) > available_height:
            break

        x, y = find_space_for_sequence(
            lenght_sequence, height_sequence, ctx, align, start_y, step, margin
        )

    if x is not None and y is not None:
        for scaled_segments, position in sequence.sequence:
            position[0] += x
            position[1] += y
        return sequence

    # ── ATTEMPT 2: rotated system around the reference entity ───────────
    from snapmark.utils.geometry import lwpolylines_to_virtual_segments, find_longer_entity
    lines = list(msp.query('LINE'))
    lwpolylines = list(msp.query('LWPOLYLINE'))
    all_candidates = lines + lwpolylines_to_virtual_segments(lwpolylines)

    if not all_candidates:
        return SequenceText()

    if ref_entity is None:
        ref_entity, _ = find_longer_entity(all_candidates)

    ref_angle, ref_pivot = ref_angle_and_pivot(ref_entity)

    segs_rotated = rotate_segs(segs, ref_pivot, -ref_angle)
    avoid_segs_rotated = rotate_segs(ctx.avoid_segs, ref_pivot, -ref_angle) if ctx.avoid_segs else None

    all_x_r = [v for seg in segs_rotated for v in (seg[0], seg[2])]
    all_y_r = [v for seg in segs_rotated for v in (seg[1], seg[3])]
    min_x_r = min(all_x_r)
    min_y_r = min(all_y_r)
    max_x_r = max(all_x_r)
    max_y_r = max(all_y_r)

    segments_cache = (segs_rotated, min_x_r, min_y_r, max_x_r, max_y_r, is_2d)
    x_intercept_cache.clear()

    start_y_r = comp_start_y_rotated(segs_rotated, min_y_r, ref_pivot)

    x, y = find_space_for_sequence(
        lenght_sequence, height_sequence, ctx, align, start_y_r, step, margin
    )

    if x is not None and y is not None:
        for scaled_segments, position in sequence.sequence:
            position[0] += x
            position[1] += y
        sequence = rotate_segment_text_sequence(sequence, ref_pivot, ref_angle)
        return sequence

    return SequenceText()