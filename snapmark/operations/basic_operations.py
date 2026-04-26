
import os
import traceback
import ezdxf
from abc import ABC, abstractmethod
from pathlib import Path

try:
    from snapmark.utils.backup_manager import BackupManager
    BACKUP_AVAILABLE = True
except ImportError:
    BACKUP_AVAILABLE = False

from snapmark.utils.helpers import find_dxf_files, print_layers
from snapmark.utils.messages import (
    file_in_use_error, file_not_found_error, 
    cannot_open_error, cannot_save_error,
    processing_error, backup_error
)
from snapmark.utils.text_utils import fix_mleader_styles


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
                import traceback
                traceback.print_exc()
                print(processing_error(file_name, str(e)))
                return False
            
            # Save if modified
            if modified:
                try:
                    fix_mleader_styles(doc)
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
            traceback.print_exc()
            print(processing_error(file_name, str(e)))
            return False
        
    
    def execute_on_doc(self, doc, file_name: str, folder: str = "") -> bool:
        """
        Performs the operation on an ezdxf document already loaded in memory.
        Does not open or save files — processing only.

        Args:
            doc: Already opened ezdxf document.
            file_name: Filename (used for name-based sequences).
            folder: File directory (used only if the sequence calls .folder()).

        Returns:
            bool: True if the document was modified.
        """
        return self.execute(doc, folder, file_name)

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




