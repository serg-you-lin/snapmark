"""
Helpers.py - Generic utility functions for SnapMark.

Collects common helper functions used by multiple modules.
"""

import ezdxf
from pathlib import Path
from snapmark.utils.messages import file_not_found_error, not_a_dxf_error, no_dxf_found_error

def count_holes(hole_list):
    """Counts the number of holes in a list."""

    return len(list(hole_list))
    

def get_file_base_name(file_name):
    """Extracts the base name of a file without extension."""
    
    import os
    return os.path.splitext(file_name)[0]


def find_all_circles(doc):
    """Finds all circles in a DXF document."""
    
    msp = doc.modelspace()
    return msp.query('CIRCLE')


def find_dxf_files(folder_path, recursive=False):
    """Finds all DXF files in a folder or validates a single DXF file."""
    
    path = Path(folder_path)
    
    # 1. Controlla se esiste
    if not path.exists():
        print(file_not_found_error(folder_path))
        return []
    
    # 2. Se è un FILE singolo
    if path.is_file():
        # Controlla se è un DXF
        if path.suffix.lower() != ".dxf":
            print(not_a_dxf_error(path.name))
            return []
        print(f"🔧 Found 1 file to process: {path.name}")
        return [path]
    
    # 3. Se è una CARTELLA
    if recursive:
        dxf_files = [f for f in path.rglob("*") if f.suffix.lower() == ".dxf"]
    else:
        dxf_files = [f for f in path.iterdir() if f.suffix.lower() == ".dxf"]
    
    # 4. Se non trova nessun DXF
    if not dxf_files:
        print(no_dxf_found_error(folder_path))
        return []
    
    print(f"🔧 Found {len(dxf_files)} file(s) to process in {folder_path}")
    return dxf_files


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



def find_circle_by_radius(min_diam=0, max_diam=float('inf')):
    """Creates a function that finds circles within a specified diameter range."""
    
    return lambda doc: find_spec_holes(doc, min_diam, max_diam)


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

# Print the names of the layers
def print_layers(doc):
    # print("Layers:")
    for layer in doc.layers:
        print(layer.dxf.name)
        return print(layer.dxf.name)


def is_excluded_layer(entity_layer, excluded_list):
    if excluded_list is None:
        return False  # niente è escluso
    layer = entity_layer.strip().lower()
    excluded = [e.strip().lower() for e in excluded_list]
    return layer in excluded




# Alias for backward compatibility
def select_files(filtered_files):
    """DEPRECATED: Use file_pattern in process_folder() instead."""

    filtered_files = [f.lower() for f in filtered_files]
    
    def __filter_file(folder, dxf_file):
        return dxf_file.lower() in filtered_files
    
    return lambda folder, dxf_file: __filter_file(folder, dxf_file)



