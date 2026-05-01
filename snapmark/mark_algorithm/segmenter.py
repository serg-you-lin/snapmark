"""
segmenter.py

module that contains the main algorithm to find space for a sequence in a document, given its length and height, and the document's segments. 
It also includes a helper function to check if there is enough space between interceptions for a given sequence.    
"""
import ezdxf
import numpy as np  
from snapmark.utils.messages import dxf_3d_geometry_error
from snapmark.utils.helpers import is_excluded_layer
from snapmark.utils.geometry import lwpolyline_to_segs

MIN_ARC_SEGS = 15

# # Global variable to store all y values, allowing retrieval if y has already been calculated.
# x_intercept_cache = {}

# # Global variable to cache segments and avoid recalculation
# segments_cache = None

class GeometryContext:
    def __init__(self, doc, excluded_layers=None, avoid_layers=None):
        msp = doc.modelspace()
        self.segs, self.min_x, self.min_y, self.max_x, self.max_y, self.is_2d = \
            comp_segs_and_limits(msp, excluded_layers)
        
        if not self.is_2d:
            file_name = doc.filename if hasattr(doc, 'filename') else 'unknown file'
            raise ValueError(dxf_3d_geometry_error(file_name))
        
        self.msp = msp
        self.avoid_segs = comp_avoid_segs(msp, avoid_layers) if avoid_layers else None
        self.x_intercept_cache = {}

    @classmethod
    def from_rotated(cls, original_ctx, segs_rotated, avoid_segs_rotated,
                     min_x_r, min_y_r, max_x_r, max_y_r):
        """Crea un ctx con geometria ruotata, senza rileggere il doc."""
        obj = cls.__new__(cls)
        obj.msp = original_ctx.msp
        obj.is_2d = original_ctx.is_2d
        obj.segs = segs_rotated
        obj.avoid_segs = avoid_segs_rotated
        obj.min_x = min_x_r
        obj.min_y = min_y_r
        obj.max_x = max_x_r
        obj.max_y = max_y_r
        obj.x_intercept_cache = {}
        return obj
    

# Trasforma ogni entità in lista di segmenti espressi in tuple.
def comp_segs_and_limits(msp, excluded_layers=None):
    """
    Converts entities in the model space to a list of line segments and their limits.

    Args:
        msp: The model space containing the entities to be processed.
        excluded_layers: list of layers to skip entirely.

    Returns:
        A tuple containing:
            - tot_segs: A list of segments represented as tuples (start_x, start_y, end_x, end_y).
            - min_x: The minimum x-coordinate among all segments.
            - min_y: The minimum y-coordinate among all segments.
            - max_x: The maximum x-coordinate among all segments.
            - max_y: The maximum y-coordinate among all segments.
            - is_2d: True if all geometry is 2D, False if 3D geometry detected.
    """

    if excluded_layers is None:
        excluded_layers = []
    elif isinstance(excluded_layers, str):
        excluded_layers = [excluded_layers]

    def skip(entity):
        return is_excluded_layer(entity.dxf.layer, excluded_layers)
    
    # Initializes lists for arcs and lines
    round_segs = []
    line_segs = []
    is_2d = True
    
    # Finds the minimum and maximum coordinate values among all lines    
    for entity in msp.query('LINE'):
        if skip(entity):
            continue
        start_point = entity.dxf.start
        end_point = entity.dxf.end
        line_segs.append((start_point.x, start_point.y, end_point.x, end_point.y))
        if start_point.z != 0 or end_point.z != 0:
            is_2d = False   

    for entity in msp.query('LWPOLYLINE'):
        if skip(entity):
            continue
        line_segs.extend(lwpolyline_to_segs(entity, MIN_ARC_SEGS))

    for entity in msp.query('POLYLINE'):
        if skip(entity):
            continue
        
        # Solo 2D polyline
        if entity.get_mode() != 'AcDb2dPolyline':
            continue
        
        verts = entity.vertices 
        if len(verts) < 2:
            continue

        for i in range(len(verts) - 1):
            x1 = verts[i].dxf.location.x
            y1 = verts[i].dxf.location.y
            z1 = verts[i].dxf.location.z
            x2 = verts[i+1].dxf.location.x
            y2 = verts[i+1].dxf.location.y
            z2 = verts[i+1].dxf.location.z
            line_segs.append((x1, y1, x2, y2))
            if z1 != 0 or z2 != 0:
                is_2d = False

        if entity.is_closed:
            x1 = verts[-1].dxf.location.x
            y1 = verts[-1].dxf.location.y
            x2 = verts[0].dxf.location.x
            y2 = verts[0].dxf.location.y
            line_segs.append((x1, y1, x2, y2))

    for entity in msp.query('CIRCLE ARC'):
        if skip(entity):
            continue

        if entity.dxftype() == 'CIRCLE':
            if entity.dxf.center.z != 0:
                is_2d = False
            center_x, center_y = entity.dxf.center.x, entity.dxf.center.y
            rad = entity.dxf.radius
            num_segment = MIN_ARC_SEGS + rad//2

            ang = np.linspace(0, 2 * np.pi, int(num_segment) + 1)
            x = center_x + rad * np.cos(ang)
            y = center_y + rad * np.sin(ang)
            coords = list(zip(x, y))
            circ_segs = [(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1]) for i in range(0, len(coords) - 2)]
            circ_segs.append((coords[-1][0], coords[-1][1], coords[0][0], coords[0][1]))
            round_segs.extend(circ_segs)

        elif entity.dxftype() == 'ARC':
            if entity.dxf.center.z != 0:
                is_2d = False
            center_x, center_y = entity.dxf.center.x, entity.dxf.center.y
            rad = entity.dxf.radius
            start_angle = np.radians(entity.dxf.start_angle)
            final_angle = np.radians(entity.dxf.end_angle)
            if start_angle > final_angle:
                final_angle += 2 * np.pi
            num_segment = MIN_ARC_SEGS + (rad//2) * ((final_angle - start_angle) / (2 * np.pi))

            ang = np.linspace(start_angle, final_angle, int(num_segment) + 1)
            x = center_x + rad * np.cos(ang)
            y = center_y + rad * np.sin(ang)
            coords = list(zip(x, y))
            arc_segs = [(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1]) for i in range(0, len(coords) - 2)]
            round_segs.extend(arc_segs)

            
    tot_segs = round_segs + line_segs
    
    # Initializes the minimum and maximum coordinate values
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for (start_x, start_y, end_x, end_y) in tot_segs:        
        min_x = min(min_x, start_x, end_x)
        min_y = min(min_y, start_y, end_y)
        max_x = max(max_x, start_x, end_x)
        max_y = max(max_y, start_y, end_y)

    return tot_segs, min_x, min_y, max_x, max_y, is_2d


def comp_avoid_segs(msp, avoid_layers):
    """
    Extracts segments ONLY from layers in avoid_layers.
    Used to calculate real obstacles to avoid (e.g., bending lines) without affecting the drawing limits.

    Args:
        msp: The model space of the DXF document.
        avoid_layers: List of layers from which to extract segments.

    Returns:    
        List of tuples (x1, y1, x2, y2) of the found segments.
    """
    if not avoid_layers:
        return []

    if isinstance(avoid_layers, str):
        avoid_layers = [avoid_layers]

    avoid_segs = []

    for entity in msp.query('LINE'):
        if entity.dxf.layer in avoid_layers:
            s = entity.dxf.start
            e = entity.dxf.end
            avoid_segs.append((s.x, s.y, e.x, e.y))

    for entity in msp.query('LWPOLYLINE'):
        if entity.dxf.layer in avoid_layers:
            verts = list(entity.get_points(format='xy'))
            for i in range(len(verts) - 1):
                x1, y1 = verts[i]
                x2, y2 = verts[i + 1]
                avoid_segs.append((x1, y1, x2, y2))
            if entity.closed and len(verts) >= 2:
                x1, y1 = verts[-1]
                x2, y2 = verts[0]
                avoid_segs.append((x1, y1, x2, y2))

        for entity in msp.query('TEXT'):
            if entity.dxf.layer in avoid_layers:
                # bounding box approssimativo del testo
                x = entity.dxf.insert.x
                y = entity.dxf.insert.y
                h = entity.dxf.char_height
                w = len(entity.text) * h * 0.6
                avoid_segs.append((x, y, x + w, y))          # bottom
                avoid_segs.append((x, y + h, x + w, y + h))  # top
                avoid_segs.append((x, y, x, y + h))           # left
                avoid_segs.append((x + w, y, x + w, y + h))  # right

    return avoid_segs


def find_x_intercept_raw(y, segs):
    """Finds x-intercepts for a given y value without caching — usato per avoid_segs."""
    x_intercept = []
    for (start_x, start_y, end_x, end_y) in segs:
        if start_y >= y >= end_y or start_y <= y <= end_y:
            if start_y != end_y:
                x = (y - start_y)/(end_y - start_y) * (end_x - start_x) + start_x
                x_intercept.append(x)
    x_intercept.sort()
    return x_intercept


def find_x_intercept(y, segs, ctx=None):
    key = round(y, 3)
    cache = ctx.x_intercept_cache if ctx is not None else {}
    
    if key in cache:
        return cache[key]
    
    x_intercept = []
    for (start_x, start_y, end_x, end_y) in segs:
        if start_y >= y >= end_y or start_y <= y <= end_y:
            if start_y != end_y:
                x = (y - start_y)/(end_y - start_y) * (end_x - start_x) + start_x
                x_intercept.append(x)
    
    x_intercept.sort()
    if ctx is not None:
        cache[key] = x_intercept
    return x_intercept
    

def find_intermediate_y(bottom_y, top_y, int_step=2):
    """Finds intermediate y values between bottom and top for potential intersections."""
    steps = []
    first_int = (bottom_y // int_step) * int_step + int_step
    int_y = first_int
    while int_y < top_y:
        steps.append(int_y)
        int_y += int_step
        
    return steps


def comp_center_point(doc):
    """Calculates the center point of all lines in the DXF document."""
    msp = doc.modelspace()
    
    # Inizializes the minimum and maximum coordinate values
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    # Find the minimum and maximum coordinate values among all lines
    for entity in msp.query('LINE'):
        start_point = entity.dxf.start
        end_point = entity.dxf.end
        min_x = min(min_x, start_point.x, end_point.x)
        min_y = min(min_y, start_point.y, end_point.y)
        max_x = max(max_x, start_point.x, end_point.x)
        max_y = max(max_y, start_point.y, end_point.y)

    # Calcola il punto centrale
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    return center_x, center_y


def comp_start_point(doc, x_pos=1, y_pos=1):
    """Calculates a starting point based on the minimum coordinates of lines in the DXF document."""
    msp = doc.modelspace()
    
    # Inizialize the minimum and maximum coordinate values
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    # Trova i valori minimi e massimi delle coordinate tra tutte le linee
    for entity in msp.query('LINE'):
        start_point = entity.dxf.start
        end_point = entity.dxf.end
        min_x = min(min_x, start_point.x, end_point.x)
        min_y = min(min_y, start_point.y, end_point.y)
        max_x = max(max_x, start_point.x, end_point.x)
        max_y = max(max_y, start_point.y, end_point.y)

    # Calcola il punto centrale
    start_x = min_x + x_pos
    start_y = min_y + y_pos

    return start_x, start_y
