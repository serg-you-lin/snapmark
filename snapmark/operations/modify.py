from snapmark.operations.basic_operations import Operation
from snapmark.utils.helpers import find_circle_centers
from snapmark.entities.editor import add_circle, delete_circle, add_x, delete_layer                          

class SubstituteCircle(Operation):
    """Replaces existing circles with new circles of a different radius."""

    def __init__(self, find_circle_function, new_radius=None, new_diameter=None, circle_layer='0', circle_color=None):
        super().__init__()
        self.find_circle_function = find_circle_function
        self.new_radius = new_radius 
        self.new_diameter = new_diameter
        self.circle_layer = circle_layer
        self.circle_color = circle_color

        if self.new_radius is None and self.new_diameter is None:
            raise ValueError('You must specify either new_radius or new_diameter.')

    def execute(self, doc, folder, file_name):
        holes = self.find_circle_function(doc)

        if self.new_diameter:
            self.new_radius = self.new_diameter / 2

        center_holes = find_circle_centers(holes)
        add_circle(doc, center_holes, radius=self.new_radius, circle_layer=self.circle_layer, circle_color=self.circle_color)
        delete_circle(doc, holes)

        return self.create_new
    
    def message(self, file_name):
        if self.new_diameter:
            self.message_text = f"✓ Holes in {file_name}: new diameter {self.new_diameter}"
        else:
            self.message_text = f"✓ Holes in {file_name}: new radius {self.new_radius}"
        print(self.message_text)


class AddX(Operation):
    """Adds an 'X' shape at the locations of circles."""
    
    def __init__(self, find_circle_function, x_size=8, x_layer='MARK', x_color=None, delete_hole=True):
        super().__init__()
        self.find_circle_function = find_circle_function
        self.x_size = x_size
        self.x_layer = x_layer
        self.x_color = x_color
        self.delete_hole = delete_hole

    def execute(self, doc, folder, file_name):
        holes = self.find_circle_function(doc)
        center_holes = find_circle_centers(holes)
        
        if self.delete_hole:
            delete_circle(doc, holes)
            
        add_x(doc, center_holes, x_size=self.x_size, x_layer=self.x_layer, x_color=self.x_color)
        return self.create_new
    
    def message(self, file_name):
        self.message_text = f"✓ 'X' added to {file_name}"
        print(self.message_text)


class RemoveCircle(Operation):
    """Removes circles from the file."""
    
    def __init__(self, find_circle_function):
        super().__init__()
        self.find_circle_function = find_circle_function

    def execute(self, doc, folder, file_name):
        holes = self.find_circle_function(doc)
        delete_circle(doc, holes)
        return self.create_new
    
    def message(self, file_name):
        self.message_text = f"✓ Holes removed from {file_name}"
        print(self.message_text)


class RemoveLayer(Operation):
    """Removes a layer from the file."""
    
    def __init__(self, layer):
        super().__init__()
        self.layer = layer

    def execute(self, doc, folder, file_name):
        delete_layer(doc, self.layer)
        return self.create_new

    def message(self, file_name):
        self.message_text = f"✓ Layer '{self.layer}' removed from {file_name}"
        print(self.message_text)
