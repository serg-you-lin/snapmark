"""Funzioni di convenienza per uso rapido."""
import os
from .sequence.sequence_system import from_file_name, from_split_text
from .operations.basic_operations import Operation
from .operations.placement import AddMark
from .utils.helpers import find_circle_by_radius
from .operations.counter import CountHoles, Counter 
from .utils.backup_manager import BackupManager


def mark_by_name(file_or_folder, align='c', min_height=5, max_height=20, start_y=1, **kwargs):
    """
    Marks file/folder using the full name of the file.
    
    Args:
        file_or_folder: Path to the file or folder
        align (str): The alignment of the sequence ('l' for left, 'c' for center, 'r' for right; default is 'c').
        min_height (float): The minimum height for characters (default is 5).
        max_height (float): The maximum height for characters (default is 20).
        start_y (float): The starting y-coordinate for the search (default is 1).
        **kwargs: Other parameters for AddMark
    """
    
    sequence = from_file_name(trim_start=kwargs.pop('trim_start', 0), trim_end=kwargs.pop('trim_end', 0))
    mark_op = AddMark(sequence, align=align, min_height=min_height, max_height=max_height, start_y=start_y, **kwargs)
    
    if os.path.isfile(file_or_folder):
        mark_op.execute_single(file_or_folder)
    else:
        Operation.process_folder(file_or_folder, mark_op)

def mark_by_split_text(file_or_folder, separator='_', part_index=0, 
                      align='c', min_height=5, max_height=20, start_y=1, **kwargs):
    """
    Marks using a part of the file name (split by separator).
    
    Useful when the filename contains multiple pieces of information separated (e.g., PART_123_5mm).
    
    Args:
        file_or_folder: Path to the file or folder
        separator: Separator character (default: '_')
        part_index: Which part to extract (0 = first)
        align (str): The alignment of the sequence ('l' for left, 'c' for center, 'r' for right; default is 'c').
        min_height (float): The minimum height for characters (default is 5).
        max_height (float): The maximum height for characters (default is 20).
        start_y (float): The starting y-coordinate for the search (default is 1).
        **kwargs: Other parameters for AddMark
    """
    
    sequence = from_split_text(separator, part_index)
    mark_op = AddMark(sequence, align=align, min_height=min_height, max_height=max_height, start_y=start_y, **kwargs)
    
    if os.path.isfile(file_or_folder):
        mark_op.execute_single(file_or_folder)
    else:
        Operation.process_folder(file_or_folder, mark_op)

def mark_with_sequence(file_or_folder, sequence, align='c', min_height=5, max_height=20, start_y=1, **kwargs):
    """
    Marks files with a custom sequence.

    Args:
        file_or_folder: File or folder path
        sequence: Custom Sequence object
        align (str): The alignment of the sequence ('l' for left, 'c' for center, 'r' for right; default is 'c').
        min_height (float): The minimum height for characters (default is 5).
        max_height (float): The maximum height for characters (default is 20).
        start_y (float): The starting y-coordinate for the search (default is 1).
    """
    
    # from .operations.basic_operations import AddMark, Operation
    
    mark_op = AddMark(sequence, align=align, min_height=min_height, max_height=max_height, start_y=start_y, **kwargs)
    
    if os.path.isfile(file_or_folder):
        mark_op.execute_single(file_or_folder)
    else:
        Operation.process_folder(file_or_folder, mark_op)



def quick_count_holes(file_or_folder, min_diam=0, max_diam=float('inf'), 
                    multiplier=None, verbose=False):
    """
    Quickly counts holes in a folder.
    
    Args:
        file_or_folder: Path to the file or folder
        min_diam: Minimum diameter
        max_diam: Maximum diameter
        multiplier: Optional function that takes file_name and returns a multiplier
        verbose: If True, shows details for each file
        
    Returns:
        dict with statistics
    """
    
    find_func = find_circle_by_radius(min_diam, max_diam)
    counter = CountHoles(find_func, verbose=verbose)
    
    # Add multiplier if provided
    if multiplier:
        counter.mult(multiplier)
    
    if os.path.isfile(file_or_folder):
        return counter.execute_single(file_or_folder)
    else:
        return Counter.process_folder(file_or_folder, counter)



def single_file_pipeline(file_path, *operations, use_backup=True):
    """
    Applies a pipeline of operations to a single file.
    
    Args:
        file_path: Path to the DXF file
        *operations: Operations to apply in sequence
        use_backup: If True, creates a backup before modifying
    
    Returns:
        dict with statistics
    """

    import ezdxf

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Optional backup
    if use_backup:
        BackupManager.ensure_original(file_path)
    
    # Open file
    doc = ezdxf.readfile(file_path)
    folder = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    
    # Apply operations in sequence
    modified = False
    for operation in operations:
        result = operation.execute(doc, folder, file_name)
        if result:  # If operation modified the file
            modified = True
        
        # Show message if available
        if hasattr(operation, 'message'):
            operation.message(file_name)
    
    # Save if modified
    if modified:
        doc.saveas(file_path)
        print(f"✓ File modified: {file_name}")
    else:
        print(f"○ File not modified: {file_name}")
    
    return {
        'file': file_path,
        'modified': modified,
        'operations_count': len(operations)
    }






def restore_backup(file_or_folder, delete_backups=True, recursive=False):
    """
    Restores backup files (.bak) in the folder.
    
    Overwrites the original DXF files with the backup versions.
    Useful for undoing unwanted operations.
    
    Args:
        file_or_folder: Path to a single file or folder
        delete_backups: If True, deletes the .bak files after restoration (default: True)
        recursive: If True, searches for backups in subfolders as well (default: False)
    
    Returns:
        dict with restoration statistics
    
    Warning:
        This operation OVERWRITES existing files!
    """
    from .utils.backup_manager import BackupManager
    
    return BackupManager.restore_all_in_folder(file_or_folder, delete_backups, recursive)



