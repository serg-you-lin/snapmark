



# # builders/standalone_marking.py

# import os
# import ezdxf
# from snapmark.mark_algorithm.sequence import rescale_sequence, sequence_dim
# from snapmark.utils.segments_dict import number_segments_dict
# from snapmark.entities.editor import add_sequence
# from snapmark.utils.messages import empty_sequence_error, standalone_mark_created, standalone_mark_missing_source_error


# def _scale_factor_for_height(segment_text, char_height):
#     """
#     Returns the scale factor such that the maximum height of the glyphs in the
#     sequence is exactly char_height (mm). Same logic as _scale_sequence_to_bounds,
#     without the min/max char limits.
#     """
#     base_scale = 1.0
#     height_raw = 0.0

#     for char in segment_text:
#         if char in number_segments_dict:
#             segments = number_segments_dict[char]
#             scaled = [
#                 None if pt is None else [pt[0] * base_scale, pt[1] * base_scale]
#                 for pt in segments
#             ]
#             valid = [pt for pt in scaled if pt is not None]
#             if not valid:
#                 continue
#             ys = [pt[1] for pt in valid]
#             height_raw = max(max(ys) - min(ys), height_raw)

#     if height_raw == 0:
#         raise ValueError('No valid characters in sequence.')

#     return base_scale / height_raw * char_height


# class StandaloneMark:
#     """
#     Generate a new DXF containing only the marking, without any source file.
#     Same algorithm as place_sequence (rescale_sequence + sequence_dim).

#     The sequence has no source file_name to read from (it generates the
#     output file name itself): .file_name() / .split_text() in the
#     SequenceBuilder will raise if used here. .folder() is valid and
#     receives output_dir.
#     """

#     def __init__(self, sequence, char_height=10, space=1.5,
#                  start_x=0, start_y=0,
#                  mark_layer='MARK', mark_color=None):
#         self.sequence = sequence
#         self.char_height = char_height
#         self.space = space
#         self.start_x = start_x
#         self.start_y = start_y
#         self.mark_layer = mark_layer
#         self.mark_color = mark_color

#     def _resolve_text(self, output_dir):
#         try:
#             return self.sequence.get_sequence_text(folder=output_dir, file_name=None)
#         except TypeError as e:
#             raise ValueError(standalone_mark_missing_source_error()) from e

#     def build(self, output_dir):
#         """Generate the ezdxf document. Does not save to disk.
#         Returns (doc, segment_text)."""
#         segment_text = self._resolve_text(output_dir)

#         if len(segment_text) == 0:
#             raise ValueError(empty_sequence_error())

#         scale_factor = _scale_factor_for_height(segment_text, self.char_height)

#         seq = rescale_sequence(segment_text, scale_factor, self.start_x, self.start_y)
#         sequence_dim(seq, self.start_x, self.start_y, self.space)

#         doc = ezdxf.new()
#         add_sequence(doc, seq, self.mark_layer, self.mark_color)
#         return doc, segment_text

#     def save(self, output_dir):
#         """Build and save. The output file name is the sequence text + '.dxf'.
#         Non solleva eccezioni: in caso di errore stampa il messaggio e ritorna None,
#         cosi' la sessione resta viva (stesso comportamento di Operation.execute_single)."""
#         try:
#             doc, segment_text = self.build(output_dir)
#         except ValueError as e:
#             print(e)
#             return None

#         output_path = os.path.join(output_dir, f"{segment_text}.dxf")
#         doc.saveas(output_path)
#         print(standalone_mark_created(segment_text, output_path))
#         return output_path



# builders/standalone_marking.py

import os
import ezdxf
from snapmark.mark_algorithm.sequence import rescale_sequence, sequence_dim
from snapmark.utils.segments_dict import number_segments_dict
from snapmark.entities.editor import add_sequence
from snapmark.utils.messages import (
    empty_sequence_error,
    standalone_mark_created,
    standalone_mark_missing_source_error,
    cannot_save_error,
)


def _scale_factor_for_height(segment_text, char_height):
    """
    Returns the scale factor such that the maximum height of the glyphs in the
    sequence is exactly char_height (mm). Same logic as _scale_sequence_to_bounds,
    without the min/max char limits.
    """
    base_scale = 1.0
    height_raw = 0.0

    for char in segment_text:
        if char in number_segments_dict:
            segments = number_segments_dict[char]
            scaled = [
                None if pt is None else [pt[0] * base_scale, pt[1] * base_scale]
                for pt in segments
            ]
            valid = [pt for pt in scaled if pt is not None]
            if not valid:
                continue
            ys = [pt[1] for pt in valid]
            height_raw = max(max(ys) - min(ys), height_raw)

    if height_raw == 0:
        raise ValueError('No valid characters in sequence.')

    return base_scale / height_raw * char_height


class StandaloneMark:
    """
    Generate a new DXF containing only the marking, without any source file.
    Same algorithm as place_sequence (rescale_sequence + sequence_dim).

    The sequence has no source file_name to read from (it generates the
    output file name itself): .file_name() / .split_text() in the
    SequenceBuilder will raise if used here. .folder() is valid and
    receives output_dir.
    """

    def __init__(self, sequence, char_height=10, space=1.5,
                 start_x=0, start_y=0,
                 mark_layer='MARK', mark_color=None):
        self.sequence = sequence
        self.char_height = char_height
        self.space = space
        self.start_x = start_x
        self.start_y = start_y
        self.mark_layer = mark_layer
        self.mark_color = mark_color

    def _resolve_text(self, output_dir):
        try:
            return self.sequence.get_sequence_text(folder=output_dir, file_name=None)
        except TypeError as e:
            raise ValueError(standalone_mark_missing_source_error()) from e

    def build(self, output_dir):
        """Generate the ezdxf document. Does not save to disk.
        Returns (doc, segment_text)."""
        segment_text = self._resolve_text(output_dir)

        if len(segment_text) == 0:
            raise ValueError(empty_sequence_error())

        scale_factor = _scale_factor_for_height(segment_text, self.char_height)

        seq = rescale_sequence(segment_text, scale_factor, self.start_x, self.start_y)
        sequence_dim(seq, self.start_x, self.start_y, self.space)

        doc = ezdxf.new()
        add_sequence(doc, seq, self.mark_layer, self.mark_color)
        return doc, segment_text

    def save(self, output_dir):
        """Build and save. The output file name is the sequence text + '.dxf'.
        Non solleva eccezioni: in caso di errore stampa il messaggio e ritorna None,
        cosi' la sessione resta viva (stesso comportamento di Operation.execute_single)."""
        try:
            doc, segment_text = self.build(output_dir)
        except ValueError as e:
            print(e)
            return None

        output_path = os.path.join(output_dir, f"{segment_text}.dxf")

        try:
            doc.saveas(output_path)
        except PermissionError:
            print(cannot_save_error(os.path.basename(output_path), "file in uso o permessi insufficienti"))
            return None
        except OSError as e:
            print(cannot_save_error(os.path.basename(output_path), str(e)))
            return None

        print(standalone_mark_created(segment_text, output_path))
        return output_path