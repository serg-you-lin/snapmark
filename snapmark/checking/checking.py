import sys
import os
import ezdxf
from snapmark.mark_algorithm.mark_algorithm import *
from snapmark.entities.add_entities import *


# Print the names of the layers
def print_layers(doc):
    # print("Layers:")
    for layer in doc.layers:
        print(layer.dxf.name)
        return print(layer.dxf.name)
    
def find_spec_holes(doc, diametro_minimo=0, diametro_massimo=float('inf')):
    """
    Searches for specific holes in a document based on diameter range.
    
    Args:
        doc: The document containing the entities to search.
        diametro_minimo: Minimum diameter of the holes to find (default: 0).
        diametro_massimo: Maximum diameter of the holes to find (default: infinity).
    
    Returns:
        A list of circular entities that match the specified diameter range.
    """
    holes = []  # List to store circular entities

    msp = doc.modelspace()  # Access the model space of the drawing

    # Iterate through all entities in the model space
    for entity in msp.query('CIRCLE'):  # Filter only entities of type circle
        diameter = entity.dxf.radius * 2  # Calculate the diameter of the circle
        if diametro_minimo <= diameter <= diametro_massimo:
            holes.append(entity)
            # Add the circular entity to the list if it falls within the diameter range
        
    return holes


def find_entities(file_path, entity_type):
    """Return a list of DXF entities of the given type from the specified file."""
    # Load DXF file using ezdxf
    doc = ezdxf.readfile(file_path)
    
    # extract entities from model
    msp = doc.modelspace()

    entities = []

    # Iterate through all entities of the specified type
    for entity in msp.query(entity_type):
        entities.append(entity)

    return entities

def print_entities(msp):
    for e in msp.query():
        print(e)



def find_circle_centers(holes_list):
    """
    Finds the centers of circles from a list of holes.
    
    Args:
        holes_list: A list of circular entities representing holes.
    
    Returns:
        A list of tuples containing the (x, y) coordinates of the circle centers.
    """
    centers = []  # List to store the centers of the circles

    # Iterate through the circular entities in the holes_list
    for circle in holes_list:  # Use the list passed as an argument
        center_x = circle.dxf.center.x  # Extract the x coordinate of the circle's center
        center_y = circle.dxf.center.y  # Extract the y coordinate of the circle's center
        centers.append((center_x, center_y))  # Add the x and y coordinates of the center to the list
        
    return centers


def find_circle_centers_2(doc):
    """
    Searches for circles in a document and detects their centers.
    
    Args:
        doc: The document containing the entities to search.
    
    Returns:
        A list of tuples containing the (x, y) coordinates of the circle centers.
    """
    centers = []  # List to store the centers of the circles

    msp = doc.modelspace()  # Access the model space of the drawing

    # Iterate through all entities in the model space
    for circle in msp.query('CIRCLE'):  # Filter only entities of type circle
        center_x = circle.dxf.center.x  # Extract the x coordinate of the circle's center
        center_y = circle.dxf.center.y  # Extract the y coordinate of the circle's center
        centers.append((center_x, center_y))  # Add the x and y coordinates of the center to the list
        
    return centers


def change_layer(entities, new_layer):
    for entity in entities:
        entity.set_dxf_attrib('layer', new_layer)



