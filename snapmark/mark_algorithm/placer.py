"""
placer.py

This module contains the main algorithm to find space for a sequence in a document, given its length
and height, and the document's segments. 
It also includes a helper function to check if there is enough space between interceptions for a given sequence.
"""

from pydoc import doc

from .segmenter import (comp_segs_and_limits, 
                       find_x_intercept, 
                       find_x_intercept_raw, 
                       find_intermediate_y,
                       GeometryContext
)


def find_space_for_sequence(lenght_sequence, height_sequence, ctx, align, start_y, step, margin):

    segs = ctx.segs
    min_x = ctx.min_x
    min_y = ctx.min_y
    max_x = ctx.max_x
    max_y = ctx.max_y
    avoid_segs = ctx.avoid_segs

    available_width = max_x - min_x
    available_height = max_y - min_y

    if available_width <= 2 * margin:
        return None, None

    if available_height <= 2 * margin:
        return None, None

    y = min_y + start_y
    start_x = None
    y_to_try = []

    if (height_sequence + 2 * margin) <= (max_y - min_y):
        while y < max_y - 0.5 - height_sequence:
            y_to_try.append(y)
            y += step
        y = min_y + start_y - step
        while y > min_y + 0.5:
            y_to_try.append(y)
            y -= step

        if 0.5 not in y_to_try:
            y_to_try.append(0.5)
        if max_y - height_sequence - 0.5 not in y_to_try:
            y_to_try.append(max_y - height_sequence - 0.5)

    is_space = False
    for y in y_to_try:
        x_intercept_bottom = find_x_intercept(y, segs, ctx)

        if len(x_intercept_bottom) > 1:
            x_intercept_top = find_x_intercept(y + height_sequence, segs, ctx)
            if len(x_intercept_top) > 1:

                shared_spaces_list = find_shared_spaces(x_intercept_top, x_intercept_bottom)

                if len(shared_spaces_list) > 0:
                    if align == 'r':
                        shared_spaces_list = shared_spaces_list[::-1]
                    elif align == 'c':
                        middle_point = (shared_spaces_list[0][0] + shared_spaces_list[-1][1]) / 2
                        shared_spaces_list.sort(key=lambda space: abs(middle_point - (space[0] + space[1]) / 2))

                    for spaces in shared_spaces_list:
                        is_space = find_space_between_interceptions(
                            spaces[0], spaces[1], lenght_sequence, height_sequence,
                            segs, margin, y, avoid_segs, ctx
                        )
                        if is_space:
                            x_left, x_right = spaces[0], spaces[1]
                            break

                if is_space == True:
                    if align == 'l':
                        start_x = x_left + margin
                    elif align == 'r':
                        start_x = x_right - lenght_sequence - margin
                    else:
                        start_x_middle = middle_point - (lenght_sequence / 2)
                        if x_right - (lenght_sequence/2) > middle_point > x_left + (lenght_sequence / 2):
                            start_x = start_x_middle
                        else:
                            start_x = ((x_right - x_left) - lenght_sequence) / 2 + x_left
                            if start_x > start_x_middle:
                                start_x = x_left + margin
                            else:
                                start_x = x_right - lenght_sequence - margin
                    start_y = y
                    break

    if start_x is None:
        if y_to_try == []:
            print('Sequence needs to be adjusted due to y values.')
        else:
            print('Sequence needs to be adjusted due to x values.')
        return None, None
    else:
        if start_x + lenght_sequence + margin > max_x:
            return None, None
        if start_y + height_sequence + margin > max_y:
            return None, None
        return start_x, start_y
    

def find_space_between_interceptions(x_left, x_right, lenght_sequence, height_sequence, segs, margin, y, avoid_segs=None, ctx=None):   
    """
    Checks if there is enough space between interceptions for a given sequence.

    Args:
        x_left (float): The left boundary of the space to check.
        x_right (float): The right boundary of the space to check.
        lenght_sequence (float): The length of the sequence to be placed.
        height_sequence (float): The height of the sequence to be placed.
        segs (list): A list of segments to check for interceptions.
        margin (float): The margin to be added to the sequence length.
        y (float): The y-coordinate to check for interceptions.
        avoid_segs (list, optional): A list of segments to avoid (es. bending lines, inner contours).
        ctx (GeometryContext, optional): The geometry context for caching.

    Returns:
        bool: True if there is enough space for the sequence, False otherwise.
    """           

    if (lenght_sequence + 2*margin) <= (x_right - x_left):
        y_ints = find_intermediate_y(y, y + height_sequence)
        for y_int in y_ints:
            x_intercept = find_x_intercept(y_int, segs, ctx)
            for interception in x_intercept:
                if x_right > interception > x_left:
                    return False
                
        if avoid_segs:
            for (x1, y1, x2, y2) in avoid_segs:
                if abs(y1 - y2) < 1e-6:
                    if y < y1 < y + height_sequence:
                        x_min_seg = min(x1, x2)
                        x_max_seg = max(x1, x2)
                        if x_min_seg < x_right and x_max_seg > x_left:
                            return False

        y_ints = find_intermediate_y(y, y + height_sequence)
        for y_int in y_ints:
            x_intercept = find_x_intercept(y_int, segs, ctx)         
            for interception in x_intercept:
                if x_right > interception > x_left:
                    return False

            if avoid_segs:
                x_avoid = find_x_intercept_raw(y_int, avoid_segs)
                if len(x_avoid) >= 2:
                    mid = (x_left + x_right) / 2
                    for i in range(0, len(x_avoid) - 1, 2):
                        if x_avoid[i] < mid < x_avoid[i+1]:
                            return False
                    for interception in x_avoid:
                        if x_left < interception < x_right:
                            return False
                
        return True
    else:
        return False
    
  

def find_shared_spaces(top_interceptions, bottom_interceptions):
    """
    Finds shared spaces between top and bottom interceptions.

    Args:
        top_interceptions (list): A list of x-coordinates for the top interceptions.
        bottom_interceptions (list): A list of x-coordinates for the bottom interceptions.

    Returns:
        list: A list of tuples representing shared spaces, where each tuple contains the start and end x-coordinates.
    """
    combined_interceptions = []
    for i, t_intercept in enumerate(top_interceptions):
        if i % 2 == 0:
            combined_interceptions.append((t_intercept, 'true t'))
        else:
            combined_interceptions.append((t_intercept, 'false t'))

    for i, b_intercept in enumerate(bottom_interceptions):
        if i % 2 == 0:
            combined_interceptions.append((b_intercept, 'true b'))
        else:
            combined_interceptions.append((b_intercept, 'false b'))

    combined_interceptions.sort(key = lambda interc: interc[0])
    top_statement = None
    bottom_statement = None
    top_filled_part_start = None
    bottom_filled_part_start = None
    shared_spaces = []
    for interc in combined_interceptions:
        if interc[1].endswith('t'):
            top_statement = interc[1]
            if top_statement == 'true t':
                top_filled_part_start = interc[0]
            else:
                if bottom_statement == 'true b':
                    shared_spaces.append((max(top_filled_part_start, bottom_filled_part_start), interc[0]))
        else:
            bottom_statement = interc[1]
            if bottom_statement == 'true b':
                bottom_filled_part_start = interc[0]
            else:
                if top_statement == 'true t':
                    shared_spaces.append((max(top_filled_part_start, bottom_filled_part_start), interc[0]))

    return shared_spaces 
          

    