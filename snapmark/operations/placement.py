from snapmark.operations.basic_operations import Operation
from snapmark.mark_algorithm import (place_sequence, 
                                    comp_sf,
                                    comp_center_point,
                                    SequenceText,
                                    place_text,
                                    comp_segs_and_limits
                                )

from snapmark.entities.editor import add_numbers_to_layer

class AddMark(Operation):
    """Adding numeric marking to DXF files."""
    
    def __init__(self, sequence, scale_factor=50, space=1.5, min_height=5,
                 max_height=20, arbitrary_x=None, arbitrary_y=None, align='c',
                 start_y=1, step=2, margin=1, down_to=None, mark_layer='MARK', 
                 mark_color=None, excluded_layers=None, avoid_layers=None):
        super().__init__()
        self.sequence = sequence
        self.scale_factor = scale_factor
        self.space = space
        self.min_char_height = min_height
        self.max_char_height = max_height
        self.arbitrary_x = arbitrary_x
        self.arbitrary_y = arbitrary_y
        self.align = align
        self.start_y = start_y
        self.step = step
        self.margin = margin
        self.down_to = down_to
        self.mark_layer = mark_layer
        self.avoid_layers = avoid_layers
        self.mark_color = mark_color
        self.excluded_layers = excluded_layers
        self.sequence_position = SequenceText()

    def __repr__(self):
        return f"AddMark(sequence={self.sequence})"

    def execute(self, doc, folder, file_name):
        """Legacy method - maintains original logic for compatibility."""
        scale_factor = comp_sf(doc, self.scale_factor)
        sequence = self.sequence.get_sequence_text(folder, file_name)
        
        start_x, start_y = comp_center_point((doc))

        seq = place_sequence(
            doc, sequence, scale_factor, self.excluded_layers, self.avoid_layers, self.space, 
            self.min_char_height, self.max_char_height, self.arbitrary_x, self.arbitrary_y, 
            self.align, self.start_y, self.step, self.margin, self.down_to
        )

        # 🔴 BLOCCO: se non piazzabile → sequenza vuota
        if seq is None or len(seq.sequence) == 0:
            self.sequence_position = SequenceText()  # vuota
            return self.create_new
        
        # controlla se è stata traslata
        first_pos = seq.sequence[0][1]

        if first_pos[0] == 0 and first_pos[1] == 0:
            # non è stata piazzata
            self.sequence_position = SequenceText()
            return self.create_new

        self.sequence_position = seq
        add_numbers_to_layer(doc, self.sequence_position, self.mark_layer, self.mark_color)

        return self.create_new
                     
    def message(self, file_name):
        if len(self.sequence_position.sequence) == 0:
            self.message_text = f"⚠ No space found for the sequence in file {file_name}." 
        else:
            self.message_text = f"✓ Sequence added to {file_name}"
        print(self.message_text)


class AddText(Operation):
    """Aggiunge entità testo ai file DXF tramite l'algoritmo di posizionamento."""

    def __init__(
        self,
        text_sequence,         
        char_height=2,
        align='l',
        start_y=1,
        step=2,
        margin=1,
        text_layer='TEXT',
        text_color=30,
        excluded_layers=None,
        avoid_layers=None,
        text_bbbox=False,
        **kwargs
    ):
        super().__init__()

        self.text_sequence = text_sequence

        self.char_height = char_height
        self.align = align
        self.start_y = start_y
        self.step = step
        self.margin = margin

        self.text_layer = text_layer
        self.text_color = text_color

        self.excluded_layers = excluded_layers
        self.avoid_layers = avoid_layers

        self.extra = kwargs
        self.text_position = None
        self.text_bbbox = text_bbbox

    def __repr__(self):
        return f"AddText(text_sequence={self.text_sequence})"

    def execute(self, doc, folder, file_name):

        # ─────────────────────────────
        # 1. Solve lines        
        # ─────────────────────────────
        texts = self.text_sequence.get_lines(folder, file_name)

        if not texts:
            self.text_position = None
            return self.create_new

        # ─────────────────────────────
        # 2. Find position
        # ─────────────────────────────
        x, y, estimated_width, real_height = place_text(
            doc, texts, self.char_height,
            self.excluded_layers, self.avoid_layers,
            self.align, self.start_y, self.step, self.margin, self.text_bbbox
        )

        if x is None or y is None:
            self.text_position = None
            return self.create_new

        # ─────────────────────────────
        # 3. OUTPUT DXF
        # ─────────────────────────────
        msp = doc.modelspace()

        for i, text in enumerate(reversed(texts)):
            dxfattribs = {'layer': self.text_layer}
            if self.text_color is not None:
                dxfattribs['color'] = self.text_color

            mt = msp.add_mtext(text, dxfattribs=dxfattribs)
            mt.dxf.char_height = self.char_height
            mt.dxf.attachment_point = 7
            mt.set_location((x, y + i * self.char_height * 2.0))

        self.text_position = (x, y)
        return self.create_new

    def message(self, file_name):
        if self.text_position is None:
            self.message_text = f"⚠ No space found for text in file {file_name}."
        else:
            self.message_text = f"✓ Text added to {file_name}"
        print(self.message_text)
