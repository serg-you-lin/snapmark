
import os
import ezdxf
from abc import ABC, abstractmethod
from pathlib import Path

try:
    from snapmark.utils.backup_manager import BackupManager
    BACKUP_AVAILABLE = True
except ImportError:
    BACKUP_AVAILABLE = False

from snapmark.mark_algorithm.mark_algorithm import *
from snapmark.entities.add_entities import *
from snapmark.checking.checking import *
from snapmark.utils.helpers import find_dxf_files
from snapmark.utils.messages import (
    file_in_use_error, file_not_found_error, 
    cannot_open_error, cannot_save_error,
    processing_error, backup_error
)


class Operation(ABC):
    """Base class for all operations on DXF files."""
    
    def __init__(self):
        self.create_new = True 
        self.message_text = None
        self.modifies_files = True
    
    @abstractmethod
    def execute(self, doc, folder, file_name):
        """Legacy method for compatibility with iteration_manager."""
        pass
    
    def message(self, file_name):
        """Prints a completion message for the operation."""
        if self.message_text:
            print(self.message_text)
        else:
            print(f"Operation complete on {file_name}")
    
    def execute_single(self, file_path: str, use_backup: bool = True) -> bool:
        """
        Executes the operation on a single file.
        CATCHES ALL ERRORS and prints ONE clear message.
        
        Args:
            file_path: Full path of the DXF file.
            use_backup: If True, uses BackupManager to preserve the original.
            
        Returns:
            bool: True if the file was modified, False if error occurred.
        """
        file_name = os.path.basename(file_path)
        
        try:
            # Check file exists
            if not os.path.exists(file_path):
                print(file_not_found_error(file_name))
                return False
            
            # Backup handling
            if use_backup and BACKUP_AVAILABLE:
                try:
                    BackupManager.ensure_original(file_path)
                except PermissionError:
                    print(file_in_use_error(file_name))
                    return False
                except Exception as e:
                    print(backup_error(file_name, str(e)))
                    return False
            
            # Extract folder and filename
            folder = os.path.dirname(file_path)
            
            # Open the file - THIS IS WHERE IT FAILS IF FILE IS OPEN
            try:
                doc = ezdxf.readfile(file_path)
            except PermissionError:
                print(file_in_use_error(file_name))
                return False
            except Exception as e:
                print(cannot_open_error(file_name, str(e)))
                return False
            
            # Execute operation
            try:
                modified = self.execute(doc, folder, file_name)
            except Exception as e:
                print(processing_error(file_name, str(e)))
                return False
            
            # Save if modified
            if modified:
                try:
                    doc.saveas(file_path)
                    self.message(file_name)
                    return True
                except PermissionError:
                    print(file_in_use_error(file_name))
                    return False
                except Exception as e:
                    print(cannot_save_error(file_name, str(e)))
                    return False
            
            return False
            
        except Exception as e:
            # Catch-all for any unexpected error
            print(processing_error(file_name, str(e)))
            return False
    
    @classmethod
    def process_folder(cls, folder_path: str, operation_instance: 'Operation', 
                      use_backup: bool = True, recursive: bool = False,
                      file_pattern: str = "*.dxf") -> dict:
        """Static method to apply an operation to all DXF files in a folder."""
        stats = {
            'processed': 0,
            'modified': 0,
            'errors': 0
        }

        dxf_files = find_dxf_files(folder_path, recursive=recursive)
        
        for file_path in dxf_files:
            success = operation_instance.execute_single(str(file_path), use_backup=use_backup)
            if success:
                stats['processed'] += 1
                stats['modified'] += 1
            else:
                if operation_instance.modifies_files:
                    stats['errors'] += 1
                else:
                    stats['processed'] += 1  
        
        print(f"\n✓ Processed: {stats['processed']}")
        print(f"✓ Modified: {stats['modified']}")
        if stats['errors'] > 0:
            print(f"❌ Errors: {stats['errors']}")
        
        return stats


# ========== CONCRETE IMPLEMENTATIONS (unchanged) ==========

class AddMark(Operation):
    """Adding numeric marking to DXF files."""
    
    def __init__(self, sequence, scale_factor=50, space=1.5, min_char=5,
                 max_char=20, arbitrary_x=None, arbitrary_y=None, align='c',
                 start_y=1, step=2, margin=1, down_to=None, mark_layer='MARK', 
                 mark_color=None, excluded_layers=None):
        super().__init__()
        self.sequence = sequence
        self.scale_factor = scale_factor
        self.space = space
        self.min_char = min_char
        self.max_char = max_char
        self.arbitrary_x = arbitrary_x
        self.arbitrary_y = arbitrary_y
        self.align = align
        self.start_y = start_y
        self.step = step
        self.margin = margin
        self.down_to = down_to
        self.mark_layer = mark_layer
        self.mark_color = mark_color
        self.excluded_layers = excluded_layers
        self.sequence_position = NS()

    def __repr__(self):
        return f"AddMark(sequence={self.sequence})"

    def execute(self, doc, folder, file_name):
        """Legacy method - maintains original logic for compatibility."""
        scale_factor = comp_sf(doc, self.scale_factor)
        sequence = self.sequence.get_sequence_text(folder, file_name)
        
        start_x, start_y = comp_center_point((doc))
        self.sequence_position = place_sequence(
            doc, sequence, scale_factor, self.excluded_layers, self.space, 
            self.min_char, self.max_char, self.arbitrary_x, self.arbitrary_y, 
            self.align, self.start_y, self.step, self.margin, self.down_to
        )

        add_numbers_to_layer(doc, self.sequence_position, self.mark_layer, self.mark_color)
        return self.create_new
                     
    def message(self, file_name):
        if len(self.sequence_position.sequence) == 0:
            self.message_text = f"⚠ No space found for the sequence in file {file_name}." 
        else:
            self.message_text = f"✓ Sequence added to {file_name}"
        print(self.message_text)


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


class PrintLayers(Operation):
    """Prints the layers present in the file (does not modify)."""
    
    def __init__(self):
        super().__init__()
        self.create_new = False

    def execute(self, doc, folder, file_name):
        print_layers(doc)
        return self.create_new
    
    def message(self, file_name):
        self.message_text = f"Layer presenti in {file_name}:"
        print(self.message_text)