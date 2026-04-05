# ✅ metti questi
from snapmark.operations.basic_operations import Operation
from snapmark.utils.geometry import (
    lwpolylines_to_virtual_segments,
    find_longer_entity,
    rotate_point,
)
import math
from ezdxf.math import Vec3


class Aligner(Operation):
    """
    A class to align entities in a DXF document based on the longest line.

    Attributes:
        create_new (bool): Indicates whether to create a new alignment (default is True).
    """

    def __init__(self):
        """Initializes the Aligner with the option to create a new alignment."""
        super().__init__()
        self.create_new = True

    def execute(self, doc, folder, file_name): 
        """
        Executes the alignment operation on the entities in the given DXF document.

        Args:
            doc: The DXF document containing the entities to be aligned.
            folder: The folder where the document is located (not used in this method).
            file_name: The name of the DXF file (not used in this method).

        Returns:
            bool: Indicates whether a new alignment was created.
        """

        msp = doc.modelspace()

        circles, arcs, lines, ellipses, lwpolylines = iter_on_all_entities(msp) 

        # costruisce lista unificata: LINE reali + segmenti virtuali da LWPOLYLINE
        virtual_segments = lwpolylines_to_virtual_segments(lwpolylines)
        all_candidates = lines + virtual_segments  # find_longer_entity non vede la differenza
        
        num_entities = len(lines + arcs + circles + ellipses + lwpolylines)
        if len(msp.query()) > num_entities:
            print("Some entities are not supported for alignment and will be ignored.")

        if len(all_candidates) > 0:
            side, longest_side_is_below = find_longer_entity(all_candidates)
        else:
            side = None

        if side is not None:
            # print("Side: ", side)
            pp = get_pivot_point(side)
            angolo = comp_inclination(side)
                       
            add_rotated_entities_to_msp(msp, lines, arcs, circles, ellipses, lwpolylines, pp, angolo)

            # ricalcola dopo la rotazione
            circles, arcs, lines, ellipses, lwpolylines = iter_on_all_entities(msp)
            virtual_segments = lwpolylines_to_virtual_segments(lwpolylines)
            all_candidates = lines + virtual_segments

            side, longest_side_is_below = find_longer_entity(all_candidates)
            pp = get_pivot_point(side)

            if longest_side_is_below == False:
                self.flip_file(msp, lines, arcs, circles, ellipses, lwpolylines, pp, side)
            else:
                print("No lines found in the DXF file. Alignment not performed.")
            


        return self.create_new

    def message(self, file_name):
        print(f"{file_name} aligned to the longest edge along the X-axis.")

    def flip_file(self, msp, lines, arcs, circles, ellipses, lwpolylines, pp, longer_side):
        """
        Rotates the entities in the model space by 180 degrees based on the longest edge.

        Args:
            msp: The model space containing the entities to be rotated.
            lines: A list of line entities to be rotated.
            arcs: A list of arc entities to be rotated.
            circles: A list of circle entities to be rotated.
            ellipses: A list of ellipse entities to be rotated.
            lwpolylines: A list of LWPOLYLINE entities to be rotated.
            pp: The pivot point around which the entities will be rotated.
            longer_edge: The longest edge used to determine the rotation angle.

        Overview:
            This method calculates the angle of inclination of the longest edge and rotates the entities in the model space
            by 180 degrees. It adjusts the angle based on whether it is less than or greater than π (180 degrees).
        """
        print('file rotated by 180°')
        
        rad_angle = comp_inclination(longer_side)

        if rad_angle < math.pi:
            rad_angle = rad_angle + math.pi
            
        else:
            rad_angle = rad_angle - math.pi
       
        add_rotated_entities_to_msp(msp, lines, arcs, circles, ellipses, lwpolylines, pp, rad_angle)

    

################################################################################################    


def add_rotated_entities_to_msp(msp, lines, arcs, circles, ellipses, lwpolylines, pivot, angle):
    """
    Rotates entities (lines, arcs, circles, ellipses) around a pivot point by a specified angle.

    Args:
        msp: The model space where the entities will be added.
        lines (list): A list of line entities to be rotated.
        arcs (list): A list of arc entities to be rotated.
        circles (list): A list of circle entities to be rotated.
        ellipses (list): A list of ellipse entities to be rotated.
        lwpolylines (list): A list of LWPOLYLINE entities to be rotated.
        pivot (tuple): The pivot point (x, y) around which the entities will be rotated.
        angle (float): The angle in radians by which to rotate the entities.

    Overview:
        This function rotates each type of entity around the specified pivot point and adds the rotated entities
        to the model space while deleting the original entities.
    """

    for l in lines:
        rotated_line = rotate_line_by_pivot_point(l, pivot, -1*angle)    
        msp.add_entity(rotated_line)    
        msp.delete_entity(l)
   
    for c in circles:
        rotated_circle = rotate_circle_by_pp(c, pivot, -1*angle)
        msp.add_entity(rotated_circle)
        msp.delete_entity(c)

    for a in arcs:
        rotated_arc = rotate_arc_by_pp(a, pivot, -1*angle)
        msp.add_entity(rotated_arc)
        msp.delete_entity(a)

    for e in ellipses:
        rotated_ellipse = rotate_ellipse_by_pp(e, pivot, -1*angle)
        msp.add_entity(rotated_ellipse)
        msp.delete_entity(e)

    for lw in msp.query('LWPOLYLINE'):
        rotated_lwpoly = rotate_lwpolyline_by_pp(lw, pivot, -1*angle)
        msp.add_entity(rotated_lwpoly)
        msp.delete_entity(lw)

def comp_inclination(entity):
    """
    Computes the angle of inclination of a line entity.

    Args:
        entity: The line entity for which to calculate the inclination.

    Returns:
        float: The angle of inclination in radians.
    """

    if entity.dxf.end.x > entity.dxf.start.x:
        deltaX = entity.dxf.end.x - entity.dxf.start.x
        deltaY = entity.dxf.end.y - entity.dxf.start.y
    else:
        deltaX = entity.dxf.start.x - entity.dxf.end.x
        deltaY = entity.dxf.start.y - entity.dxf.end.y

    angolo_rad = math.atan2(deltaY, deltaX)
   
    return angolo_rad


def get_pivot_point(entity):
    """Returns the starting point of the entity as the pivot point."""
    return entity.dxf.start.x, entity.dxf.start.y

def iter_on_all_entities(msp):
    """
    Iterates through all entities in the model space and categorizes them.

    Args:
        msp: The model space from which to extract entities.

    Returns:
        tuple: A tuple containing lists of circles, arcs, lines, and ellipses.
    """

    lines = []
    arcs = []
    circles = []
    ellipses = []
    lwpolylines = []
    
    for entity in msp.query('CIRCLE'):
        circles.append(entity)
    for entity in msp.query('ARC'):
        arcs.append(entity)
    for entity in msp.query('LINE'):
        lines.append(entity)
    for entity in msp.query('ELLIPSE'):
        ellipses.append(entity)
    for entity in msp.query('LWPOLYLINE'):
        lwpolylines.append(entity)

    return circles, arcs, lines, ellipses, lwpolylines


################################################################################################    
################################################################################################    


def rotate_circle_by_pp(circle, pivot, angle):
    """Rotates a circle around a pivot point by a specified angle."""
    radius = circle.dxf.radius
    rotated_center_x, rotated_center_y = rotate_point(circle.dxf.center, pivot, angle)

    #rotated_circle = circle.new()
    rotated_circle = circle.copy()
    rotated_circle.dxf.center = (rotated_center_x, rotated_center_y)
    rotated_circle.dxf.radius = radius
    
    return rotated_circle

def rotate_arc_by_pp(arc, pivot, angle):
    """Rotates an arc around a pivot point by a specified angle."""
    radius = arc.dxf.radius
    rotated_start_angle = deg_to_rad(arc.dxf.start_angle) + angle
    rotated_end_angle = deg_to_rad(arc.dxf.end_angle) + angle
    if rotated_start_angle >= 2*math.pi:
        rotated_start_angle = rotated_start_angle - 2*math.pi
        if rotated_end_angle >= 2*math.pi:
            rotated_end_angle = rotated_end_angle - 2*math.pi
        else:
            rotated_start_angle, rotated_end_angle = rotated_end_angle, rotated_start_angle
    else:
        if rotated_end_angle >= 2*math.pi:
            rotated_end_angle = rotated_end_angle - 2*math.pi
            rotated_start_angle, rotated_end_angle = rotated_end_angle, rotated_start_angle


    rotated_center_x, rotated_center_y = rotate_point(arc.dxf.center, pivot, angle)

    # rotated_arc = arc.new()
    rotated_arc = arc.copy()
    rotated_arc.dxf.center = (rotated_center_x, rotated_center_y)
    rotated_arc.dxf.radius = radius
    rotated_arc.dxf.start_angle = rad_to_deg(rotated_start_angle)
    rotated_arc.dxf.end_angle = rad_to_deg(rotated_end_angle)
    
    return rotated_arc


def rotate_ellipse_by_pp(ellipse, pivot, angle):
    """Rotates an ellipse around a pivot point by a specified angle."""
    ratio = ellipse.dxf.ratio
    start_param = ellipse.dxf.start_param
    end_param = ellipse.dxf.end_param

    rotated_center_x, rotated_center_y = rotate_point(ellipse.dxf.center, pivot, angle)
    major_axis_vector = Vec3(ellipse.dxf.major_axis)
    current_angle = math.atan2(major_axis_vector.y, major_axis_vector.x)
    new_angle = current_angle + angle

    major_axis_length = major_axis_vector.magnitude
    new_major_axis = (major_axis_length * math.cos(new_angle), major_axis_length * math.sin(new_angle))
    
    rotated_major_axis_x, rotated_major_axis_y = rotate_point(ellipse.dxf.major_axis, pivot, angle)
    rotated_minor_axis_x, rotated_minor_axis_y = rotate_point(ellipse.minor_axis, pivot, angle)

    #rotated_ellipse = ellipse.new()
    rotated_ellipse = ellipse.copy()
    rotated_ellipse.dxf.center = (rotated_center_x, rotated_center_y)
    rotated_ellipse.dxf.major_axis = new_major_axis
    rotated_ellipse.dxf.ratio = ratio
    rotated_ellipse.dxf.start_param = start_param
    rotated_ellipse.dxf.end_param = end_param

    return rotated_ellipse



def rotate_line_by_pivot_point(line, pivot, angle):
    """Rotates a line around a pivot point by a specified angle."""
    
    # Rotate the entity around the pivot
    rotated_start_x, rotated_start_y = rotate_point(line.dxf.start, pivot, angle)
    rotated_end_x, rotated_end_y = rotate_point(line.dxf.end, pivot, angle)
    
    # Create a new entity with the rotated coordinates
    # rotated_line = line.new()
    rotated_line = line.copy()
    rotated_line.dxf.start = (rotated_start_x, rotated_start_y)
    rotated_line.dxf.end = (rotated_end_x, rotated_end_y)

    return rotated_line


def rotate_lwpolyline_by_pp(lwpoly, pivot, angle):
    """
    Ruota una LWPOLYLINE attorno a un pivot.
    Il bulge si conserva — appartiene al segmento, non ai punti.
    """
    points = list(lwpoly.get_points(format='xyseb'))  # x, y, start_width, end_width, bulge
    rotated_points = []
    for (x, y, sw, ew, bulge) in points:
        rx, ry = rotate_point((x, y), pivot, angle)
        rotated_points.append((rx, ry, sw, ew, bulge))
    
    rotated = lwpoly.copy()
    rotated.dxf.layer = lwpoly.dxf.layer
    rotated.set_points(rotated_points, format='xyseb')
    return rotated



##################################################################################################
##################################################################################################
################################################################################################    


def deg_to_rad(angle_deg):
    """Converts an angle from degrees to radians."""
    return (angle_deg * math.pi) / 180

def rad_to_deg(angle_rad):
    """Converts an angle from radians to degrees."""
    return (angle_rad * 180) / math.pi



