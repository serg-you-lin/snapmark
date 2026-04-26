
"""
sequence.py

This module defines the SequenceText class, which represents an alphanumeric sequence composed of scaled segments and positions.
"""

from snapmark.utils.segments_dict import number_segments_dict
from .segmenter import comp_segs_and_limits

# Class to define the alphanumeric sequence composed of scaled segments and positions, to be used for text placement.
class SequenceText:
    def __init__(self):
        self.sequence = []

    def add_number(self, number, position):
        self.sequence.append((number, position))


# Rescale sequence if necessary
def rescale_sequence(text, scale_factor, start_x, start_y):
    sequence = SequenceText()
    for i, char in enumerate(text):
         if char in number_segments_dict:
              # Get the segments for the specified number (from the implemented dictionary)
              segments = number_segments_dict[char]
              scaled_segments = [
                    None if pt is None else [pt[0] * scale_factor, pt[1] * scale_factor]
                    for pt in segments
                ]
              sequence.add_number(scaled_segments, [start_x, start_y])
    return sequence
             

def sequence_dim(sequence, x_pos, y_pos, space):
    """
    Calculates the dimensions of a sequence and updates the positions of its components.

    Args:
        sequence: An object containing the sequence of segments and their positions.
        x_pos (float): The initial x-coordinate for positioning the sequence.
        y_pos (float): The initial y-coordinate for positioning the sequence (not used in calculations).
        space (float): The spacing factor between characters in the sequence.

    Returns:
        tuple: A tuple containing:
            - lenght_sequence (float): The total length of the sequence after accounting for spacing.
            - height_sequence (float): The maximum height of the sequence components.

    Overview:
        This function iterates through the segments of the sequence to calculate the total width and height.
        It updates the x-coordinate for each segment based on the specified spacing and returns the total dimensions.
    """

    x_position = x_pos
    lenght_sequence = 0.0
    height_sequence = 0.0

    for scaled_segments, position in sequence.sequence:
        valid = [pt for pt in scaled_segments if pt is not None]

        if not valid:
            continue

        xs = [pt[0] for pt in valid]
        ys = [pt[1] for pt in valid]

        number_width = max(xs) - min(xs)
        number_height = max(ys) - min(ys)

        height_sequence = max(number_height, height_sequence)

        if number_width == 0:
            number_width = number_height / 2

        position[0] = x_position
        x_position += number_width * space
        lenght_sequence += number_width * space

    return lenght_sequence, height_sequence



def comp_sf(doc, scale_factor=50):
    extmax = doc.header.get('$EXTMAX')
    extmin = doc.header.get('$EXTMIN')

    # Header mancante o valori sentinella (file vecchi)
    if extmin is None or extmax is None or abs(extmax[0]) > 1e15:
        msp = doc.modelspace()
        _, min_x, min_y, max_x, max_y, _ = comp_segs_and_limits(msp)
        drawing_width = max_x - min_x
        drawing_height = max_y - min_y
    else:
        drawing_width = abs(extmax[0] - extmin[0])
        drawing_height = abs(extmax[1] - extmin[1])

    return min(drawing_width, drawing_height) / scale_factor


def comp_text_bbox(texts, min_char):
    """Computes the actual dimensions of the bounding box for multiline text."""
    n = len(texts)
    longest = max(texts, key=len)
    width = len(longest) * min_char * 0.9
    height = n * min_char * 2.0
    return width, height
